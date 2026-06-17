from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Box:
    class_id: int
    x: float
    y: float
    width: float
    height: float


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_box(box: Box, image_width: int, image_height: int) -> tuple[int, float, float, float, float]:
    x1 = clamp(box.x, 0, image_width)
    y1 = clamp(box.y, 0, image_height)
    x2 = clamp(box.x + box.width, 0, image_width)
    y2 = clamp(box.y + box.height, 0, image_height)
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1

    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    cx = (x1 + width / 2) / image_width
    cy = (y1 + height / 2) / image_height
    bw = width / image_width
    bh = height / image_height
    return box.class_id, cx, cy, bw, bh


def denormalize_box(class_id: int, cx: float, cy: float, width: float, height: float, image_width: int, image_height: int) -> Box:
    abs_w = width * image_width
    abs_h = height * image_height
    x = (cx * image_width) - abs_w / 2
    y = (cy * image_height) - abs_h / 2
    return Box(class_id=class_id, x=x, y=y, width=abs_w, height=abs_h)


def read_yolo(path: Path, image_width: int, image_height: int) -> list[Box]:
    if not path.exists():
        return []
    boxes: list[Box] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            class_id = int(float(parts[0]))
            cx, cy, width, height = map(float, parts[1:5])
        except ValueError:
            continue
        boxes.append(denormalize_box(class_id, cx, cy, width, height, image_width, image_height))
    return boxes


def write_yolo(path: Path, boxes: list[Box], image_width: int, image_height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for box in boxes:
        if box.width < 1 or box.height < 1:
            continue
        class_id, cx, cy, width, height = normalize_box(box, image_width, image_height)
        if width <= 0 or height <= 0:
            continue
        lines.append(f"{class_id} {cx:.6f} {cy:.6f} {width:.6f} {height:.6f}")
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

