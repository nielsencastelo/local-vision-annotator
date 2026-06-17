# Plano para App Local de Anotacao de Imagens

Este documento orienta uma IA ou desenvolvedor a implementar um sistema web simples, local, para anotacao de imagens em projetos de visao computacional. A primeira versao deve reproduzir e melhorar o fluxo do notebook `notebook/05_anotar_numero_onibus.ipynb`, mas de forma generica para diferentes projetos, classes e datasets.

## Objetivo

Criar um app local em Streamlit para:

- ler um diretorio local de imagens;
- permitir anotacao visual com bounding boxes;
- salvar anotacoes em formato YOLO;
- registrar status por imagem;
- organizar projetos de anotacao;
- exportar datasets prontos para treinamento;
- permitir reutilizacao em outros casos, como numero de onibus, caixas, avarias, onibus quebrado ou qualquer outro objeto.

O app deve ser simples de rodar em qualquer maquina com Python:

```bash
streamlit run app.py
```

## Contexto do Notebook Atual

O notebook `05_anotar_numero_onibus.ipynb` implementa um anotador OpenCV para uma classe fixa:

- classe: `0 NUMERO_ONIBUS`;
- entrada: diretorios como `bases/numero_onibus` e `bases/imagens_old`;
- saida: arquivos `.txt` em `labels_numero/`;
- formato: YOLO bounding box, com linhas `class_id cx cy w h`;
- interacao: desenhar box com mouse, salvar com Enter, descartar com `D`, desfazer com `Z`;
- integracao final: copia imagens anotadas para `datasets/fase_c_v1/combined/{train,val,test}`.

O novo app deve manter a ideia central, mas remover as limitacoes:

- classe nao deve ser fixa;
- subpasta de labels nao deve ser fixa;
- projeto deve ter metadados;
- imagem sem objeto deve ter status explicito;
- exportacao deve ser separada da anotacao;
- app deve funcionar no navegador, sem depender da GUI do OpenCV.

## Escopo da Primeira Versao

A primeira versao deve suportar apenas bounding boxes e exportacao YOLO. Nao implementar segmentacao, poligonos, OCR automatico, login, banco de dados ou multiusuario.

Funcionalidades obrigatorias:

- selecionar ou digitar um diretorio local de imagens;
- criar ou abrir um projeto de anotacao;
- definir classes do projeto;
- listar imagens pendentes, anotadas, vazias e para revisao;
- exibir uma imagem por vez;
- desenhar, editar e remover bounding boxes;
- escolher a classe de cada box;
- salvar anotacoes em disco;
- marcar imagem como sem objeto;
- marcar imagem como revisar depois;
- navegar para proxima/anterior;
- mostrar progresso;
- exportar dataset YOLO com `train`, `val`, `test` e `data.yaml`.

Funcionalidades opcionais para versoes futuras:

- classificacao por imagem sem bounding box;
- anotacao por poligono;
- atalhos de teclado;
- pre-anotacao com modelo YOLO;
- revisao por filtro de classe;
- importacao de labels existentes;
- suporte COCO;
- suporte Label Studio/CVAT.

## Tecnologia Recomendada

Usar Streamlit como interface principal.

Dependencias recomendadas:

- `streamlit`;
- `streamlit-drawable-canvas`, para desenhar boxes no navegador;
- `Pillow`, para leitura e exibicao das imagens;
- `PyYAML`, para gerar `data.yaml`;
- `pandas`, opcional para tabelas de progresso;
- bibliotecas ja existentes no projeto, quando fizer sentido.

Evitar dependencia de `opencv-python` com GUI. O projeto atualmente usa `opencv-python-headless`, que e adequado para servidor e processamento, mas nao para janelas interativas.

## Estrutura Recomendada

Criar um modulo isolado para o app de anotacao. Exemplo:

```text
annotation_app/
  app.py
  core/
    project.py
    images.py
    yolo.py
    export.py
    status.py
  ui/
    sidebar.py
    annotator.py
    dashboard.py
  README.md
```

Alternativa mais simples para MVP:

```text
annotation_app/
  app.py
  project_io.py
  yolo_io.py
  exporter.py
```

Preferir a alternativa simples no inicio. Separar melhor depois, quando o fluxo estiver validado.

