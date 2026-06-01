@echo off
setlocal EnableExtensions

title Conciliador NF x Etiquetas - Frontend

set "ROOT_DIR=%~dp0"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

echo ============================================================
echo  Conciliador NF x Etiquetas - Frontend
echo ============================================================
echo.

if not exist "%FRONTEND_DIR%\" (
    echo [ERRO] A pasta frontend nao foi encontrada.
    goto :erro
)

if not exist "%FRONTEND_DIR%\node_modules\" (
    echo [ERRO] A pasta frontend\node_modules nao foi encontrada.
    goto :erro
)

cd /d "%FRONTEND_DIR%"

if not exist "%FRONTEND_DIR%\dist\index.html" (
    echo [INFO] Build do frontend nao encontrado. Gerando dist...
    npm.cmd run build
    if errorlevel 1 (
        echo [ERRO] Nao foi possivel gerar o build do frontend.
        goto :erro
    )
    echo.
)

echo [INFO] Iniciando Vite Preview em http://localhost:8080 ...
echo [INFO] Para parar, use parar_conciliador.bat ou feche esta janela.
echo.

npm.cmd run preview -- --host 0.0.0.0 --port 8080

echo.
echo [ERRO] O frontend foi encerrado.
goto :erro

:erro
echo.
echo Revise a mensagem acima. Esta janela ficara aberta para diagnostico.
pause
exit /b 1
