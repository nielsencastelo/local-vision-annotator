from __future__ import annotations

import random
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .project_io import label_path, load_image_index, load_metadata, load_project


def _copy_pair(project_path: Path, item: dict[str, str], split_dir: Path, used_names: set[str]) -> None:
    image_path = Path(item["path"])
    target_name = image_path.name
    if target_name in used_names:
        target_name = f"{item['id']}{image_path.suffix.lower()}"
    used_names.add(target_name)

    image_out = split_dir / "images" / target_name
    label_out = split_dir / "labels" / f"{Path(target_name).stem}.txt"
    image_out.parent.mkdir(parents=True, exist_ok=True)
    label_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image_path, image_out)

    source_label = label_path(project_path, item["id"])
    if source_label.exists():
        shutil.copy2(source_label, label_out)
    else:
        label_out.write_text("", encoding="utf-8")


def export_yolo(
    project_path: Path,
    output_dir: Path | None = None,
    train_pct: int = 80,
    val_pct: int = 15,
    seed: int = 42,
    include_empty: bool = False,
) -> Path:
    project = load_project(project_path)
    images = load_image_index(project_path)
    allowed = {"annotated"}
    if include_empty:
        allowed.add("empty")

    selected = [item for item in images if load_metadata(project_path, item["id"], item["path"]).get("status") in allowed]
    rng = random.Random(seed)
    rng.shuffle(selected)

    total = len(selected)
    n_train = int(total * train_pct / 100)
    n_val = int(total * val_pct / 100)
    splits = {
        "train": selected[:n_train],
        "val": selected[n_train : n_train + n_val],
        "test": selected[n_train + n_val :],
    }

    if output_dir is None:
        stamp = datetime.now().strftime("yolo_%Y_%m_%d_%H%M%S")
        output_dir = project_path / "exports" / stamp
    output_dir.mkdir(parents=True, exist_ok=False)

    used_names: set[str] = set()
    for split, rows in splits.items():
        split_dir = output_dir / split
        (split_dir / "images").mkdir(parents=True, exist_ok=True)
        (split_dir / "labels").mkdir(parents=True, exist_ok=True)
        for item in rows:
            _copy_pair(project_path, item, split_dir, used_names)

    names = {int(item["id"]): item["name"] for item in project["classes"]}
    data = {"path": ".", "train": "train/images", "val": "val/images", "test": "test/images", "names": names}
    (output_dir / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return output_dir

