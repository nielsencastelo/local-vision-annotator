from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.elements.image as st_image
from PIL import Image
from streamlit_drawable_canvas import st_canvas

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from annotation_app.exporter import export_yolo, sync_to_source_labels
from annotation_app.project_io import (
    DEFAULT_COLORS,
    STATUSES,
    create_or_update_project,
    import_labels_dir,
    import_legacy_yolo_labels,
    label_path,
    list_projects,
    load_image_index,
    load_metadata,
    load_project,
    progress,
    project_exists,
    rebuild_image_index,
    save_metadata,
    slugify,
    sync_labels_dir,
)
from annotation_app.yolo_io import Box, read_yolo, write_yolo


st.set_page_config(page_title="Local Vision Annotator", layout="wide")

PROJECTS_ROOT = ROOT / "annotations"
MAX_CANVAS_WIDTH = 1100
RESUMABLE_STATUSES = {"annotated", "empty", "skipped", "needs_review"}

REPO_ROOT = ROOT.parent   # .../urubupunga-ml

# ── Presets: atalhos para os datasets do urubupunga-ml ────────────────────────
# Sao apenas valores iniciais do formulario — qualquer pasta/classe pode ser
# digitada na mao, e projetos ja existentes sempre carregam a propria config.
PRESET_VAZIO = "Projeto vazio (personalizado)"

PRESETS: dict[str, dict] = {
    PRESET_VAZIO: {
        "name": "",
        "image_dir": str(REPO_ROOT / "bases"),
        "classes": [{"id": 0, "name": "objeto", "color": DEFAULT_COLORS[0]}],
        "instructions": "Descreva o que deve ser anotado e o que deve ser ignorado.",
        "sync_labels_dir": "",
        "import_labels_dir": "",
    },
    "Avarias de onibus (notebooks 04/06)": {
        "name": "avarias_onibus",
        "image_dir": str(REPO_ROOT / "bases" / "imagens_extraidas_avul_santana"),
        # Cores em hex (RGB) equivalentes as do anotador do notebook 09.
        "classes": [
            {"id": 0, "name": "numero_onibus",    "color": "#ffc800"},
            {"id": 1, "name": "amassado",         "color": "#dc5000"},
            {"id": 2, "name": "arranhao",         "color": "#00c800"},
            {"id": 3, "name": "rachadura",        "color": "#0064ff"},
            {"id": 4, "name": "vidro_quebrado",   "color": "#c800c8"},
            {"id": 5, "name": "ferrugem",         "color": "#ffa500"},
            {"id": 6, "name": "peca_faltando",    "color": "#0000b4"},
            {"id": 7, "name": "espelho_quebrado", "color": "#00ffff"},
        ],
        "instructions": (
            "Anote TODAS as avarias visiveis (mesmo pequenas), com a caixa mais justa possivel.\n"
            "1) Escolha a classe em 'Classe para novas boxes' ANTES de desenhar.\n"
            "2) Desenhe a caixa sobre o dano. Pode trocar a classe de cada caixa na tabela.\n"
            "Classes: 0 numero_onibus, 1 amassado, 2 arranhao, 3 rachadura, 4 vidro_quebrado,\n"
            "5 ferrugem, 6 peca_faltando, 7 espelho_quebrado.\n"
            "Onibus integro (sem avaria): use 'Sem objeto' (vira negativa/fundo).\n"
            "Se o numero do onibus aparecer, aproveite e marque a classe 0 tambem.\n"
            "O progresso e salvo a cada imagem — pode fechar e continuar depois."
        ),
        "sync_labels_dir": str(REPO_ROOT / "bases" / "imagens_extraidas_avul_santana" / "labels_avarias"),
        "import_labels_dir": str(REPO_ROOT / "bases" / "imagens_extraidas_avul_santana" / "labels_numero"),
    },
    "Detector de onibus (notebook 13)": {
        "name": "detector_onibus",
        "image_dir": str(REPO_ROOT / "bases" / "detector_onibus" / "images"),
        "classes": [{"id": 0, "name": "onibus", "color": "#00c8ff"}],
        "instructions": (
            "Desenhe UMA caixa por onibus visivel (inclua micro-onibus e vans de transporte).\n"
            "Onibus cortado pela borda: anote a parte visivel.\n"
            "Sem nenhum onibus na foto: use 'Sem objeto' (negativa valida para ESTE modelo).\n"
            "As pre-anotacoes do COCO ja vem importadas — confira e corrija pela tabela.\n"
            "Ao terminar use 'Exportar YOLO' marcando 'Incluir imagens vazias'."
        ),
        # Este projeto alimenta o merge do notebook 13 via export, nao via sync.
        "sync_labels_dir": "",
        "import_labels_dir": str(REPO_ROOT / "bases" / "detector_onibus" / "labels_auto"),
    },
}


