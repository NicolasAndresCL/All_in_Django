@echo off
REM ============================================================================
REM  run_app.bat - Levanta la API Django y la UI Streamlit de All in Django.
REM
REM  Flujo:
REM    1. Localiza la raiz del proyecto y su entorno virtual (env\).
REM    2. Activa el env (falla claro si no existe).
REM    3. Ejecuta run_ui.py, que orquesta el resto:
REM         - levanta la API Django (migrate + runserver) y espera a que responda,
REM         - luego abre la UI Streamlit (puerto 8501 o el siguiente libre).
REM
REM  La API corre como subproceso de la UI: al cerrar la UI, la API se detiene sola.
REM ============================================================================
setlocal

REM -- Rutas: este .bat vive en streamlit_ui\; la raiz es su carpeta padre -------
set "UI_DIR=%~dp0"
pushd "%UI_DIR%.."
set "ROOT=%CD%"
popd
set "VENV=%ROOT%\env"
set "PY=%VENV%\Scripts\python.exe"

REM -- 1) Reconocer el entorno virtual ------------------------------------------
if not exist "%VENV%\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual en: %VENV%
    echo         Crealo con:  python -m venv env
    echo         e instala:   env\Scripts\activate ^&^& pip install -r requirements-dev.txt
    exit /b 1
)
if not exist "%ROOT%\manage.py" (
    echo [ERROR] No se encontro manage.py en: %ROOT%
    exit /b 1
)

echo [1/2] Activando entorno virtual...
call "%VENV%\Scripts\activate.bat"

REM -- 2) Orquestar API + UI (run_ui.py hace migrate, runserver y luego Streamlit)
echo [2/2] Levantando API Django y UI Streamlit...
"%PY%" "%UI_DIR%run_ui.py"

endlocal
