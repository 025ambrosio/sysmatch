$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"
$pidDir = Join-Path $rootDir ".runtime"
$backendPid = Join-Path $pidDir "backend.pid"
$frontendPid = Join-Path $pidDir "frontend.pid"
$backendScript = Join-Path $rootDir "iniciar_backend_conciliador.bat"
$frontendScript = Join-Path $rootDir "iniciar_frontend_conciliador.bat"

function Stop-WithMessage {
    param([string] $Message)
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Message, "Conciliador NF x Etiquetas", "OK", "Error") | Out-Null
    exit 1
}

if (-not (Test-Path $backendDir -PathType Container)) {
    Stop-WithMessage "A pasta 'backend' nao foi encontrada. Verifique se o script esta na raiz do projeto."
}

if (-not (Test-Path $frontendDir -PathType Container)) {
    Stop-WithMessage "A pasta 'frontend' nao foi encontrada. Verifique se o script esta na raiz do projeto."
}

if (-not (Test-Path (Join-Path $backendDir ".venv\Scripts\activate.bat") -PathType Leaf)) {
    Stop-WithMessage "O ambiente virtual do backend nao foi encontrado em backend\.venv. Instale as dependencias antes de iniciar."
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules") -PathType Container)) {
    Stop-WithMessage "A pasta frontend\node_modules nao foi encontrada. Execute npm install antes de iniciar."
}

New-Item -ItemType Directory -Path $pidDir -Force | Out-Null

$backendArgs = '/c "{0}"' -f $backendScript
$frontendArgs = '/c "{0}"' -f $frontendScript

$backend = Start-Process -FilePath "cmd.exe" -ArgumentList $backendArgs -WindowStyle Hidden -PassThru
$frontend = Start-Process -FilePath "cmd.exe" -ArgumentList $frontendArgs -WindowStyle Hidden -PassThru

Set-Content -Path $backendPid -Value $backend.Id
Set-Content -Path $frontendPid -Value $frontend.Id