def patch_streamlit_drawable_canvas_image_url() -> None:
    """Restore the Streamlit internal helper expected by streamlit-drawable-canvas.

    Newer Streamlit versions removed `streamlit.elements.image.image_to_url`,
    but streamlit-drawable-canvas still calls it for background images.
    Prefer Streamlit's current media-file helper when available, so the canvas
    receives a normal `/media/...` URL instead of a data URL.
    """
    if hasattr(st_image, "image_to_url"):
        return

    try:
        from streamlit.elements.lib import image_utils
        from streamlit.elements.lib.layout_utils import LayoutConfig

        def image_to_url(image, width=None, clamp=False, channels="RGB", output_format="PNG", image_id=None):
            return image_utils.image_to_url(
                image,
                LayoutConfig(width=width),
                clamp,
                channels,
                output_format,
                image_id or "drawable-canvas-bg",
            )

        st_image.image_to_url = image_to_url
        return
    except Exception:
        pass

    def image_to_url(image, width=None, clamp=False, channels="RGB", output_format="PNG", image_id=None):
        if not isinstance(image, Image.Image):
            image = Image.open(image)
        if channels:
            image = image.convert(channels)
        buffer = io.BytesIO()
        image.save(buffer, format=output_format or "PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        mime = "image/png" if (output_format or "PNG").upper() == "PNG" else "image/jpeg"
        return f"data:{mime};base64,{encoded}"

    st_image.image_to_url = image_to_url


patch_streamlit_drawable_canvas_image_url()


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


def canvas_key(item_id: str) -> str:
    """Chave do canvas, versionada por imagem.

    O `st_canvas` so le `initial_drawing` quando monta. Sem trocar a chave apos
    salvar, uma caixa removida continuaria desenhada na tela (e voltaria para a
    tabela na proxima interacao, porque a tabela e derivada do canvas).
    """
    version = st.session_state.get("canvas_versions", {}).get(item_id, 0)
    return f"canvas_{item_id}_{version}"


def refresh_canvas(item_id: str) -> None:
    versions = st.session_state.setdefault("canvas_versions", {})
    versions[item_id] = versions.get(item_id, 0) + 1


def next_index(current: int, total: int, step: int) -> int:
    if total == 0:
        return 0
    return max(0, min(total - 1, current + step))


def initial_resume_index(project_path: Path, images: list[dict], filtered: list[dict]) -> int:
    """Open near the latest saved annotation without changing project files."""
    if not filtered:
        return 0

    filtered_by_id = {item["id"]: idx for idx, item in enumerate(filtered)}
    latest_saved: tuple[str, int, str] | None = None

    for image_pos, item in enumerate(images):
        meta = load_metadata(project_path, item["id"], item["path"])
        if meta.get("status", "pending") not in RESUMABLE_STATUSES:
            continue
        updated_at = str(meta.get("updated_at", ""))
        candidate = (updated_at, image_pos, item["id"])
        if latest_saved is None or candidate > latest_saved:
            latest_saved = candidate

    if latest_saved is None:
        return 0

    _, latest_pos, latest_id = latest_saved

    for item in images[latest_pos + 1 :]:
        if item["id"] not in filtered_by_id:
            continue
        meta = load_metadata(project_path, item["id"], item["path"])
        if meta.get("status", "pending") == "pending":
            return filtered_by_id[item["id"]]

    if latest_id in filtered_by_id:
        return filtered_by_id[latest_id]

    for item in images[latest_pos + 1 :]:
        if item["id"] in filtered_by_id:
            return filtered_by_id[item["id"]]

    return 0


def proxima_pendente_index(project_path: Path, images: list[dict], filtered: list[dict], apos_id: str | None = None) -> int | None:
    """Posicao (em `filtered`) da proxima imagem `pending`.

    Se `apos_id` for informado, procura a partir da imagem seguinte a ela na
    ordem do indice, dando a volta ao inicio se necessario. Retorna None se nao
    houver nenhuma pendente visivel no filtro atual.
    """
    filtered_by_id = {item["id"]: idx for idx, item in enumerate(filtered)}
    inicio = 0
    if apos_id:
        for pos, item in enumerate(images):
            if item["id"] == apos_id:
                inicio = pos + 1
                break
    for item in images[inicio:] + images[:inicio]:
        if item["id"] not in filtered_by_id:
            continue
        meta = load_metadata(project_path, item["id"], item["path"])
        if meta.get("status", "pending") == "pending":
            return filtered_by_id[item["id"]]
    return None


def project_form(base: dict, key_prefix: str) -> dict:
    """Campos de configuracao de um projeto, pre-preenchidos com `base`.

    Usado tanto para criar quanto para editar: as chaves dos widgets incluem o
    `key_prefix` (nome do projeto) para que trocar de projeto recarregue os
    valores em vez de manter o que estava na tela.
    """
    image_dir = st.text_input("Diretorio de imagens", value=str(base.get("image_dir", "")), key=f"{key_prefix}_image_dir")
    if image_dir and not Path(image_dir).expanduser().exists():
        st.warning("Pasta inexistente — o indice ficara vazio.")
    classes_df = st.data_editor(
        pd.DataFrame(base.get("classes") or [{"id": 0, "name": "objeto", "color": DEFAULT_COLORS[0]}]),
        num_rows="dynamic",
        use_container_width=True,
        key=f"{key_prefix}_classes",
    )
    instructions = st.text_area("Instrucoes", value=str(base.get("instructions", "")), height=180, key=f"{key_prefix}_instructions")
    sync_dir = st.text_input(
        "Pasta de sincronizacao (labels p/ o pipeline)",
        value=str(base.get("sync_labels_dir", "") or ""),
        help="Vazio = <diretorio de imagens>/labels_avarias.",
        key=f"{key_prefix}_sync_dir",
    )
    legacy_dir = st.text_input(
        "Pasta de labels para importar",
        value=str(base.get("import_labels_dir", "") or ""),
        help="Labels YOLO ja prontas (pre-anotacao ou notebook). Vazio = <diretorio de imagens>/labels_auto.",
        key=f"{key_prefix}_import_dir",
    )
    return {
        "image_dir": image_dir,
        "classes": classes_df.to_dict("records"),
        "instructions": instructions,
        "extra": {"sync_labels_dir": sync_dir.strip(), "import_labels_dir": legacy_dir.strip()},
    }


def project_stats_caption(path: Path) -> str:
    counts = progress(path, load_image_index(path))
    return (
        f"{counts['total']} imagens · {counts['annotated']} anotadas · "
        f"{counts['empty']} negativas · {counts['pending']} pendentes"
    )


st.title("Local Vision Annotator")

PROJECTS_ROOT.mkdir(exist_ok=True)
projects = list_projects(PROJECTS_ROOT)

with st.sidebar:
    st.header("Projeto")
    project_options = ["Criar novo"] + [p.name for p in projects]
    preferred_project = st.session_state.get("selected_project")
    selected_index = project_options.index(preferred_project) if preferred_project in project_options else 0
    selected_project = st.selectbox("Abrir", project_options, index=selected_index)

    if selected_project == "Criar novo":
        preset_label = st.selectbox("Preset", list(PRESETS), key="preset_novo")
        if st.session_state.get("preset_aplicado") != preset_label:
            st.session_state["preset_aplicado"] = preset_label
            st.session_state["novo_nome"] = PRESETS[preset_label]["name"]
        project_name = st.text_input("Nome do projeto", key="novo_nome")

        slug = slugify(project_name) if project_name.strip() else ""
        ja_existe = bool(slug) and project_exists(PROJECTS_ROOT, slug)

        if ja_existe:
            existing_path = PROJECTS_ROOT / slug
            base = load_project(existing_path)
            st.success(f"Projeto `{slug}` ja existe — {project_stats_caption(existing_path)}")
            st.caption("Os campos abaixo mostram a config atual. Abrir mantem tudo; salvar so altera o que voce editar.")
            if st.button("Abrir este projeto", type="primary", use_container_width=True):
                st.session_state["selected_project"] = slug
                st.rerun()
        else:
            base = PRESETS[preset_label]
            if slug:
                st.caption(f"Sera criado em `annotations/{slug}/`.")

        form = project_form(base, key_prefix=f"novo_{slug or 'sem_nome'}")

        if ja_existe and form["image_dir"].strip() != str(base.get("image_dir", "")):
            st.warning("Voce mudou o diretorio de imagens: as anotacoes serao remapeadas pelo nome do arquivo.")

        if st.button("Salvar configuracao" if ja_existe else "Criar projeto", use_container_width=True):
            if not project_name.strip():
                st.error("Informe um nome para o projeto.")
            else:
                path = create_or_update_project(
                    PROJECTS_ROOT,
                    project_name,
                    form["image_dir"],
                    form["classes"],
                    form["instructions"],
                    extra=form["extra"],
                )
                st.session_state["project_path"] = str(path)
                st.session_state["selected_project"] = path.name
                st.session_state["image_index"] = 0
                st.rerun()
        st.stop()

    project_path = PROJECTS_ROOT / selected_project
    st.session_state["project_path"] = str(project_path)
    project = load_project(project_path)
    st.caption(str(project_path))
    st.caption(f"Imagens: {project.get('image_dir', '')}")

    if st.button("Atualizar indice de imagens"):
        rebuild_image_index(project_path)
        st.session_state["image_index"] = 0
        st.session_state["ir_proxima_pendente"] = ""   # abre direto na 1a pendente
        st.rerun()

    with st.expander("Configuracoes do projeto"):
        form = project_form(project, key_prefix=f"cfg_{selected_project}")
        if form["image_dir"].strip() != str(project.get("image_dir", "")):
            st.warning("Trocar o diretorio de imagens remapeia as anotacoes pelo nome do arquivo.")
        if st.button("Salvar configuracoes", use_container_width=True):
            # O nome define a pasta do projeto: so reaproveita o display_name se
            # ele continuar apontando para a mesma pasta.
            display_name = str(project.get("display_name") or "")
            nome_estavel = display_name if slugify(display_name) == selected_project else selected_project
            create_or_update_project(
                PROJECTS_ROOT,
                nome_estavel,
                form["image_dir"],
                form["classes"],
                form["instructions"],
                extra=form["extra"],
            )
            st.success("Configuracoes salvas.")
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

    with st.expander("Importar labels prontas (pre-anotacao / notebook)"):
        legacy_dir = st.text_input(
            "Pasta de origem",
            value=import_labels_dir(project),
            key=f"import_dir_{selected_project}",
        )
        TODAS_AS_CLASSES = -1   # sentinela: mantem as opcoes homogeneas (int)
        import_class = st.selectbox(
            "Classes a importar",
            [TODAS_AS_CLASSES] + [int(item["id"]) for item in classes],
            format_func=lambda cid: "todas as classes" if cid == TODAS_AS_CLASSES else f"{cid} - {class_name(classes, cid)}",
            key=f"import_class_{selected_project}",
        )
        if st.button("Importar labels existentes"):
            result = import_legacy_yolo_labels(
                project_path,
                Path(legacy_dir),
                class_id=None if import_class == TODAS_AS_CLASSES else int(import_class),
            )
            st.success(f"Importadas: {result['imported']} anotadas, {result['empty']} vazias, {result['skipped']} ignoradas.")
            st.rerun()

    with st.expander("Sincronizar labels p/ o pipeline", expanded=bool(project.get("sync_labels_dir"))):
        st.caption(
            "Grava as labels por nome da imagem na pasta abaixo. "
            "Depois rode o notebook de merge e o de treino desse dataset."
        )
        sync_dir = st.text_input(
            "Pasta de destino",
            value=sync_labels_dir(project),
            key=f"sync_dir_{selected_project}",
        )
        sync_empty = st.checkbox("Incluir negativas (status 'empty')", value=True, key="sync_empty")
        if st.button("Sincronizar labels"):
            result = sync_to_source_labels(project_path, Path(sync_dir), include_empty=bool(sync_empty))
            st.success(
                f"Sincronizado: {result['written']} anotadas, "
                f"{result['empty']} negativas, {result['skipped']} ignoradas."
            )
            st.caption(result["target"])

    with st.expander("Exportar YOLO (dataset independente)"):
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

if not images:
    st.warning(
        "No images were found for this project. Check the image directory, then click "
        "`Atualizar indice de imagens` in the sidebar."
    )
    st.code(project.get("image_dir", ""), language="text")
    st.stop()

if not filtered:
    st.info("No images match the current status filter.")
    st.stop()

project_session_key = str(project_path)
if st.session_state.get("image_index_project") != project_session_key:
    st.session_state["image_index"] = initial_resume_index(project_path, images, filtered)
    st.session_state["image_index_project"] = project_session_key
elif "image_index" not in st.session_state:
    st.session_state["image_index"] = initial_resume_index(project_path, images, filtered)
st.session_state["image_index"] = min(st.session_state["image_index"], len(filtered) - 1)

if "ir_proxima_pendente" in st.session_state:
    apos_id = st.session_state.pop("ir_proxima_pendente")
    destino = proxima_pendente_index(project_path, images, filtered, apos_id=apos_id)
    if destino is not None:
        st.session_state["image_index"] = destino

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
        key=canvas_key(item["id"]),
    )

