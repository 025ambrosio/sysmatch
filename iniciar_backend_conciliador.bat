@echo off
setlocal EnableExtensions

title Conciliador NF x Etiquetas - Backend

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"

echo ============================================================
echo  Conciliador NF x Etiquetas - Backend
echo ============================================================
echo.

if not exist "%BACKEND_DIR%\" (
    echo [ERRO] A pasta backend nao foi encontrada.
    goto :erro
)

if not exist "%BACKEND_DIR%\.venv\Scripts\activate.bat" (
    echo [ERRO] O ambiente virtual backend\.venv nao foi encontrado.
    goto :erro
)

cd /d "%BACKEND_DIR%"

echo [INFO] Ativando ambiente virtual...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERRO] Nao foi possivel ativar o ambiente virtual.
    goto :erro
)

echo [INFO] Iniciando FastAPI em http://localhost:8010 ...
echo [INFO] Para parar, use parar_conciliador.bat ou feche esta janela.
echo.

python -m uvicorn api:app --host 0.0.0.0 --port 8010

echo.
echo [ERRO] O backend foi encerrado.
goto :erro

:erro
echo.
echo Revise a mensagem acima. Esta janela ficara aberta para diagnostico.
pause
exit /b 1
