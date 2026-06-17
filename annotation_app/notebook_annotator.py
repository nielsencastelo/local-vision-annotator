from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .project_io import (
    STATUSES,
    label_path,
    load_image_index,
    load_metadata,
    load_project,
    save_metadata,
)
from .yolo_io import Box, read_yolo, write_yolo


def _hex_to_bgr(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return (255, 200, 0)
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return (b, g, r)


def _scale_for(width: int, height: int, max_width: int, max_height: int) -> float:
    return min(1.0, max_width / max(width, 1), max_height / max(height, 1))


def _box_to_display(box: Box, scale: float) -> tuple[int, int, int, int]:
    return (
        int(box.x * scale),
        int(box.y * scale),
        int((box.x + box.width) * scale),
        int((box.y + box.height) * scale),
    )


def _box_from_display(class_id: int, x1: int, y1: int, x2: int, y2: int, scale: float) -> Box:
    left = min(x1, x2) / scale
    top = min(y1, y2) / scale
    right = max(x1, x2) / scale
    bottom = max(y1, y2) / scale
    return Box(class_id=class_id, x=left, y=top, width=right - left, height=bottom - top)


def _draw_panel(cv2, height: int, width: int, project: dict, current_class_id: int, item_name: str, idx: int, total: int) -> object:
    import numpy as np

    classes = project["classes"]
    by_id = {int(item["id"]): item for item in classes}
    current = by_id[current_class_id]
    panel = np.full((height, width, 3), 28, dtype=np.uint8)
    color = _hex_to_bgr(current.get("color", "#00c8ff"))
    cv2.rectangle(panel, (0, 0), (width - 1, height - 1), color, 2)
    cv2.rectangle(panel, (2, 2), (width - 3, 38), color, -1)
    cv2.putText(panel, "Notebook Annotator", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 2, cv2.LINE_AA)

    lines = [
        f"Projeto: {project.get('display_name', project['name'])}",
        f"Imagem: {idx + 1}/{total}",
        item_name[:34],
        "",
        "Classe atual:",
        f"[{current_class_id}] {current['name']}",
        "",
        "Mouse: desenhar box",
        "ENTER: salvar anotada",
        "D: sem objeto",
        "R: revisar depois",
        "S: pular",
        "Z: desfazer",
        "C: proxima classe",
        "0-9: escolher classe",
        "N/P: navegar",
        "ESC: sair",
    ]
    y = 62
    for line in lines:
        if not line:
            y += 8
            continue
        line_color = color if line.startswith("[") else (210, 210, 210)
        cv2.putText(panel, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.43, line_color, 1, cv2.LINE_AA)
        y += 22
        if y > height - 12:
            break
    return panel


def _check_gui(cv2) -> bool:
    try:
        cv2.namedWindow("_local_vision_gui_check", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("_local_vision_gui_check")
        return True
    except cv2.error:
        return False


def run_notebook_annotator(
    project_path: str | Path,
    status_filter: Iterable[str] = ("pending", "needs_review"),
    reannotate: bool = False,
    max_width: int = 1600,
    max_height: int = 1080,
    fullscreen: bool = False,
) -> None:
    """Run a generic OpenCV bbox annotator from a notebook cell.

    The annotator reads and writes the same project structure used by the Streamlit app.
    It needs the desktop OpenCV package (`opencv-python`), not `opencv-python-headless`.
    """
    import cv2
    import numpy as np

    if not _check_gui(cv2):
        raise RuntimeError(
            "OpenCV sem suporte a GUI. Instale opencv-python e remova opencv-python-headless, se existir."
        )

    project_path = Path(project_path)
    project = load_project(project_path)
    classes = project["classes"]
    class_ids = [int(item["id"]) for item in classes]
    class_pos = 0
    status_filter = set(status_filter)

    images = load_image_index(project_path)
    if reannotate:
        queue = images
    else:
        queue = [
            item
            for item in images
            if load_metadata(project_path, item["id"], item["path"]).get("status", "pending") in status_filter
        ]

    if not queue:
        print("Nenhuma imagem para anotar com o filtro atual.")
        return

    win = f"Anotador - {project.get('display_name', project['name'])}"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    if fullscreen:
        cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    state = {"drawing": False, "start": (0, 0), "cursor": (0, 0), "boxes": []}
    current_idx = 0

    def mouse_callback(event, x, y, flags, param):
        canvas_width = param["canvas_width"]
        scale = param["scale"]
        if x >= canvas_width:
            return
        if event == cv2.EVENT_LBUTTONDOWN:
            state["drawing"] = True
            state["start"] = (x, y)
            state["cursor"] = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and state["drawing"]:
            state["cursor"] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and state["drawing"]:
            state["drawing"] = False
            x1, y1 = state["start"]
            if abs(x - x1) >= 8 and abs(y - y1) >= 8:
                state["boxes"].append(_box_from_display(class_ids[class_pos], x1, y1, x, y, scale))

    try:
        while 0 <= current_idx < len(queue):
            item = queue[current_idx]
            image_path = Path(item["path"])
            image = cv2.imread(str(image_path))
            if image is None:
                print(f"Nao foi possivel abrir: {image_path}")
                current_idx += 1
                continue

            image_height, image_width = image.shape[:2]
            scale = _scale_for(image_width, image_height, max_width, max_height)
            canvas_width = int(image_width * scale)
            canvas_height = int(image_height * scale)
            display = cv2.resize(image, (canvas_width, canvas_height), interpolation=cv2.INTER_AREA)
            state["boxes"] = read_yolo(label_path(project_path, item["id"]), image_width, image_height)
            cv2.setMouseCallback(win, mouse_callback, {"canvas_width": canvas_width, "scale": scale})
            if not fullscreen:
                cv2.resizeWindow(win, canvas_width + 280, canvas_height)

            while True:
                frame = display.copy()
                by_id = {int(cls["id"]): cls for cls in classes}
                for box in state["boxes"]:
                    color = _hex_to_bgr(by_id.get(int(box.class_id), classes[0]).get("color", "#00c8ff"))
                    x1, y1, x2, y2 = _box_to_display(box, scale)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, str(box.class_id), (x1, max(14, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

                if state["drawing"]:
                    color = _hex_to_bgr(by_id[class_ids[class_pos]].get("color", "#00c8ff"))
                    cv2.rectangle(frame, state["start"], state["cursor"], color, 2)

                panel = _draw_panel(cv2, canvas_height, 280, project, class_ids[class_pos], item["relative_path"], current_idx, len(queue))
                composed = np.hstack([frame, panel])
                cv2.imshow(win, composed)
                key = cv2.waitKey(30) & 0xFF

                if key == 255:
                    continue
                if key == 27:
                    raise KeyboardInterrupt
                if key == ord("z") and state["boxes"]:
                    state["boxes"].pop()
                elif key == ord("c"):
                    class_pos = (class_pos + 1) % len(class_ids)
                elif ord("0") <= key <= ord("9"):
                    chosen = key - ord("0")
                    if chosen in class_ids:
                        class_pos = class_ids.index(chosen)
                elif key == ord("p"):
                    current_idx = max(0, current_idx - 1)
                    break
                elif key == ord("n"):
                    current_idx = min(len(queue) - 1, current_idx + 1)
                    break
                elif key == ord("d"):
                    write_yolo(label_path(project_path, item["id"]), [], image_width, image_height)
                    meta = load_metadata(project_path, item["id"], item["path"])
                    meta["status"] = "empty"
                    meta["image_path"] = item["path"]
                    save_metadata(project_path, item["id"], meta)
                    current_idx += 1
                    break
                elif key == ord("r"):
                    meta = load_metadata(project_path, item["id"], item["path"])
                    meta["status"] = "needs_review"
                    meta["image_path"] = item["path"]
                    save_metadata(project_path, item["id"], meta)
                    current_idx += 1
                    break
                elif key == ord("s"):
                    meta = load_metadata(project_path, item["id"], item["path"])
                    meta["status"] = "skipped"
                    meta["image_path"] = item["path"]
                    save_metadata(project_path, item["id"], meta)
                    current_idx += 1
                    break
                elif key == 13:
                    write_yolo(label_path(project_path, item["id"]), state["boxes"], image_width, image_height)
                    meta = load_metadata(project_path, item["id"], item["path"])
                    meta["status"] = "annotated" if state["boxes"] else "empty"
                    meta["image_path"] = item["path"]
                    save_metadata(project_path, item["id"], meta)
                    current_idx += 1
                    break
    except KeyboardInterrupt:
        print("Anotacao interrompida. Progresso salvo ate a ultima imagem confirmada.")
    finally:
        cv2.destroyAllWindows()

    images = load_image_index(project_path)
    counts = {status: 0 for status in STATUSES}
    for item in images:
        status = load_metadata(project_path, item["id"], item["path"]).get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    print(counts)
