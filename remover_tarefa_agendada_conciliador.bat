@echo off
setlocal EnableExtensions

title Conciliador NF x Etiquetas - Remover tarefa agendada

set "TASK_NAME=Conciliador NF x Etiquetas"

net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Solicitando permissao de administrador...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

echo ============================================================
echo  Conciliador NF x Etiquetas
echo  Remocao do Agendador de Tarefas do Windows
echo ============================================================
echo.

schtasks /Delete /TN "%TASK_NAME%" /F
if errorlevel 1 (
    echo.
    echo [ERRO] Nao foi possivel remover a tarefa ou ela nao existe.
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Tarefa agendada removida.
echo.
pause
exit /b 0
