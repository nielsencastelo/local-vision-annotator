# Guia de uso do Local Vision Annotator

Este guia explica como instalar e usar o aplicativo de anotação de imagens para preparar um dataset para treino de modelo YOLO.

Ele foi escrito para quem vai apenas fazer as anotações, sem precisar entender visão computacional. A ideia é simples: abrir uma pasta com imagens, desenhar caixas nos objetos de interesse, salvar o progresso aos poucos e, no final, exportar uma pasta pronta para entregar.

## O que este aplicativo faz

O aplicativo permite marcar objetos em imagens usando caixas retangulares.

Por exemplo:

- se o objetivo for detectar ônibus, você desenha uma caixa em volta de cada ônibus;
- se o objetivo for detectar números na frente do ônibus, você desenha uma caixa em volta de cada número ou placa, conforme a instrução do projeto;
- se uma imagem não tiver o objeto procurado, você marca como "Sem objeto".

Cada caixa salva vira uma anotação que depois será usada para treinar um modelo YOLO.

Você não precisa saber como o YOLO funciona. Basta seguir as regras de anotação combinadas com quem vai treinar o modelo.

## O que você precisa receber antes de começar

Peça para a pessoa responsável pelo projeto enviar:

1. A pasta do aplicativo `local-vision-annotator`.
2. Uma pasta com as imagens que devem ser anotadas.
3. O nome do projeto de anotação.
4. A lista de classes, ou seja, o que deve ser marcado.
5. Instruções claras sobre o que marcar e o que ignorar.

Exemplo de instrução:

```text
Anotar os dígitos do número do ônibus na placa frontal ou lateral.
Ignorar números desfocados, muito pequenos ou distantes.
```

## Instalação no Windows

### 1. Instalar Python

Instale o Python 3.10 ou superior.

Durante a instalação, marque a opção:

```text
Add Python to PATH
```

Essa opção é importante para o Windows conseguir executar o Python pelo terminal.

### 2. Abrir o PowerShell na pasta do projeto

Abra o PowerShell e entre na pasta do aplicativo.

Exemplo:

```powershell
cd D:\Projetos\local-vision-annotator
```

Se o aplicativo estiver em outra pasta, troque o caminho pelo caminho correto.

### 3. Instalar as dependências

Com o PowerShell aberto na pasta do projeto, execute:

```powershell
pip install -r requirements.txt
```

Isso instala as bibliotecas necessárias para abrir o aplicativo.

Esse passo normalmente precisa ser feito apenas uma vez no computador.

## Como abrir o aplicativo

No PowerShell, dentro da pasta do projeto, execute:

```powershell
streamlit run annotation_app/app.py
```

Depois disso, o navegador deve abrir automaticamente.

Se não abrir, procure no PowerShell um endereço parecido com este:

```text
http://localhost:8501
```

Copie esse endereço e cole no navegador.

## Criar um novo projeto de anotação

Na barra lateral esquerda do aplicativo:

1. Em "Projeto", escolha `Criar novo`.
2. Em "Nome", digite um nome simples para o projeto.
3. Em "Diretório de imagens", informe a pasta onde estão as imagens.
4. Na tabela de classes, informe o que será anotado.
5. Em "Instruções", escreva ou cole as regras de anotação.
6. Clique em `Criar ou atualizar`.

Exemplo de nome de projeto:

```text
onibus_numeros_fase_1
```

Exemplo de diretório de imagens:

```text
D:\Projetos\imagens_onibus
```

Exemplo de classe única:

| id | name | color |
| --- | --- | --- |
| 0 | NUMERO_ONIBUS | #00c8ff |

O `id` é o número da classe. Para um projeto com apenas um tipo de objeto, use `0`.

## Abrir um projeto já criado

Se o projeto já existir:

1. Abra o aplicativo.
2. Na barra lateral, em "Abrir", escolha o nome do projeto.
3. O aplicativo carregará as imagens e o progresso salvo.

Os projetos ficam salvos dentro da pasta:

```text
D:\Projetos\local-vision-annotator\annotations
```

Cada projeto tem sua própria pasta.

