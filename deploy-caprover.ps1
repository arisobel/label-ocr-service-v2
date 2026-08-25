# deploy-caprover.ps1
# Envia o tarball mais recente de ./dist para o CapRover via CLI.
# Credenciais nao sao gravadas: informe por parametros ou pelas variaveis
# CAPROVER_URL, CAPROVER_APP e CAPROVER_APP_TOKEN (ou via .env).

[CmdletBinding()]
param(
    [string]$CapRoverUrl = $env:CAPROVER_URL,
    [string]$App = $env:CAPROVER_APP,
    [string]$AppToken = $env:CAPROVER_APP_TOKEN,
    [string]$TarFile,
    [switch]$UseSavedConfig
)

$ErrorActionPreference = 'Stop'
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$distDir = Join-Path $scriptRoot 'dist'
$envFile = Join-Path $scriptRoot '.env'

# Carrega somente as tres chaves de deploy do .env local, se ele existir.
# Parametros explicitos e variaveis de ambiente existentes continuam tendo prioridade.
if (Test-Path -LiteralPath $envFile -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        $entry = $line.Trim()
        if (-not $entry -or $entry.StartsWith('#') -or $entry -notmatch '^(CAPROVER_URL|CAPROVER_APP|CAPROVER_APP_TOKEN)=(.*)$') {
            continue
        }

        $key = $matches[1]
        $value = $matches[2].Trim().Trim('"').Trim("'")
        switch ($key) {
            'CAPROVER_URL'       { if ([string]::IsNullOrWhiteSpace($CapRoverUrl)) { $CapRoverUrl = $value } }
            'CAPROVER_APP'       { if ([string]::IsNullOrWhiteSpace($App))         { $App         = $value } }
            'CAPROVER_APP_TOKEN' { if ([string]::IsNullOrWhiteSpace($AppToken))    { $AppToken    = $value } }
        }
    }
}

# Localiza o executavel caprover (suporte a Windows com npm global)
$caproverCommand = Get-Command caprover -ErrorAction SilentlyContinue
if (-not $caproverCommand) {
    $caproverCommand = Get-Command caprover.cmd -ErrorAction SilentlyContinue
}
if (-not $caproverCommand) {
    $npmPrefix = (& npm.cmd prefix -g 2>$null | Select-Object -First 1)
    if ($npmPrefix) {
        $caproverCmdPath = Join-Path $npmPrefix 'caprover.cmd'
        if (Test-Path -LiteralPath $caproverCmdPath -PathType Leaf) {
            $caproverCommand = Get-Item -LiteralPath $caproverCmdPath
        }
    }
}
if (-not $caproverCommand) {
    throw "A CLI do CapRover nao foi encontrada. Instale-a com: npm install -g caprover"
}

$caproverExecutable = $caproverCommand.Source
if ([string]::IsNullOrWhiteSpace($caproverExecutable)) { $caproverExecutable = $caproverCommand.Path }
if ([string]::IsNullOrWhiteSpace($caproverExecutable)) { $caproverExecutable = $caproverCommand.FullName }

# Seleciona o tarball
if ($TarFile) {
    $tarPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($TarFile)
    if (-not (Test-Path -LiteralPath $tarPath -PathType Leaf)) {
        throw "Tarball nao encontrado: $TarFile"
    }
} else {
    $latestTar = Get-ChildItem -LiteralPath $distDir -Filter 'deploy-*.tar' -File -ErrorAction SilentlyContinue |
        Sort-Object -Property LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latestTar) {
        throw "Nenhum tarball 'deploy-*.tar' foi encontrado em $distDir. Execute .\build-caprover.ps1 primeiro."
    }

    $tarPath = $latestTar.FullName
}

Write-Host "Tarball selecionado: $tarPath"

# A CLI do CapRover no Windows concatena o diretorio atual ao caminho do TAR,
# por isso usamos caminho relativo a partir da raiz do projeto.
Push-Location -LiteralPath $scriptRoot
try {
    $tarFileForCli = Resolve-Path -LiteralPath $tarPath -Relative

    if ($UseSavedConfig) {
        Write-Host 'Enviando com a configuracao salva da CLI do CapRover...'
        & $caproverExecutable deploy --default --tarFile $tarFileForCli
    } else {
        if ([string]::IsNullOrWhiteSpace($CapRoverUrl) -or [string]::IsNullOrWhiteSpace($App)) {
            throw 'Informe -CapRoverUrl e -App (ou defina CAPROVER_URL e CAPROVER_APP no .env).'
        }

        $deployArgs = @(
            'deploy',
            '--caproverUrl', $CapRoverUrl,
            '--caproverApp', $App,
            '--tarFile', $tarFileForCli
        )

        if (-not [string]::IsNullOrWhiteSpace($AppToken)) {
            $deployArgs += '--appToken', $AppToken
        } else {
            Write-Host 'Nenhum app token informado; a CLI solicitara a senha do CapRover.'
        }

        Write-Host "Enviando para o app '$App' em $CapRoverUrl..."
        & $caproverExecutable @deployArgs
    }
} finally {
    Pop-Location
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host 'Deploy enviado com sucesso. Acompanhe os logs de build acima ou no painel do CapRover.'
