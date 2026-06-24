@echo off
REM =============================================================================
REM flux.bat — Punto de entrada para Windows
REM =============================================================================

IF NOT EXIST ".venv_win\Scripts\activate.bat" (
    echo [ERROR] El entorno virtual no existe. Ejecuta python install.py primero.
    exit /b 1
)

call .venv_win\Scripts\activate.bat
python main.py %*