with top_right:
    aviso = st.session_state.pop("flash", None)
    if aviso:
        st.success(aviso)
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
            "keep": st.column_config.CheckboxColumn(
                "manter",
                help="Desmarque e clique em Salvar para remover a caixa.",
            ),
            "class_id": st.column_config.SelectboxColumn(
                "class_id",
                options=[int(item["id"]) for item in classes],
            ),
        },
        disabled=["x", "y", "width", "height"],
        key=f"boxes_{canvas_key(item['id'])}",
    )

    # Desligado por padrao: 'Salvar' continua na mesma imagem (comportamento antigo).
    avancar_ao_salvar = st.toggle(
        "Avancar para a proxima pendente ao salvar",
        value=False,
        key="avancar_ao_salvar",
        help="Ligado: 'Salvar' grava e ja pula para a proxima imagem pendente. "
             "Desligado: grava e continua na imagem atual.",
    )

    col_a, col_b = st.columns(2)
    if col_a.button("Salvar", type="primary", use_container_width=True):
        kept = boxes_df[boxes_df["keep"]] if "keep" in boxes_df else boxes_df
        removidas = len(boxes_df) - len(kept)
        final_status = "annotated" if len(kept) else status
        save_current(project_path, item, boxes_df, image, final_status, notes)
        # Recarrega o canvas a partir do que foi gravado — necessario tanto para
        # ficar na imagem quanto para o caso de nao existir proxima pendente.
        refresh_canvas(item["id"])
        st.session_state["flash"] = (
            f"Anotacao salva: {len(kept)} caixa(s), {removidas} removida(s)."
            if removidas
            else f"Anotacao salva: {len(kept)} caixa(s)."
        )
        if avancar_ao_salvar:
            st.session_state["ir_proxima_pendente"] = item["id"]
        st.rerun()
    if col_b.button("Sem objeto", use_container_width=True):
        save_current(project_path, item, pd.DataFrame([], columns=["keep", "class_id", "x", "y", "width", "height"]), image, "empty", notes)
        # Estes botoes avancam, mas o canvas precisa estar limpo caso nao haja
        # proxima pendente e a tela continue nesta imagem.
        refresh_canvas(item["id"])
        st.session_state["ir_proxima_pendente"] = item["id"]
        st.rerun()

    col_c, col_d = st.columns(2)
    if col_c.button("Revisar depois", use_container_width=True):
        save_current(project_path, item, boxes_df, image, "needs_review", notes)
        refresh_canvas(item["id"])
        st.session_state["ir_proxima_pendente"] = item["id"]
        st.rerun()
    if col_d.button("Pular", use_container_width=True):
        meta["status"] = "skipped"
        meta["notes"] = notes
        save_metadata(project_path, item["id"], meta)
        st.session_state["ir_proxima_pendente"] = item["id"]
        st.rerun()

    nav_a, nav_b = st.columns(2)
    if nav_a.button("Anterior", use_container_width=True):
        st.session_state["image_index"] = next_index(st.session_state["image_index"], len(filtered), -1)
        st.rerun()
    if nav_b.button("Proxima", use_container_width=True):
        st.session_state["image_index"] = next_index(st.session_state["image_index"], len(filtered), 1)
        st.rerun()

    if st.button("Ir para proxima pendente", use_container_width=True):
        st.session_state["ir_proxima_pendente"] = item["id"]
        st.rerun()