## Estrutura dos Projetos de Anotacao

Cada projeto de anotacao deve ser salvo em uma pasta propria, sem misturar diretamente com o dataset final.

Exemplo:

```text
annotations/
  numero_onibus/
    project.json
    images_index.json
    labels/
      img001.txt
      img002.txt
    metadata/
      img001.json
      img002.json
    exports/
      yolo_2026_06_17/
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

O diretorio original das imagens nao precisa ser copiado para dentro do projeto durante a anotacao. O projeto pode guardar os caminhos originais. A copia deve acontecer apenas na exportacao.

## Arquivo project.json

O arquivo `project.json` deve conter a configuracao do projeto:

```json
{
  "name": "numero_onibus",
  "task_type": "bbox",
  "image_dir": "E:/Evollo/Projetos/urubupunga-ml/bases/numero_onibus",
  "labels_dir": "annotations/numero_onibus/labels",
  "classes": [
    {"id": 0, "name": "NUMERO_ONIBUS", "color": "#00c8ff"}
  ],
  "image_extensions": [".jpg", ".jpeg", ".png"],
  "created_at": "2026-06-17T00:00:00",
  "updated_at": "2026-06-17T00:00:00"
}
```

Para outros projetos, o usuario deve conseguir trocar as classes:

```json
{
  "classes": [
    {"id": 0, "name": "CAIXA", "color": "#f59e0b"},
    {"id": 1, "name": "PALETE", "color": "#22c55e"}
  ]
}
```

## Metadata por Imagem

Cada imagem deve ter um arquivo de metadata para registrar status e informacoes extras.

Exemplo `metadata/img001.json`:

```json
{
  "image_path": "E:/dados/imagens/img001.jpg",
  "status": "annotated",
  "notes": "",
  "tags": ["frontal", "boa_qualidade"],
  "updated_at": "2026-06-17T00:00:00"
}
```

Status permitidos:

- `pending`: ainda nao revisada;
- `annotated`: possui anotacoes salvas;
- `empty`: revisada e sem objeto visivel;
- `skipped`: ignorada por problema de qualidade ou outro motivo;
- `needs_review`: marcada para revisao posterior.

Essa separacao e importante. Uma imagem sem objeto nao deve voltar como pendente.

## Formato das Labels

Usar YOLO bounding box:

```text
class_id center_x center_y width height
```

Todos os valores devem ser normalizados entre 0 e 1.

Exemplo:

```text
0 0.512345 0.433210 0.120000 0.080000
1 0.222222 0.700000 0.180000 0.150000
```

O app deve ter funcoes claras para converter:

- coordenadas absolutas de tela para coordenadas da imagem;
- coordenadas da imagem para YOLO normalizado;
- YOLO normalizado para boxes exibiveis.

Este ponto e critico porque a imagem pode ser redimensionada no navegador. Nunca salvar coordenadas baseadas apenas no tamanho exibido.

## Fluxo da Interface

A interface deve ter uma sidebar e uma area principal.

Sidebar:

- campo para escolher projeto;
- campo para diretorio de imagens;
- editor simples de classes;
- filtro de status;
- botoes de exportacao;
- resumo de progresso.

Area principal:

- nome da imagem atual;
- imagem com canvas;
- seletor de classe atual;
- lista de boxes da imagem;
- botoes:
  - salvar;
  - sem objeto;
  - revisar depois;
  - pular;
  - anterior;
  - proxima;
  - remover box selecionada.

O app deve salvar frequentemente. O usuario nao deve perder progresso se fechar o navegador.

## Regras de Anotacao

Permitir que cada projeto tenha instrucoes proprias. Para o caso atual de numero de onibus:

- anotar os digitos do numero do onibus na placa frontal ou lateral;
- incluir todos os digitos visiveis;
- aceitar numero parcialmente cortado se ainda for util;
- ignorar numero desfocado;
- ignorar placa traseira se essa regra continuar valendo;
- ignorar numero muito pequeno ou distante.

Essas instrucoes podem ficar em `project.json` ou em um arquivo `instructions.md` dentro do projeto.

Para projetos genericos, o usuario deve conseguir escrever instrucoes como:

- "Anotar todas as caixas visiveis";
- "Marcar apenas onibus quebrado";
- "Ignorar objetos parcialmente ocluidos";
- "Marcar avarias maiores que 5 cm".

## Exportacao YOLO

A exportacao deve ser uma etapa separada da anotacao.

Entrada da exportacao:

- projeto de anotacao;
- percentual de split, por exemplo 80/15/5;
- seed aleatoria;
- destino de saida.

Saida esperada:

```text
exports/yolo_YYYY_MM_DD/
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