## Como anotar uma imagem

Na tela principal, a imagem aparece à esquerda.

Para criar uma anotação:

1. Clique e segure no canto inicial do objeto.
2. Arraste o mouse até o canto oposto.
3. Solte o mouse para criar a caixa.
4. Confira se a caixa cobre o objeto corretamente.
5. Clique em `Salvar`.

A caixa deve ficar justa ao redor do objeto, sem pegar muito fundo e sem cortar partes importantes.

### O que é uma caixa boa

Uma caixa boa:

- cobre o objeto inteiro;
- não deixa partes importantes para fora;
- não pega muito espaço vazio ao redor;
- segue a regra combinada para aquele projeto.

### O que evitar

Evite:

- caixa muito grande;
- caixa cortando o objeto;
- marcar objetos que as instruções mandam ignorar;
- salvar uma imagem sem conferir se a caixa está no lugar certo.

## Quando usar cada botão

### Salvar

Use `Salvar` quando a imagem tiver uma ou mais caixas corretas.

Depois de salvar, a imagem fica com status `annotated`.

### Sem objeto

Use `Sem objeto` quando a imagem não tiver nada que precisa ser marcado.

Exemplo: o projeto pede número de ônibus, mas a imagem não mostra nenhum número visível.

Esse botão é importante. Imagens sem objeto também ajudam o treino, porque ensinam ao modelo quando ele não deve detectar nada.

### Revisar depois

Use `Revisar depois` quando você estiver em dúvida.

Exemplos:

- imagem muito borrada;
- objeto parcialmente escondido;
- não está claro se aquilo deve ser marcado;
- você quer que outra pessoa confira.

Depois, é possível filtrar pelo status `needs_review` para voltar nessas imagens.

### Pular

Use `Pular` quando a imagem não deve entrar no trabalho agora.

Exemplos:

- imagem corrompida;
- imagem errada;
- imagem fora do escopo;
- caso combinado com a pessoa responsável pelo projeto.

## Como continuar outro dia sem perder progresso

Você pode fazer as anotações por etapas.

O progresso é salvo quando você clica em:

- `Salvar`;
- `Sem objeto`;
- `Revisar depois`;
- `Pular`.

Depois de clicar em um desses botões, aquela imagem fica registrada no projeto.

Para parar:

1. Termine a imagem atual.
2. Clique em `Salvar`, `Sem objeto`, `Revisar depois` ou `Pular`.
3. Feche a aba do navegador.
4. Se quiser, feche também o PowerShell.

Para continuar outro dia:

1. Abra o PowerShell na pasta do projeto.
2. Execute:

```powershell
streamlit run annotation_app/app.py
```

3. Abra o mesmo projeto na barra lateral.
4. Em "Filtro de status", deixe marcado principalmente:

```text
pending
needs_review
```

Assim o aplicativo mostra as imagens que ainda precisam ser feitas ou revisadas.

Importante: se você desenhar uma caixa e fechar o navegador antes de clicar em `Salvar`, essa última caixa não será gravada. Sempre salve antes de parar.

## O que significam os status

| Status | Significado |
| --- | --- |
| `pending` | Imagem ainda não foi anotada. |
| `annotated` | Imagem foi anotada com uma ou mais caixas. |
| `empty` | Imagem foi marcada como sem objeto. |
| `skipped` | Imagem foi pulada. |
| `needs_review` | Imagem precisa ser revisada depois. |

## Conferir o progresso

Na barra lateral, o aplicativo mostra a quantidade de imagens em cada status.

Use esses números para acompanhar o trabalho.

Antes de entregar o dataset, o ideal é que não existam imagens importantes em `pending` ou `needs_review`, a menos que isso tenha sido combinado.

## Exportar o dataset final

Quando terminar as anotações:

1. Abra o projeto no aplicativo.
2. Na barra lateral, abra a seção `Exportar YOLO`.
3. Confira os percentuais:

```text
Train %: 80
Val %: 15
```

O restante vai para teste.

