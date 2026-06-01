@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Conciliador NF x Etiquetas - Parar

set "ROOT_DIR=%~dp0"
set "PID_DIR=%ROOT_DIR%.runtime"
set "BACKEND_PID=%PID_DIR%\backend.pid"
set "FRONTEND_PID=%PID_DIR%\frontend.pid"

echo ============================================================
echo  Conciliador NF x Etiquetas
echo  Encerramento local
echo ============================================================
echo.

call :stop_pid "%BACKEND_PID%" "backend"
call :stop_pid "%FRONTEND_PID%" "frontend"

echo [INFO] Verificando processos nas portas 8010 e 8080...
call :stop_port 8010
call :stop_port 8080

echo.
echo [OK] Encerramento solicitado.
echo Se alguma janela ainda estiver aberta, ela pode ser fechada manualmente.
echo.
pause
exit /b 0

:stop_pid
set "PID_FILE=%~1"
set "LABEL=%~2"
if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    if defined PID (
        echo [INFO] Parando %LABEL% pelo PID !PID!...
        taskkill /PID !PID! /T /F >nul 2>&1
    )
    del "%PID_FILE%" >nul 2>&1
) else (
    echo [INFO] Nenhum PID salvo para %LABEL%.
)
exit /b 0

:stop_port
set "PORT=%~1"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    echo [INFO] Encerrando processo na porta %PORT% com PID %%P...
    taskkill /PID %%P /T /F >nul 2>&1
)
exit /b 0
