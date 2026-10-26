<#
Shares the local PlacementIQ app on a temporary public HTTPS URL (a Cloudflare quick tunnel),
for a demo on a phone or another machine. Run scripts\tunnel.bat, or:
    powershell -ExecutionPolicy Bypass -File scripts\tunnel.ps1 [-Port 8501]
Needs cloudflared on PATH. There is no login: anyone with the URL can use the app and, in live
mode, spend the Groq quota. Close the window (or press Ctrl+C) when the demo ends.
#>
param (
    [int]$Port = 8501
)

$root = Split-Path -Parent $PSScriptRoot

function Test-Port([int]$p) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { return $client.ConnectAsync("127.0.0.1", $p).Wait(500) }
    catch { return $false }
    finally { $client.Dispose() }
}

Write-Host "PlacementIQ - public demo tunnel" -ForegroundColor Cyan

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] cloudflared is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Download it from https://github.com/cloudflare/cloudflared/releases" -ForegroundColor Yellow
    exit 1
}

$server = $null
if (Test-Port $Port) {
    Write-Host "[OK] Using the app already running on port $Port." -ForegroundColor Green
    Write-Host "     If uploads fail through the tunnel, stop it and run this script again." -ForegroundColor Yellow
} else {
    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = "python" }
    # Some proxies trip Streamlit's same-origin checks (the upload XSRF token, WebSocket CORS).
    # They are lifted for this tunnelled process only; .streamlit/config.toml keeps them on.
    $server = Start-Process -FilePath $python -WorkingDirectory $root -PassThru -ArgumentList @(
        "-m", "streamlit", "run", "app.py", "--server.port", "$Port", "--server.headless", "true",
        "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"
    )
    Write-Host "Starting Streamlit on port $Port in its own window ..."
    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Test-Port $Port)) {
        if ($server.HasExited -or (Get-Date) -gt $deadline) {
            Write-Host "[ERROR] Streamlit did not start; see its window for the error." -ForegroundColor Red
            exit 1
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host "[OK] Streamlit is running." -ForegroundColor Green
}

Write-Host "Starting the tunnel. The public https://...trycloudflare.com URL appears below." -ForegroundColor Cyan
try {
    & cloudflared tunnel --url "http://localhost:$Port"
} finally {
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id }
}
