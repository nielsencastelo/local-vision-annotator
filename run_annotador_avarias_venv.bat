@echo off
setlocal

REM Inicia o anotador web de avarias no Windows 11.
REM Edite CUSTOM_VENV abaixo para apontar para um ambiente especifico.
REM Exemplo: set "CUSTOM_VENV=C:\tmp\env"
REM Se deixar vazio, usa/cria um ambiente local em .venv nesta pasta.
set "CUSTOM_VENV="

cd /d "%~dp0"

set "APP_DIR=%~dp0"
set "DEFAULT_VENV=%APP_DIR%.venv"

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
        pause
        exit /b 1
    )
)

if not exist "%PYTHON_EXE%" (
    echo.
    echo ERRO: Python do ambiente nao encontrado:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

echo.
echo Usando ambiente:
echo %VENV_DIR%
echo.
echo Conferindo dependencias...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERRO: falha ao instalar/conferir dependencias.
    echo Verifique sua internet ou rode manualmente:
    echo "%PYTHON_EXE%" -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Iniciando o anotador... abra http://localhost:8501 no navegador.
echo Para parar, feche esta janela ou pressione CTRL+C.
echo.
"%PYTHON_EXE%" -m streamlit run annotation_app\app.py

pause