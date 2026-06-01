@echo off
setlocal EnableExtensions

title Conciliador NF x Etiquetas - Inicializador

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "BACKEND_SCRIPT=%ROOT_DIR%iniciar_backend_conciliador.bat"
set "FRONTEND_SCRIPT=%ROOT_DIR%iniciar_frontend_conciliador.bat"

echo ============================================================
echo  Conciliador NF x Etiquetas
echo  Inicializacao local para Windows
echo ============================================================
echo.
echo Pasta do sistema:
echo %ROOT_DIR%
echo.

if not exist "%BACKEND_DIR%\" (
    echo [ERRO] A pasta "backend" nao foi encontrada.
    echo Verifique se este arquivo esta na raiz do projeto.
    goto :erro
)

if not exist "%FRONTEND_DIR%\" (
    echo [ERRO] A pasta "frontend" nao foi encontrada.
    echo Verifique se este arquivo esta na raiz do projeto.
    goto :erro
)

if not exist "%BACKEND_DIR%\.venv\Scripts\activate.bat" (
    echo [ERRO] O ambiente virtual do backend nao foi encontrado.
    echo Esperado: backend\.venv\Scripts\activate.bat
    echo.
    echo Solucao:
    echo   cd backend
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    goto :erro
)

if not exist "%FRONTEND_DIR%\node_modules\" (
    echo [ERRO] As dependencias do frontend nao foram encontradas.
    echo Esperado: frontend\node_modules
    echo.
    echo Solucao:
    echo   cd frontend
    echo   npm install
    goto :erro
)

echo [OK] Estrutura validada.
echo [INFO] Iniciando backend na porta 8010...
start "Conciliador Backend" /min "%BACKEND_SCRIPT%"

echo [INFO] Iniciando frontend na porta 8080...
start "Conciliador Frontend" /min "%FRONTEND_SCRIPT%"

echo.
echo [OK] Comandos de inicializacao enviados.
echo.
echo Acesse no computador principal:
echo   http://localhost:8080
echo.
echo Para verificar:
echo   verificar_conciliador.bat
echo.
echo Para parar:
echo   parar_conciliador.bat
echo.
echo Dica: as janelas foram abertas minimizadas. Aguarde alguns segundos antes de acessar.
echo.
pause
exit /b 0

:erro
echo.
echo A inicializacao foi interrompida. Corrija o item acima e tente novamente.
echo.
pause
exit /b 1
