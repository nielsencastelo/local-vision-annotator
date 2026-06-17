from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from annotation_app.exporter import export_yolo
from annotation_app.project_io import (
    DEFAULT_COLORS,
    STATUSES,
    create_or_update_project,
    import_legacy_yolo_labels,
    label_path,
    list_projects,
    load_image_index,
    load_metadata,
    load_project,
    progress,
    rebuild_image_index,
    save_metadata,
)
from annotation_app.yolo_io import Box, read_yolo, write_yolo


st.set_page_config(page_title="Local Vision Annotator", layout="wide")

PROJECTS_ROOT = ROOT / "annotations"
MAX_CANVAS_WIDTH = 1100


def class_name(classes: list[dict], class_id: int) -> str:
    for item in classes:
        if int(item["id"]) == int(class_id):
            return item["name"]
    return str(class_id)


def display_size(width: int, height: int) -> tuple[int, int, float]:
    scale = min(1.0, MAX_CANVAS_WIDTH / max(width, 1))
    return int(width * scale), int(height * scale), scale


def boxes_to_drawing(boxes: list[Box], scale: float, classes: list[dict]) -> dict:
    color_by_id = {int(item["id"]): item.get("color", DEFAULT_COLORS[0]) for item in classes}
    objects = []
    for box in boxes:
        color = color_by_id.get(int(box.class_id), DEFAULT_COLORS[0])
        objects.append(
            {
                "type": "rect",
                "left": box.x * scale,
                "top": box.y * scale,
                "width": box.width * scale,
                "height": box.height * scale,
                "fill": "rgba(0, 0, 0, 0)",
                "stroke": color,
                "strokeWidth": 3,
            }
        )
    return {"version": "4.4.0", "objects": objects}


def canvas_objects_to_rows(objects: list[dict], scale: float, loaded_boxes: list[Box], default_class_id: int) -> list[dict]:
    rows = []
    for idx, obj in enumerate(objects):
        if obj.get("type") != "rect":
            continue
        class_id = loaded_boxes[idx].class_id if idx < len(loaded_boxes) else default_class_id
        rows.append(
            {
                "keep": True,
                "class_id": int(class_id),
                "x": round(float(obj.get("left", 0)) / scale, 1),
                "y": round(float(obj.get("top", 0)) / scale, 1),
                "width": round(float(obj.get("width", 0)) * float(obj.get("scaleX", 1)) / scale, 1),
                "height": round(float(obj.get("height", 0)) * float(obj.get("scaleY", 1)) / scale, 1),
            }
        )
    return rows


def boxes_dataframe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["keep", "class_id", "x", "y", "width", "height"])


def save_current(project_path: Path, item: dict, rows: pd.DataFrame, image: Image.Image, status: str, notes: str) -> None:
    boxes = [
        Box(
            class_id=int(row["class_id"]),
            x=float(row["x"]),
            y=float(row["y"]),
            width=float(row["width"]),
            height=float(row["height"]),
        )
        for _, row in rows.iterrows()
        if bool(row.get("keep", True)) and float(row["width"]) >= 1 and float(row["height"]) >= 1
    ]
    write_yolo(label_path(project_path, item["id"]), boxes, image.width, image.height)
    meta = load_metadata(project_path, item["id"], item["path"])
    meta["image_path"] = item["path"]
    meta["status"] = status
    meta["notes"] = notes
    save_metadata(project_path, item["id"], meta)


def next_index(current: int, total: int, step: int) -> int:
    if total == 0:
        return 0
    return max(0, min(total - 1, current + step))


st.title("Local Vision Annotator")

PROJECTS_ROOT.mkdir(exist_ok=True)
projects = list_projects(PROJECTS_ROOT)

with st.sidebar:
    st.header("Projeto")
    project_options = ["Criar novo"] + [p.name for p in projects]
    selected_project = st.selectbox("Abrir", project_options)

    if selected_project == "Criar novo":
        project_name = st.text_input("Nome", value="numero_onibus")
        image_dir = st.text_input("Diretorio de imagens", value=str(ROOT / "bases" / "numero_onibus"))
        classes_df = st.data_editor(
            pd.DataFrame([{"id": 0, "name": "NUMERO_ONIBUS", "color": "#00c8ff"}]),
            num_rows="dynamic",
            use_container_width=True,
        )
        instructions = st.text_area(
            "Instrucoes",
            value="Anotar os digitos do numero do onibus na placa frontal ou lateral. Ignorar numeros desfocados, muito pequenos ou distantes.",
            height=90,
        )
        if st.button("Criar ou atualizar", type="primary"):
            path = create_or_update_project(PROJECTS_ROOT, project_name, image_dir, classes_df.to_dict("records"), instructions)
            st.session_state["project_path"] = str(path)
            st.session_state["image_index"] = 0
            st.rerun()
        st.stop()

    project_path = PROJECTS_ROOT / selected_project
    st.session_state["project_path"] = str(project_path)
    project = load_project(project_path)
    st.caption(str(project_path))

    if st.button("Atualizar indice de imagens"):
        rebuild_image_index(project_path)
        st.session_state["image_index"] = 0
        st.rerun()

images = load_image_index(project_path)
counts = progress(project_path, images)
classes = project["classes"]