O arquivo `data.yaml` deve conter:

```yaml
path: .
train: train/images
val: val/images
test: test/images
names:
  0: NUMERO_ONIBUS
```

Exportar apenas imagens com status:

- `annotated`, quando o objetivo for dataset positivo;
- opcionalmente `empty`, se o treinamento precisar de imagens negativas.

Essa escolha deve ser uma opcao da interface.

## Compatibilidade com o Notebook Atual

Para aproveitar anotacoes ja feitas pelo notebook:

- detectar labels existentes em `labels_numero/`;
- importar essas labels para o novo projeto;
- criar metadata como `annotated` quando houver box;
- criar metadata como `empty` quando existir arquivo vazio;
- manter classe `0 NUMERO_ONIBUS`.

Esse importador pode ser uma funcionalidade posterior, mas a arquitetura deve permitir.

## Plano de Implementacao

### Fase 1: MVP de Anotacao

Implementar:

- app Streamlit;
- criacao/abertura de projeto;
- leitura de diretorio de imagens;
- canvas de bounding box;
- salvamento YOLO;
- metadata com status;
- navegacao entre imagens.

Criterio de pronto:

- usuario consegue anotar uma pasta pequena;
- fechar e abrir o app preserva progresso;
- labels YOLO geradas corretamente.

### Fase 2: Organizacao e Exportacao

Implementar:

- dashboard de progresso;
- filtros por status;
- exportacao YOLO `train/val/test`;
- geracao de `data.yaml`;
- opcao de incluir ou excluir imagens `empty`.

Criterio de pronto:

- dataset exportado treina com Ultralytics sem ajuste manual;
- splits sao reprodutiveis com seed.

### Fase 3: Melhorias de Produtividade

Implementar:

- atalhos de teclado;
- editor de classes mais confortavel;
- importacao das labels do notebook;
- revisao de imagens `needs_review`;
- copia ou snapshot opcional das imagens usadas no projeto.

Criterio de pronto:

- fluxo fica rapido o suficiente para centenas ou milhares de imagens;
- usuario consegue migrar anotacoes antigas.

### Fase 4: Generalizacao

Implementar, se necessario:

- classificacao por imagem;
- suporte a multiplos formatos de exportacao;
- pre-anotacao com modelo YOLO;
- relatorio de qualidade do dataset;
- validacao de labels quebradas ou boxes fora da imagem.

## Cuidados Tecnicos

- Nao misturar anotacao com exportacao.
- Nao depender da janela GUI do OpenCV.
- Nao salvar coordenadas no tamanho exibido pelo navegador.
- Nao considerar arquivo de label ausente igual a imagem sem objeto.
- Nao apagar labels de outras classes sem aviso.
- Nao sobrescrever exportacoes antigas automaticamente.
- Nao copiar milhares de imagens durante a anotacao, apenas na exportacao.
- Nao criar banco de dados na primeira versao.

## Criterios de Qualidade

Antes de considerar o app pronto:

- testar com imagens `.jpg`, `.jpeg` e `.png`;
- testar imagem pequena, grande, horizontal e vertical;
- testar imagem sem box;
- testar multiplas boxes na mesma imagem;
- testar multiplas classes;
- validar que YOLO gerado esta correto;
- treinar ou ao menos carregar o dataset com Ultralytics;
- interromper o app e abrir novamente para confirmar persistencia.

## Resultado Esperado

Ao final, o projeto deve ter uma ferramenta local e reutilizavel para anotacao de datasets de visao computacional. Ela deve substituir o fluxo manual do notebook para tarefas recorrentes, mas continuar simples o bastante para rodar em qualquer maquina sem infraestrutura externa.

O primeiro alvo pratico e o projeto `NUMERO_ONIBUS`, mas a estrutura deve permitir criar novos projetos, como caixas, avarias ou classificacao visual de onibus quebrado, sem reescrever o app.
