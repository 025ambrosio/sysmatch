$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"
$pidDir = Join-Path $rootDir ".runtime"
$backendPid = Join-Path $pidDir "backend.pid"
$frontendPid = Join-Path $pidDir "frontend.pid"
$backendLog = Join-Path $pidDir "backend.log"
$frontendLog = Join-Path $pidDir "frontend.log"

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

$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$npmCmd = "npm.cmd"

if (-not (Test-Path $backendPython -PathType Leaf)) {
    Stop-WithMessage "Python do ambiente virtual nao foi encontrado em backend\.venv\Scripts\python.exe."
}

if (-not (Test-Path (Join-Path $frontendDir "dist\index.html") -PathType Leaf)) {
    $build = Start-Process `
        -FilePath $npmCmd `
        -ArgumentList @("run", "build") `
        -WorkingDirectory $frontendDir `
        -WindowStyle Hidden `
        -Wait `
        -PassThru `
        -RedirectStandardOutput (Join-Path $pidDir "frontend-build.log") `
        -RedirectStandardError (Join-Path $pidDir "frontend-build.err.log")

    if ($build.ExitCode -ne 0) {
        Stop-WithMessage "Nao foi possivel gerar o build do frontend. Verifique .runtime\frontend-build.err.log."
    }
}

$backend = Start-Process `
    -FilePath $backendPython `
    -ArgumentList @("-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8010") `
    -WorkingDirectory $backendDir `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError (Join-Path $pidDir "backend.err.log")

$frontend = Start-Process `
    -FilePath $npmCmd `
    -ArgumentList @("run", "preview", "--", "--host", "0.0.0.0", "--port", "8080") `
    -WorkingDirectory $frontendDir `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError (Join-Path $pidDir "frontend.err.log")

Set-Content -Path $backendPid -Value $backend.Id
Set-Content -Path $frontendPid -Value $frontend.Id
