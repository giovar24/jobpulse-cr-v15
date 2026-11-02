@echo off
REM ============================================================
REM JobPulse CR v1.5 - Launcher UI v2 (plana y modular)
REM
REM La UI clasica (jobpulse_v15.ui) sigue intacta en
REM jobpulse-v15.bat. Esta version vive aparte.
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo  JobPulse CR v1.5 - UI v2 (flat)
echo ============================================================
echo.

echo [1/2] Verificando entorno Python...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
    echo     Entorno virtual existe [OK]
) else (
    echo     ERROR: no existe .venv. Ejecuta jobpulse-v15.bat una vez para crearlo.
    pause
    exit /b 1
)

echo [2/2] Lanzando JobPulse CR UI v2...
echo.
echo ============================================================
echo  JobPulse CR v1.5 - UI v2 abierta
echo  - Pesana "Datos crudos": avisos con sus valores originales
echo  - Boton "Actualizar": recarga la vista
echo  - Exportar CSV: vuelca la vista actual a un archivo
echo ============================================================
echo.

"%PYTHON%" -X utf8 -m jobpulse_v15.ui_v2

echo.
echo JobPulse CR UI v2 finalizada.
pause
