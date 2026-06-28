@echo off
REM Lanca o anotador web de avarias (urubupunga-ml) no ambiente conda "evollo"
cd /d "%~dp0"

REM Ativa o ambiente conda evollo (ja preparado)
call activate evollo
if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel ativar o ambiente "evollo".
    echo Abra o "Anaconda Prompt" e rode: conda activate evollo
    pause
    exit /b 1
)

echo Iniciando o anotador... abra http://localhost:8501 no navegador.
streamlit run annotation_app\app.py
pause