4. Deixe `Incluir imagens vazias` marcado, se a pessoa responsável pelo treino pediu para incluir imagens sem objeto.
5. Clique em `Exportar dataset`.

O aplicativo mostrará uma mensagem parecida com:

```text
Exportado em: D:\Projetos\local-vision-annotator\annotations\nome_do_projeto\exports\yolo_2026_06_19_153000
```

Essa pasta exportada é o dataset pronto para entregar.

## Qual pasta entregar

Depois da exportação, envie a pasta criada dentro de:

```text
annotations\nome_do_projeto\exports
```

Exemplo:

```text
D:\Projetos\local-vision-annotator\annotations\onibus_numeros_fase_1\exports\yolo_2026_06_19_153000
```

Essa pasta deve conter:

```text
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

Envie a pasta `yolo_...` inteira.

## O que não mover durante a anotação

Enquanto o projeto estiver em andamento, evite:

- renomear as imagens;
- mover a pasta das imagens;
- apagar imagens;
- renomear a pasta do projeto dentro de `annotations`;
- editar manualmente arquivos dentro de `labels` ou `metadata`.

O aplicativo guarda o caminho das imagens. Se as imagens forem movidas, ele pode não conseguir encontrá-las.

## Boas práticas para anotar muitas imagens

Para trabalhar com muitas imagens:

1. Faça blocos pequenos, por exemplo 100 ou 200 imagens por vez.
2. Salve cada imagem antes de avançar.
3. Use `Revisar depois` quando tiver dúvida, em vez de tentar resolver tudo na hora.
4. No fim do dia, confira a contagem de progresso.
5. Antes de exportar, revise as imagens com status `needs_review`.

É melhor anotar com calma e consistência do que terminar rápido com caixas mal posicionadas.

## Checklist antes de entregar

Antes de enviar o dataset, confira:

- o projeto correto está aberto;
- não há imagens importantes em `pending`;
- as dúvidas em `needs_review` foram resolvidas;
- imagens sem objeto foram marcadas como `empty`;
- o dataset foi exportado pela seção `Exportar YOLO`;
- a pasta enviada é a pasta `yolo_...` dentro de `exports`.

## Problemas comuns

### O navegador não abriu

Veja se o PowerShell mostrou um endereço como:

```text
http://localhost:8501
```

Copie e cole esse endereço no navegador.

### O comando `streamlit` não funciona

Execute novamente:

```powershell
pip install -r requirements.txt
```

Depois tente abrir o aplicativo de novo:

```powershell
streamlit run annotation_app/app.py
```

### As imagens não aparecem

Confira se o caminho em "Diretório de imagens" está correto.

Depois clique em `Atualizar índice de imagens`.

### Fiz uma caixa errada

Se ainda não salvou, ajuste a anotação na tela ou remova a linha correspondente na tabela de caixas, se necessário.

Se já salvou, abra a imagem novamente pelo filtro de status, corrija as caixas e clique em `Salvar` de novo.

### Fechei o aplicativo sem querer

Abra novamente o aplicativo e selecione o mesmo projeto.

Tudo que foi salvo antes de fechar continuará no projeto.

## Explicação simples dos arquivos gerados

Durante a anotação, o aplicativo cria arquivos internos:

```text
annotations/
  nome_do_projeto/
    project.json
    images_index.json
    labels/
    metadata/
    exports/
```

Você normalmente não precisa mexer nesses arquivos.

Eles servem para o aplicativo lembrar:

- quais imagens existem;
- quais imagens já foram feitas;
- onde estão as caixas desenhadas;
- quais imagens estão vazias;
- quais imagens precisam de revisão.

No final, a pasta importante para envio é a pasta exportada em `exports`.

## Resumo do fluxo de trabalho

1. Abrir o PowerShell.
2. Entrar na pasta `local-vision-annotator`.
3. Rodar `streamlit run annotation_app/app.py`.
4. Criar ou abrir o projeto.
5. Anotar as imagens.
6. Salvar cada imagem.
7. Parar e continuar outro dia se necessário.
8. Revisar pendências.
9. Exportar YOLO.
10. Enviar a pasta `yolo_...` exportada.

