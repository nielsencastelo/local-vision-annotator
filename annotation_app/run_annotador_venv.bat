@echo off
setlocal

REM Inicia o anotador web no Windows usando um ambiente virtual (.venv).
REM Edite CUSTOM_VENV abaixo para apontar para um ambiente especifico.
REM Exemplo: set "CUSTOM_VENV=C:\tmp\env"
REM Se deixar vazio, usa/cria um ambiente local em .venv na raiz do projeto.
set "CUSTOM_VENV="

REM Pasta deste script (annotation_app) e raiz do projeto (pasta acima).
set "APP_DIR=%~dp0"
pushd "%APP_DIR%.."
set "PROJECT_ROOT=%CD%"

set "DEFAULT_VENV=%PROJECT_ROOT%\.venv"

if defined CUSTOM_VENV (
    set "VENV_DIR=%CUSTOM_VENV%"
) else if defined ANNOTADOR_VENV (
    set "VENV_DIR=%ANNOTADOR_VENV%"
) else (
    set "VENV_DIR=%DEFAULT_VENV%"
)

set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo.
    echo Ambiente Python nao encontrado em:
    echo %VENV_DIR%
    echo.
    echo Criando ambiente local...

    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv "%VENV_DIR%"
    ) else (
        python -m venv "%VENV_DIR%"
    )

    if errorlevel 1 (
        echo.
        echo ERRO: nao foi possivel criar o ambiente Python.
        echo Instale o Python 3 para Windows e marque "Add python.exe to PATH".
        popd
        pause
        exit /b 1
    )
)

if not exist "%PYTHON_EXE%" (
    echo.
    echo ERRO: Python do ambiente nao encontrado:
    echo %PYTHON_EXE%
    popd
    pause
    exit /b 1
)

echo.
echo Usando ambiente:
echo %VENV_DIR%
echo.
echo Conferindo dependencias...
"%PYTHON_EXE%" -m pip install -r "%PROJECT_ROOT%\requirements.txt"
if errorlevel 1 (
    echo.
    echo ERRO: falha ao instalar/conferir dependencias.
    echo Verifique sua internet ou rode manualmente:
    echo "%PYTHON_EXE%" -m pip install -r "%PROJECT_ROOT%\requirements.txt"
    popd
    pause
    exit /b 1
)

echo.
echo Iniciando o anotador... abra http://localhost:8501 no navegador.
echo Para parar, feche esta janela ou pressione CTRL+C.
echo.
"%PYTHON_EXE%" -m streamlit run "%PROJECT_ROOT%\annotation_app\app.py"

popd
pause
