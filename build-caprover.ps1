# build-caprover.ps1
# Gera um TAR com os arquivos necessários para deploy no CapRover.
# O arquivo é salvo em /dist com timestamp no nome.

$timestamp      = Get-Date -Format "yyyyMMdd-HHmmss"
$distDir        = Join-Path $PSScriptRoot "dist"
$outputFile     = Join-Path $distDir "deploy-$timestamp.tar"
$outputFileRel  = "dist\deploy-$timestamp.tar"   # path relativo para o tar.exe do Windows
$tarExe         = "$env:SystemRoot\System32\tar.exe"  # força o tar nativo do Windows (evita WSL)

# Cria a pasta /dist se não existir
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
    Write-Host "Pasta /dist criada."
}

# Garante que o tar roda a partir da raiz do projeto
Push-Location $PSScriptRoot

try {
    $tarArgs = @(
        "-cf", $outputFileRel,
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=*.pyo",
        "captain-definition",
        "Dockerfile",
        "requirements.txt",
        "README.md",
        "app",
        "docs"
    )

    & $tarExe @tarArgs

    if ($LASTEXITCODE -eq 0) {
        $size = (Get-Item $outputFile).Length / 1KB
        Write-Host "TAR criado com sucesso: $outputFile ($([math]::Round($size, 1)) KB)" -ForegroundColor Green
        Write-Host "Para fazer o deploy: caprover deploy --tarFile $outputFile" -ForegroundColor Cyan
    } else {
        Write-Error "Falha ao criar o TAR (exit code $LASTEXITCODE)."
        exit 1
    }
} finally {
    Pop-Location
}