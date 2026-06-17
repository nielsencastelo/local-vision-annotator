# Annotation App Package

This package contains the reusable annotation workflow used by both interfaces:
the Streamlit web app and the Jupyter notebook demo.

## Modules

- `app.py`: Streamlit browser interface.
- `notebook_annotator.py`: OpenCV GUI annotator for notebook workflows.
- `project_io.py`: project creation, image indexing, metadata, and legacy label import.
- `yolo_io.py`: YOLO label reading, writing, and coordinate conversion.
- `exporter.py`: YOLO dataset export with train/validation/test splits.

## Demo Data

The root-level `annotation.ipynb` notebook is configured to use:

```text
data/
  image_01.jpeg
  image_02.jpeg
  image_03.jpeg
```

It creates the project `annotations/demo_boxes/` and uses a single class:

```python
{"id": 0, "name": "BOX", "color": "#f59e0b"}
```

The same project can be opened from the Streamlit app after the notebook creates it.
The Streamlit app also creates this demo project automatically when `data/`
contains the sample images.

If the notebook annotation window appears too small, increase `max_width` and
`max_height` in the `run_notebook_annotator(...)` call.
