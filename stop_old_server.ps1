# Stop stale GR AMS servers blocking port 5000
Write-Host "Checking port 5000..."
$lines = netstat -ano | Select-String ":5000" | Select-String "LISTENING"
if (-not $lines) {
    Write-Host "Port 5000 is free. Run: python run.py"
    exit 0
}
$pids = $lines | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
foreach ($pid in $pids) {
    Write-Host "Stopping PID $pid ..."
    try {
        Stop-Process -Id $pid -Force -ErrorAction Stop
        Write-Host "  Stopped."
    } catch {
        Write-Host "  Could not stop PID $pid (try Task Manager -> end Python as Administrator)."
    }
}
Start-Sleep -Seconds 2
$left = netstat -ano | Select-String ":5000" | Select-String "LISTENING"
if ($left) {
    Write-Host ""
    Write-Host "Port 5000 still in use. Either:"
    Write-Host "  1. End remaining Python in Task Manager, then run: python run.py"
    Write-Host "  2. Or run python run.py anyway — it will use port 5001 and print the URL."
} else {
    Write-Host "Port 5000 is free. Run: python run.py"
}
