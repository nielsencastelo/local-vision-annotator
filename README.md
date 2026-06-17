# Local Vision Annotator

Local Vision Annotator is a lightweight image annotation toolkit for computer
vision datasets. It provides a reusable local workflow for drawing bounding
boxes, tracking image status, and exporting YOLO-ready datasets without setting
up a database, server, or external labeling platform.

The project supports two annotation modes:

- **Streamlit web app** for browser-based annotation.
- **Notebook annotator** for users who prefer running the workflow from Jupyter
  with an OpenCV GUI window.

Both modes use the same project structure, metadata files, YOLO labels, and
export pipeline.

## Features

- Create and reopen local annotation projects.
- Index images from any local directory.
- Define one or more custom classes per project.
- Draw bounding boxes and save labels in YOLO format.
- Track per-image status: `pending`, `annotated`, `empty`, `skipped`, and
  `needs_review`.
- Mark images explicitly as empty when no target object is visible.
- Import legacy YOLO labels by matching label filenames to image stems.
- Export YOLO datasets with reproducible `train`, `val`, and `test` splits.
- Generate a `data.yaml` file compatible with Ultralytics YOLO training.

## Requirements

Install the Python dependencies from the project root:

```bash
pip install -r requirements.txt
```

The Streamlit app uses `streamlit-drawable-canvas` for browser annotations.
The notebook annotator uses OpenCV GUI support, so it requires `opencv-python`.
If your environment has `opencv-python-headless` installed and the notebook GUI
does not open, remove the headless package and reinstall `opencv-python`.

## Run the Streamlit App

Start the local web app from the project root:

```bash
streamlit run annotation_app/app.py
```

In the sidebar, create or open a project, select the image directory, define
classes, annotate images, update status, and export the final YOLO dataset.

When the repository contains the sample images in `data/`, the app automatically
creates and opens the `demo_boxes` project with one class: `BOX`.

## Quick Start with Sample Images

This repository includes three sample warehouse images in `data/`. They are used
to demonstrate both the notebook workflow and the Streamlit app workflow.

1. Open `annotation.ipynb`.
2. Run the first setup cell. It creates `annotations/demo_boxes/`, indexes the
   images from `data/`, and defines one class: `BOX`.
3. Run the annotation cell to draw boxes around visible cardboard boxes.
4. Open the same project in Streamlit if you want to continue in the browser:

```bash
streamlit run annotation_app/app.py
```

Then select `demo_boxes` in the sidebar.

## Run Annotation from the Notebook

Open:

```text
annotation.ipynb
```

The notebook is configured as a demo using `data/`:

```python
PROJECT_NAME = "demo_boxes"
IMAGE_DIR = PROJECT_ROOT / "data"
CLASSES = [
    {"id": 0, "name": "BOX", "color": "#f59e0b"},
]
```

To use your own images, change these values in the first setup cell:

```python
PROJECT_NAME = "my_project"
IMAGE_DIR = PROJECT_ROOT / "path_to_images"
CLASSES = [
    {"id": 0, "name": "OBJECT", "color": "#00c8ff"},
]
INSTRUCTIONS = "Describe what should be annotated and what should be ignored."
```

Then run the notebook annotator cell. The OpenCV window supports:

```text
Mouse  draw bounding box
ENTER  save as annotated and move forward
D      mark as empty
R      mark for review
S      skip
Z      undo last box
C      cycle class
0-9    select class by id
N/P    next/previous image
ESC    exit
```

If the OpenCV annotation window opens too small, increase `max_width` and
`max_height` in the notebook cell:

```python
run_notebook_annotator(
    project_path,
    max_width=1800,
    max_height=1200,
)
```

## Project Layout

Annotation projects are stored under `annotations/`:

```text
annotations/
  my_project/
    project.json
    images_index.json
    labels/
      image_id.txt
    metadata/
      image_id.json
    exports/
      yolo_YYYY_MM_DD_HHMMSS/
        train/
          images/
          labels/
        val/
          images/
          labels/
        test/
          images/
          labels/
        data.yaml
```

Original images are not copied during annotation. The project stores their
source paths and only copies images during export.

## YOLO Label Format

Labels are saved as standard YOLO bounding boxes:

```text
class_id center_x center_y width height
```

All coordinates are normalized to the original image dimensions, not the display
or browser canvas size.

Example:

```text
0 0.512345 0.433210 0.120000 0.080000
1 0.222222 0.700000 0.180000 0.150000
```

## Exporting a Dataset

Exports are created as a separate step from annotation. The exporter copies
selected images and labels into YOLO split folders and writes `data.yaml`:

```yaml
path: .
train: train/images
val: val/images
test: test/images
names:
  0: OBJECT
```

By default, annotated images are exported. Empty images can also be included as
negative training examples when needed.

## Legacy Label Import

The project can import older YOLO labels from folders such as `labels_numero/`.
Import matches labels to images by filename stem. For example:

```text
images/bus_001.jpg
labels_numero/bus_001.txt
```

Imported files with boxes become `annotated`; empty label files become `empty`.
Ambiguous matches are skipped.

## Repository Structure

```text
annotation_app/
  app.py                  Streamlit interface
  exporter.py             YOLO export pipeline
  notebook_annotator.py   Generic OpenCV notebook annotator
  project_io.py           Project, index, metadata, and import helpers
  yolo_io.py              YOLO read/write and coordinate conversion
docs/
  plano_app_anotacao_streamlit.md
data/
  image_01.jpeg
  image_02.jpeg
  image_03.jpeg
annotation.ipynb
requirements.txt
```

## Notes

- This first version supports bounding boxes and YOLO export only.
- The tool is designed for local, single-user annotation workflows.
- Image metadata is explicit: a missing label file is not treated as an empty
  image.
- Existing exports are not overwritten automatically.
