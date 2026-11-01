# Gate 2 hand test of containment on Windows (Ayan, Module C). Run in an Administrator PowerShell
# from the project folder, with the brain running:
#   powershell -ExecutionPolicy Bypass -File agent\hand_test_containment.ps1 -BrainIp <brain laptop IP>
# Uses the real agent/contain.py (DRY_RUN=0 for this run only), checks google.com is blocked and the
# brain is still reachable, then ALWAYS releases. Windows version of hand_test_containment.sh.
param(
    [Parameter(Mandatory = $true)][string]$BrainIp,
    [int]$BrainPort = 8000
)
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this in an Administrator PowerShell (containment needs admin rights).'
}
$Dir = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Dir '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) { throw "No $Py : run agent\install.ps1 first." }

$Recovery = 'netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound'
Write-Host "IF THIS WINDOW IS CLOSED MID-TEST, the PC stays cut off. Recover with:" -ForegroundColor Yellow
Write-Host "  $Recovery" -ForegroundColor Yellow
Write-Host "  netsh advfirewall firewall delete rule name=chakra-brain-out" -ForegroundColor Yellow
Write-Host "  netsh advfirewall firewall delete rule name=chakra-brain-in`n" -ForegroundColor Yellow
$PolicyBefore = (netsh advfirewall show allprofiles firewallpolicy) -join "`n"

$Results = [ordered]@{}
function Reach($h, $p) {
    [bool](Test-NetConnection $h -Port $p -InformationLevel Quiet -WarningAction SilentlyContinue)
}
function Check($name, $ok) {
    $Results[$name] = $ok
    Write-Host ("{0}  {1}" -f ($(if ($ok) { 'PASS' } else { 'FAIL' })), $name) -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
}
function Agent($fn) {           # call the real agent code, with containment really on for this call only
    $env:DRY_RUN = '0'; $env:BRAIN_IP = $BrainIp
    Push-Location $Dir
    try { & $Py -c "from agent.contain import $fn; $fn()" } finally { Pop-Location; Remove-Item Env:DRY_RUN }
}

# Programs with their own "allow outbound" rule are NOT stopped by block-outbound: list them as a warning.
$Bypass = Get-NetFirewallRule -Direction Outbound -Action Allow -Enabled True -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -notlike 'chakra-*' } |
    ForEach-Object { $app = ($_ | Get-NetFirewallApplicationFilter).Program
                     # built-in Windows services (svchost etc.) are expected; show only other programs
                     if ($app -and $app -notin 'Any', 'System' -and $app -notmatch '^(%SystemRoot%|%windir%|C:\\Windows)') {
                         "$($_.DisplayName) -> $app" } } |
    Sort-Object -Unique
if ($Bypass) {
    Write-Host "WARNING: these programs have their own allow-outbound rule and could still reach the internet:" -ForegroundColor Yellow
    $Bypass | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }
}

Write-Host "`n1. Before: internet and brain both reachable"
Check 'google.com:443 reachable before' (Reach 'google.com' 443)
Check "brain ${BrainIp}:$BrainPort reachable before" (Reach $BrainIp $BrainPort)

try {
    Write-Host "`n2. Contain (agent/contain.py, DRY_RUN=0)"
    $t = Measure-Command { Agent 'contain' }
    Write-Host ("   contain commands took {0:N1} s" -f $t.TotalSeconds)
    Start-Sleep -Seconds 2
    Check 'google.com:443 BLOCKED while contained' (-not (Reach 'google.com' 443))
    Check "brain ${BrainIp}:$BrainPort still reachable while contained" (Reach $BrainIp $BrainPort)
}
finally {
    Write-Host "`n3. Release (always runs)"
    try { Agent 'release' } catch { Write-Host "release via agent failed: $_ ; using netsh directly" -ForegroundColor Red }
    netsh advfirewall firewall delete rule name=chakra-brain-out 2>$null | Out-Null
    netsh advfirewall firewall delete rule name=chakra-brain-in 2>$null | Out-Null
    if (((netsh advfirewall show allprofiles firewallpolicy) -join "`n") -match 'BlockOutbound') { cmd /c $Recovery | Out-Null }
}
Start-Sleep -Seconds 2
Check 'google.com:443 reachable again after release' (Reach 'google.com' 443)
if (((netsh advfirewall show allprofiles firewallpolicy) -join "`n") -ne $PolicyBefore) {
    Write-Host "NOTE: firewall policy now differs from before the test (release sets the Windows default)." -ForegroundColor Yellow
}

if ($Results.Values -notcontains $false) { Write-Host "`nALL PASS" -ForegroundColor Green }
else { Write-Host "`nNOT PASSED: $(($Results.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object Key) -join '; ')" -ForegroundColor Red; exit 1 }
