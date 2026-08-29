# launch the NORMAL Unreal editor for this project, run a python script at startup,
# wait for a completion marker in the log, then leave the editor open.
#   param 1: python script absolute path
#   param 2: marker string to wait for in the log (default JP_..._WROTE/MARKER)
#   param 3: map to open at launch (default /Game/Maps/JP_ElectricFence_Test)
#   param 4: timeout seconds (default 240)
param(
    [Parameter(Mandatory=$true)][string]$Script,
    [string]$Marker,
    [string]$Map = "/Game/Maps/JP_ElectricFence_Test",
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
$Editor = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$Project = "C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58\JurassicPark1993.uproject"
$LogDir = "C:\Users\KASTROE\Downloads\JurassicPark1993_FanGame_UE58\Saved\Logs"
$LogFile = Join-Path $LogDir "JurassicPark1993.log"

# 1. stop any existing editor
Get-Process -Name "UnrealEditor" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# 2. back up / clear the previous log marker region by taking a baseline length
$baseLen = 0
if (Test-Path -LiteralPath $LogFile) { $baseLen = (Get-Item -LiteralPath $LogFile).Length }

# 3. launch the normal editor
$cmdArgs = @("`"$Project`"", "$Map", "-nop4", "-nosplash", "-ExecutePythonScript=`"$Script`"")
$proc = Start-Process -FilePath $Editor -ArgumentList $cmdArgs -PassThru
Write-Output ("LAUNCHED PID=" + $proc.Id)

# 4. poll the log for the marker or a thrown python error
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    if ($proc.HasExited) { Write-Output "EDITOR PROCESS EXITED"; break }
    if (Test-Path -LiteralPath $LogFile) {
        $newLen = (Get-Item -LiteralPath $LogFile).Length
        if ($newLen -gt $baseLen) {
            $tail = Get-Content -LiteralPath $LogFile -Tail 5000 | Select-String -Pattern $Marker -ErrorAction SilentlyContinue
            if ($Marker -and $tail) {
                Write-Output "MARKER FOUND"
                $tail | ForEach-Object { $_.Line }
                break
            }
            $err = Get-Content -LiteralPath $LogFile -Tail 3000 | Select-String -Pattern "Python:.*Traceback|LogPython: Error|Unhandled exception in Python" -ErrorAction SilentlyContinue
            if ($err) {
                Write-Output "PYTHON ERROR DETECTED"
                Get-Content -LiteralPath $LogFile -Tail 4000 | Select-String -Pattern "Python|Traceback|Error" -ErrorAction SilentlyContinue | Select-Object -Last 40 | ForEach-Object { $_.Line }
                break
            }
        }
    }
    Start-Sleep -Seconds 5
}

Write-Output "=== LOG TAIL ==="
Get-Content -LiteralPath $LogFile -Tail 60 -ErrorAction SilentlyContinue | ForEach-Object { $_ }