with st.sidebar:
    st.header("Progresso")
    done = counts.get("annotated", 0) + counts.get("empty", 0) + counts.get("skipped", 0)
    st.progress(done / max(counts["total"], 1))
    st.write({key: counts.get(key, 0) for key in STATUSES})

    status_filter = st.multiselect("Filtro de status", STATUSES, default=STATUSES)
    current_class_id = st.selectbox(
        "Classe para novas boxes",
        [int(item["id"]) for item in classes],
        format_func=lambda cid: f"{cid} - {class_name(classes, cid)}",
    )

    with st.expander("Importar labels do notebook"):
        legacy_dir = st.text_input("Pasta labels_numero", value=str(Path(project["image_dir"]) / "labels_numero"))
        if st.button("Importar labels existentes"):
            result = import_legacy_yolo_labels(project_path, Path(legacy_dir), class_id=0)
            st.success(f"Importadas: {result['imported']} anotadas, {result['empty']} vazias, {result['skipped']} ignoradas.")
            st.rerun()

    with st.expander("Exportar YOLO"):
        train_pct = st.number_input("Train %", min_value=1, max_value=98, value=80)
        val_pct = st.number_input("Val %", min_value=0, max_value=98, value=15)
        seed = st.number_input("Seed", value=42)
        include_empty = st.checkbox("Incluir imagens vazias", value=True)
        if st.button("Exportar dataset"):
            try:
                output = export_yolo(project_path, train_pct=int(train_pct), val_pct=int(val_pct), seed=int(seed), include_empty=include_empty)
                st.success(f"Exportado em: {output}")
            except FileExistsError:
                st.error("A pasta de exportacao ja existe. Tente novamente para gerar um novo timestamp.")

filtered = [item for item in images if load_metadata(project_path, item["id"], item["path"]).get("status", "pending") in status_filter]

if not filtered:
    st.info("Nenhuma imagem encontrada para o filtro atual.")
    st.stop()

if "image_index" not in st.session_state:
    st.session_state["image_index"] = 0
st.session_state["image_index"] = min(st.session_state["image_index"], len(filtered) - 1)
item = filtered[st.session_state["image_index"]]
meta = load_metadata(project_path, item["id"], item["path"])
image_path = Path(item["path"])

if not image_path.exists():
    st.error(f"Imagem nao encontrada: {image_path}")
    st.stop()

image = Image.open(image_path).convert("RGB")
canvas_width, canvas_height, scale = display_size(image.width, image.height)
display_image = image.resize((canvas_width, canvas_height))
loaded_boxes = read_yolo(label_path(project_path, item["id"]), image.width, image.height)

top_left, top_right = st.columns([0.72, 0.28], gap="large")

with top_left:
    st.subheader(f"{st.session_state['image_index'] + 1}/{len(filtered)} - {item['relative_path']}")
    canvas = st_canvas(
        fill_color="rgba(0, 0, 0, 0)",
        stroke_width=3,
        stroke_color=next((c["color"] for c in classes if int(c["id"]) == int(current_class_id)), DEFAULT_COLORS[0]),
        background_image=display_image,
        initial_drawing=boxes_to_drawing(loaded_boxes, scale, classes),
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode="rect",
        key=f"canvas_{item['id']}",
    )

with top_right:
    st.markdown("**Instrucoes**")
    st.write(project.get("instructions", ""))
    status = st.selectbox("Status", STATUSES, index=STATUSES.index(meta.get("status", "pending")) if meta.get("status", "pending") in STATUSES else 0)
    notes = st.text_area("Notas", value=meta.get("notes", ""), height=90)

    objects = canvas.json_data.get("objects", []) if canvas.json_data else []
    rows = canvas_objects_to_rows(objects, scale, loaded_boxes, int(current_class_id))
    boxes_df = st.data_editor(
        boxes_dataframe(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "class_id": st.column_config.SelectboxColumn(
                "class_id",
                options=[int(item["id"]) for item in classes],
            )
        },
        disabled=["x", "y", "width", "height"],
    )

    col_a, col_b = st.columns(2)
    if col_a.button("Salvar", type="primary", use_container_width=True):
        kept = boxes_df[boxes_df["keep"]] if "keep" in boxes_df else boxes_df
        final_status = "annotated" if len(kept) else status
        save_current(project_path, item, boxes_df, image, final_status, notes)
        st.success("Anotacao salva.")
        st.rerun()
    if col_b.button("Sem objeto", use_container_width=True):
        save_current(project_path, item, pd.DataFrame([], columns=["keep", "class_id", "x", "y", "width", "height"]), image, "empty", notes)
        st.rerun()

    col_c, col_d = st.columns(2)
    if col_c.button("Revisar depois", use_container_width=True):
        save_current(project_path, item, boxes_df, image, "needs_review", notes)
        st.rerun()
    if col_d.button("Pular", use_container_width=True):
        meta["status"] = "skipped"
        meta["notes"] = notes
        save_metadata(project_path, item["id"], meta)
        st.rerun()

    nav_a, nav_b = st.columns(2)
    if nav_a.button("Anterior", use_container_width=True):
        st.session_state["image_index"] = next_index(st.session_state["image_index"], len(filtered), -1)
        st.rerun()
    if nav_b.button("Proxima", use_container_width=True):
        st.session_state["image_index"] = next_index(st.session_state["image_index"], len(filtered), 1)
        st.rerun()
