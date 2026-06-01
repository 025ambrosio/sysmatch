@echo off
setlocal EnableExtensions

title Conciliador NF x Etiquetas - Instalar tarefa agendada

set "ROOT_DIR=%~dp0"
set "TASK_NAME=Conciliador NF x Etiquetas"
set "START_SCRIPT=%ROOT_DIR%iniciar_conciliador_oculto.ps1"

net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Solicitando permissao de administrador...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

echo ============================================================
echo  Conciliador NF x Etiquetas
echo  Instalacao no Agendador de Tarefas do Windows
echo ============================================================
echo.

if not exist "%START_SCRIPT%" (
    echo [ERRO] O arquivo iniciar_conciliador_oculto.ps1 nao foi encontrado.
    echo Esperado:
    echo %START_SCRIPT%
    echo.
    pause
    exit /b 1
)

echo [INFO] Criando tarefa agendada:
echo %TASK_NAME%
echo.

schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""%START_SCRIPT%""" /RL HIGHEST /F
if errorlevel 1 (
    echo.
    echo [ERRO] Nao foi possivel criar a tarefa agendada.
    echo Tente executar este arquivo clicando com o botao direito e escolhendo "Executar como administrador".
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; Set-ScheduledTask -TaskName '%TASK_NAME%' -Settings $settings | Out-Null"
if errorlevel 1 (
    echo [AVISO] A tarefa foi criada, mas nao foi possivel ajustar as opcoes de energia.
    echo Se estiver em notebook, confira no Agendador de Tarefas se ela pode iniciar usando bateria.
)

echo.
echo [OK] Tarefa agendada criada com sucesso.
echo.
echo A tarefa sera executada automaticamente quando este usuario fizer login no Windows.
echo.
echo Para testar agora, execute:
echo   schtasks /Run /TN "%TASK_NAME%"
echo.
echo Ou reinicie o computador e acesse:
echo   http://localhost:8080
echo.
pause
exit /b 0
