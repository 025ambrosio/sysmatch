@echo off
setlocal EnableExtensions

title Conciliador NF x Etiquetas - Verificar

echo ============================================================
echo  Conciliador NF x Etiquetas
echo  Verificacao local
echo ============================================================
echo.

call :check_url "Backend" "http://localhost:8010/api/health"
call :check_url "Frontend" "http://localhost:8080"

echo.
echo Portas em escuta:
netstat -ano | findstr /R /C:":8010 .*LISTENING" /C:":8080 .*LISTENING"
if errorlevel 1 echo Nenhum processo encontrado nas portas 8010 ou 8080.

echo.
pause
exit /b 0

:check_url
set "LABEL=%~1"
set "URL=%~2"
echo [INFO] Verificando %LABEL% em %URL%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri '%URL%' -UseBasicParsing -TimeoutSec 5; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
    echo [FALHA] %LABEL% nao respondeu.
) else (
    echo [OK] %LABEL% esta respondendo.
)
echo.
exit /b 0
