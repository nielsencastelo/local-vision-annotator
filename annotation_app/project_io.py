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
# Convencoes de pasta de labels prontas, na ordem em que sao procuradas quando o
# projeto nao configura `import_labels_dir`.
IMPORT_DIR_CANDIDATES = ["labels_auto", "labels_numero", "labels"]


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
        "classes": [{"id": 0, "name": "OBJETO", "color": DEFAULT_COLORS[0]}],
        "image_extensions": DEFAULT_EXTENSIONS,
        "instructions": "Descreva o que deve ser anotado e o que deve ser ignorado.",
        # Pastas por projeto usadas pelos botoes da barra lateral. Vazio = usa o
        # padrao derivado de image_dir.
        "sync_labels_dir": "",
        "import_labels_dir": "",
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


def project_exists(base_dir: Path, name: str) -> bool:
    return (project_dir(base_dir, name) / "project.json").exists()


def sync_labels_dir(project: dict[str, Any]) -> str:
    """Pasta destino do `sync_to_source_labels` deste projeto."""
    configured = str(project.get("sync_labels_dir", "") or "").strip()
    if configured:
        return configured
    return str(Path(project["image_dir"]) / "labels_avarias")


def import_labels_dir(project: dict[str, Any]) -> str:
    """Pasta de origem do import de labels YOLO ja prontas deste projeto.

    Sem configuracao explicita, usa a primeira convencao que existir no disco
    (`labels_auto` da pre-anotacao, `labels_numero` do notebook antigo, ...).
    """
    configured = str(project.get("import_labels_dir", "") or "").strip()
    if configured:
        return configured
    image_dir = Path(project["image_dir"])
    for candidate in IMPORT_DIR_CANDIDATES:
        if (image_dir / candidate).is_dir():
            return str(image_dir / candidate)
    return str(image_dir / IMPORT_DIR_CANDIDATES[0])


def create_or_update_project(
    base_dir: Path,
    name: str,
    image_dir: str,
    classes: list[dict[str, Any]],
    instructions: str,
    extra: dict[str, Any] | None = None,
) -> Path:
    path = project_dir(base_dir, name)
    exists = (path / "project.json").exists()
    if exists:
        project = load_project(path)
    else:
        project = default_project(name, image_dir, path)

    previous_image_dir = str(project.get("image_dir", ""))
    previous_images = load_image_index(path) if exists else []

    project["display_name"] = name.strip() or project["name"]
    project["name"] = slugify(name)
    project["image_dir"] = str(Path(image_dir).expanduser())
    project["classes"] = normalize_classes(classes)
    project["instructions"] = instructions.strip()
    for key, value in (extra or {}).items():
        project[key] = value

    save_project(path, project)
    images = rebuild_image_index(path)

    # Trocar o image_dir muda o caminho relativo e, com ele, o id das imagens.
    # Sem essa migracao as anotacoes ja feitas ficariam orfas.
    if exists and project["image_dir"] != previous_image_dir:
        migrate_annotations_to_new_ids(path, previous_images, images)
    return path


def _by_stem(images: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for item in images:
        grouped.setdefault(Path(item["path"]).stem, []).append(item)
    return grouped


def _has_work(project_path: Path, item: dict[str, str]) -> bool:
    if label_path(project_path, item["id"]).exists():
        return True
    meta_file = metadata_path(project_path, item["id"])
    if not meta_file.exists():
        return False
    try:
        return json.loads(meta_file.read_text(encoding="utf-8")).get("status", "pending") != "pending"
    except json.JSONDecodeError:
        return False


def migrate_annotations_to_new_ids(
    project_path: Path,
    old_images: list[dict[str, str]],
    new_images: list[dict[str, str]],
) -> dict[str, int]:
    """Reaproveita labels/metadata quando o `image_dir` muda e os ids sao refeitos.

    O id de uma imagem inclui o hash do caminho relativo ao `image_dir`, entao
    apontar o projeto para outra pasta renomeia todos os ids. As anotacoes sao
    reencontradas pelo *stem* do arquivo (unico nos dois indices) e movidas para
    o id novo; o que nao casar continua no disco e e reportado em `orphan`.
    """
    old_by_stem = _by_stem(old_images)
    new_by_stem = _by_stem(new_images)

    moved = orphan = 0
    for stem, olds in old_by_stem.items():
        news = new_by_stem.get(stem, [])
        if len(olds) != 1 or len(news) != 1:
            orphan += sum(1 for item in olds if _has_work(project_path, item))
            continue

        old_id, new_id = olds[0]["id"], news[0]["id"]
        if old_id == new_id or not _has_work(project_path, olds[0]):
            continue

        old_label = label_path(project_path, old_id)
        if old_label.exists():
            label_path(project_path, new_id).write_text(old_label.read_text(encoding="utf-8"), encoding="utf-8")
            old_label.unlink()

        old_meta = metadata_path(project_path, old_id)
        if old_meta.exists():
            meta = json.loads(old_meta.read_text(encoding="utf-8"))
            meta["image_path"] = news[0]["path"]
            metadata_path(project_path, new_id).write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            old_meta.unlink()
        moved += 1

    return {"moved": moved, "orphan": orphan}


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


def progress(project_path: Path, images: list[dict[str, str]]) -> dict[str, int]:
    counts = {status: 0 for status in STATUSES}
    for item in images:
        meta = load_metadata(project_path, item["id"], item["path"])
        counts[meta.get("status", "pending")] = counts.get(meta.get("status", "pending"), 0) + 1
    counts["total"] = len(images)
    return counts


def import_legacy_yolo_labels(
    project_path: Path,
    legacy_labels_dir: Path,
    class_id: int | None = 0,
    status: str = "annotated",
) -> dict[str, int]:
    """Import labels generated by the old notebook using image stem matching.

    `class_id=None` importa todas as classes do arquivo (projeto multiclasse);
    um inteiro mantem so as linhas daquela classe.

    `status` e o status atribuido as imagens que vieram com caixas — use
    `needs_review` para labels automaticas que ainda precisam de conferencia
    humana. Arquivo sem nenhuma caixa entra sempre como `empty` (negativa).
    """
    if status not in STATUSES:
        raise ValueError(f"status invalido: {status!r} (esperado um de {STATUSES})")
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
            if parts and (class_id is None or parts[0] == str(class_id)):
                lines.append(line.strip())
        target_label = label_path(project_path, item["id"])
        target_label.parent.mkdir(parents=True, exist_ok=True)
        target_label.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        meta = load_metadata(project_path, item["id"], item["path"])
        meta["status"] = status if lines else "empty"
        save_metadata(project_path, item["id"], meta)
        if lines:
            imported += 1
        else:
            empty += 1
    return {"imported": imported, "empty": empty, "skipped": skipped}
