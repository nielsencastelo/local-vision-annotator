@echo off
setlocal
REM Lanca o anotador web no ambiente conda "evollo".

REM Pasta deste script (annotation_app) e raiz do projeto (pasta acima).
set "APP_DIR=%~dp0"
pushd "%APP_DIR%.."
set "PROJECT_ROOT=%CD%"

REM Ativa o ambiente conda evollo (ja preparado).
REM Tenta o comando moderno e cai para o antigo se necessario.
call conda activate evollo 2>nul
if errorlevel 1 call activate evollo
if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel ativar o ambiente "evollo".
    echo Abra o "Anaconda Prompt" e rode: conda activate evollo
    popd
    pause
    exit /b 1
)

echo Iniciando o anotador... abra http://localhost:8501 no navegador.
echo Para parar, feche esta janela ou pressione CTRL+C.
streamlit run "%PROJECT_ROOT%\annotation_app\app.py"

popd
pause
