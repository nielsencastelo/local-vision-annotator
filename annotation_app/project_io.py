from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
import math
from pathlib import Path
from typing import Any


DEFAULT_EXTENSIONS = [".jpg", ".jpeg", ".png"]
DEFAULT_COLORS = ["#00c8ff", "#f59e0b", "#22c55e", "#ef4444", "#a855f7", "#14b8a6"]
STATUSES = ["pending", "annotated", "empty", "skipped", "needs_review"]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", value).strip("_") or "projeto"


def project_dir(base_dir: Path, name: str) -> Path:
    return base_dir / slugify(name)


def list_projects(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    return sorted([p for p in base_dir.iterdir() if (p / "project.json").exists()])


def ensure_dirs(path: Path) -> None:
    for child in ["labels", "metadata", "exports"]:
        (path / child).mkdir(parents=True, exist_ok=True)


def default_project(name: str, image_dir: str, path: Path) -> dict[str, Any]:
    created_at = now_iso()
    return {
        "name": slugify(name),
        "display_name": name.strip() or slugify(name),
        "task_type": "bbox",
        "image_dir": str(Path(image_dir).expanduser()),
        "labels_dir": str(path / "labels"),
        "classes": [{"id": 0, "name": "NUMERO_ONIBUS", "color": "#00c8ff"}],
        "image_extensions": DEFAULT_EXTENSIONS,
        "instructions": (
            "Anotar os digitos do numero do onibus na placa frontal ou lateral. "
            "Ignorar numeros desfocados, muito pequenos ou distantes."
        ),
        "created_at": created_at,
        "updated_at": created_at,
    }


def save_project(path: Path, project: dict[str, Any]) -> None:
    ensure_dirs(path)
    project["updated_at"] = now_iso()
    project["labels_dir"] = str(path / "labels")
    (path / "project.json").write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")


def load_project(path: Path) -> dict[str, Any]:
    return json.loads((path / "project.json").read_text(encoding="utf-8"))


def create_or_update_project(base_dir: Path, name: str, image_dir: str, classes: list[dict[str, Any]], instructions: str) -> Path:
    path = project_dir(base_dir, name)
    if (path / "project.json").exists():
        project = load_project(path)
    else:
        project = default_project(name, image_dir, path)
    project["display_name"] = name.strip() or project["name"]
    project["name"] = slugify(name)
    project["image_dir"] = str(Path(image_dir).expanduser())
    project["classes"] = normalize_classes(classes)
    project["instructions"] = instructions.strip()
    save_project(path, project)
    rebuild_image_index(path)
    return path


def normalize_classes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    classes = []
    for idx, row in enumerate(rows):
        raw_name = str(row.get("name", "")).strip()
        if not raw_name or raw_name.lower() in {"none", "nan"}:
            continue
        raw_id = row.get("id")
        try:
            if raw_id is None or (isinstance(raw_id, float) and math.isnan(raw_id)) or str(raw_id).strip() == "":
                class_id = len(classes)
            else:
                class_id = int(raw_id)
        except (TypeError, ValueError):
            class_id = len(classes)
        raw_color = row.get("color")
        color = "" if raw_color is None else str(raw_color).strip()
        color = color if color and color.lower() != "nan" else DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
        classes.append({"id": class_id, "name": raw_name, "color": color})
    if not classes:
        classes.append({"id": 0, "name": "OBJETO", "color": DEFAULT_COLORS[0]})
    classes.sort(key=lambda item: item["id"])
    return classes


def image_id(image_dir: Path, image_path: Path) -> str:
    try:
        rel = image_path.relative_to(image_dir).as_posix()
    except ValueError:
        rel = image_path.as_posix()
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12]
    return f"{image_path.stem}_{digest}"


def rebuild_image_index(project_path: Path) -> list[dict[str, str]]:
    project = load_project(project_path)
    image_dir = Path(project["image_dir"]).expanduser()
    extensions = {ext.lower() for ext in project.get("image_extensions", DEFAULT_EXTENSIONS)}
    images = []
    if image_dir.exists():
        for path in sorted(image_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in extensions:
                images.append(
                    {
                        "id": image_id(image_dir, path),
                        "path": str(path),
                        "relative_path": path.relative_to(image_dir).as_posix(),
                    }
                )
    (project_path / "images_index.json").write_text(json.dumps(images, indent=2, ensure_ascii=False), encoding="utf-8")
    for item in images:
        meta_path = metadata_path(project_path, item["id"])
        if not meta_path.exists():
            save_metadata(project_path, item["id"], {"image_path": item["path"], "status": "pending", "notes": "", "tags": []})
    return images


def load_image_index(project_path: Path) -> list[dict[str, str]]:
    index_path = project_path / "images_index.json"
    if not index_path.exists():
        return rebuild_image_index(project_path)
    return json.loads(index_path.read_text(encoding="utf-8"))


def label_path(project_path: Path, item_id: str) -> Path:
    return project_path / "labels" / f"{item_id}.txt"


def metadata_path(project_path: Path, item_id: str) -> Path:
    return project_path / "metadata" / f"{item_id}.json"


def load_metadata(project_path: Path, item_id: str, image_path: str = "") -> dict[str, Any]:
    path = metadata_path(project_path, item_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"image_path": image_path, "status": "pending", "notes": "", "tags": [], "updated_at": now_iso()}


def save_metadata(project_path: Path, item_id: str, metadata: dict[str, Any]) -> None:
    metadata["updated_at"] = now_iso()
    metadata_path(project_path, item_id).write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def state_path(project_path: Path) -> Path:
    return project_path / "state.json"


def load_state(project_path: Path) -> dict[str, Any]:
    path = state_path(project_path)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(project_path: Path, state: dict[str, Any]) -> None:
    state_path(project_path).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_last_image_id(project_path: Path) -> str | None:
    return load_state(project_path).get("last_image_id")


def set_last_image_id(project_path: Path, item_id: str) -> None:
    state = load_state(project_path)
    if state.get("last_image_id") == item_id:
        return
    state["last_image_id"] = item_id
    save_state(project_path, state)


def progress(project_path: Path, images: list[dict[str, str]]) -> dict[str, int]:
    counts = {status: 0 for status in STATUSES}
    for item in images:
        meta = load_metadata(project_path, item["id"], item["path"])
        counts[meta.get("status", "pending")] = counts.get(meta.get("status", "pending"), 0) + 1
    counts["total"] = len(images)
    return counts


def import_legacy_yolo_labels(project_path: Path, legacy_labels_dir: Path, class_id: int = 0) -> dict[str, int]:
    """Import labels generated by the old notebook using image stem matching."""
    images = load_image_index(project_path)
    by_stem: dict[str, list[dict[str, str]]] = {}
    for item in images:
        by_stem.setdefault(Path(item["path"]).stem, []).append(item)

    imported = 0
    empty = 0
    skipped = 0
    legacy_labels_dir = legacy_labels_dir.expanduser()
    for label in sorted(legacy_labels_dir.glob("*.txt")):
        matches = by_stem.get(label.stem, [])
        if len(matches) != 1:
            skipped += 1
            continue
        item = matches[0]
        lines = []
        for line in label.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if parts and parts[0] == str(class_id):
                lines.append(line.strip())
        target_label = label_path(project_path, item["id"])
        target_label.parent.mkdir(parents=True, exist_ok=True)
        target_label.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        meta = load_metadata(project_path, item["id"], item["path"])
        meta["status"] = "annotated" if lines else "empty"
        save_metadata(project_path, item["id"], meta)
        if lines:
            imported += 1
        else:
            empty += 1
    return {"imported": imported, "empty": empty, "skipped": skipped}
