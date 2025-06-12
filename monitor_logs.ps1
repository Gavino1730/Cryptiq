# PowerShell script to monitor Cryptiq bot logs in real time
# Usage: Right-click and 'Run with PowerShell' or run in terminal

# Monitor both the main log and error log
Write-Host "Monitoring cryptiq.log and error_log.json. Press Ctrl+C to stop."

Get-Content -Path "cryptiq.log" -Wait -Tail 20 | ForEach-Object { Write-Host "[cryptiq.log] $_" }
Get-Content -Path "error_log.json" -Wait -Tail 20 | ForEach-Object { Write-Host "[error_log.json] $_" }
