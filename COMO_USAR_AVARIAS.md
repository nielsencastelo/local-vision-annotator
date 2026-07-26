# Anotador (web) — urubupunga-ml

App Streamlit para anotar **qualquer dataset** do projeto. Cada dataset vira um
**projeto** independente em `annotations/<nome>/`, com o seu próprio diretório de
imagens, classes, instruções e pastas de sincronização/importação.

> Vantagem deste app sobre o anotador do notebook: o progresso é **salvo a cada
> imagem em disco**. Pode fechar e continuar depois quantas vezes quiser — ele
> retoma exatamente de onde parou (processo longo, 1000+ imagens).

Projetos usados hoje:

| Projeto | Imagens | Classes | Alimenta |
|---------|---------|---------|----------|
| `avarias_onibus` | `bases/imagens_extraidas_avul_santana/` | 8 (avarias) | notebooks 04 (merge) + 06 (treino), via **Sincronizar** |
| `detector_onibus` | `bases/detector_onibus/images/` | 1 (`onibus`) | notebook 13, via **Exportar YOLO** |

## 1. Instalar dependências (uma vez)

```bash
pip install -r requirements.txt
```

## 2. Abrir o app

- **Windows:** dê duplo clique em `run_annotador_avarias.bat`, ou
- No terminal, dentro de `local-vision-annotator-main/`:

```bash
streamlit run annotation_app/app.py
```

Abra `http://localhost:8501` no navegador.

## 3. Escolher ou criar o projeto

Na barra lateral, **Projeto → Abrir**:

- **Projeto já existente** → escolha na lista. Pronto, as anotações já feitas
  aparecem (progresso, filtros, retomada da última imagem).
- **"Criar novo"** → escolha um **Preset** (Avarias, Detector de ônibus ou
  Projeto vazio) e digite o **Nome do projeto**.
  - Se o nome digitado **já existir**, o app avisa (`Projeto X ja existe — N
    imagens, M anotadas`) e carrega a configuração real dele nos campos, em vez
    do preset. Use **"Abrir este projeto"** para entrar sem alterar nada.
  - Se não existir, os campos vêm do preset e o botão cria o projeto em
    `annotations/<nome>/`.

Campos de configuração (iguais na criação e na edição):

| Campo | Para que serve |
|-------|----------------|
| **Diretorio de imagens** | pasta varrida recursivamente (`.jpg/.jpeg/.png`) |
| **Classes** | tabela `id / name / color` — adicione ou remova linhas |
| **Instrucoes** | texto exibido ao lado do canvas durante a anotação |
| **Pasta de sincronizacao** | destino do botão *Sincronizar labels*. Vazio = `<imagens>/labels_avarias` |
| **Pasta de labels para importar** | origem do botão *Importar labels*. Vazio = primeira que existir entre `labels_auto`, `labels_numero`, `labels` |

Para mudar qualquer um deles depois, abra o projeto e use
**"Configuracoes do projeto"** na barra lateral.

> Trocar o **diretório de imagens** de um projeto que já tem anotações é seguro:
> as labels e o status são remapeados pelo **nome do arquivo** da imagem. O que
> não casar (nome duplicado ou imagem que sumiu) continua no disco, apenas fora
> do índice.

## 4. Anotar

1. Na barra lateral, escolha a **"Classe para novas boxes"**.
2. **Arraste** o mouse sobre o objeto para desenhar a caixa.
3. Para mudar a classe de uma caixa, edite a coluna `class_id` na tabela à direita.
4. Para **remover** uma caixa errada, desmarque a coluna **`manter`** na linha dela
   e clique em **Salvar** — o desenho é recarregado já sem ela.
5. Botões:
   - **Salvar** → marca como `annotated` e **continua na mesma imagem**, com o
     desenho recarregado a partir do que foi gravado. Dá para salvar várias vezes
     seguidas enquanto ajusta as caixas.
   - **Sem objeto** → vira **negativa/fundo** (para avarias: ônibus íntegro;
     para o detector: foto sem nenhum ônibus) e vai para a próxima pendente.
   - **Revisar depois** → `needs_review`, vai para a próxima pendente.
   - **Pular** → `skipped` (continua pendente), vai para a próxima pendente.
   - **Anterior / Próxima / Ir para proxima pendente** → navegação.

O **Progresso** (barra lateral) mostra quantas faltam. Use o **Filtro de status**
para ver só as `pending` e continuar de onde parou.

## 5. Aproveitar labels já prontas

**"Importar labels prontas"** lê arquivos YOLO `<nome_da_imagem>.txt` da pasta de
origem e traz para o projeto (casando pelo nome do arquivo). Escolha se importa
**todas as classes** ou só uma. É assim que a pré-anotação COCO do notebook 13
entra no projeto `detector_onibus`.

## 6. Levar as anotações para o treino

Dois caminhos, conforme o projeto:

**A) Sincronizar** (`avarias_onibus`) — abra **"Sincronizar labels p/ o pipeline"**
e clique em **"Sincronizar labels"**. Grava as labels por nome da imagem em
`bases/imagens_extraidas_avul_santana/labels_avarias/`, que é a pasta lida pelo
**notebook 04** (merge). Depois: notebook 04 → notebook 06 (treino).

**B) Exportar** (`detector_onibus`) — abra **"Exportar YOLO (dataset independente)"**,
marque *Incluir imagens vazias* e exporte. Gera
`annotations/<projeto>/exports/yolo_<timestamp>/` com `train/val/test` +
`data.yaml`. O **notebook 13** pega automaticamente o export mais recente.

> As duas operações são idempotentes — pode rodar quantas vezes quiser conforme
> avança. As suas anotações ficam guardadas no projeto (`annotations/<nome>/`),
> independentes do `combined/`.

## Observação sobre versões do Streamlit

O app foi ajustado para funcionar com Streamlit 1.30+. Se atualizar o Streamlit e
aparecer aviso de depreciação de `use_container_width`, é só aviso — segue
funcionando.
