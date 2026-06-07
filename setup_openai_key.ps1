param(
    [string]$Key = ""
)
if (-not $Key) {
    $Key = Read-Host "Cole sua OPENAI_API_KEY aqui"
}
$secretsDir = ".streamlit"
if (-not (Test-Path $secretsDir)) {
    New-Item -ItemType Directory -Path $secretsDir | Out-Null
}
$content = "OPENAI_API_KEY = `"$Key`""
Set-Content -Path "$secretsDir\secrets.toml" -Value $content -Encoding UTF8
Write-Host "Arquivo .streamlit\secrets.toml criado com sucesso. Nao comite esse arquivo."
