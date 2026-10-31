# One-line install of the PC agent on Windows (Ayan, Module C). Run in an Administrator PowerShell:
#   powershell -ExecutionPolicy Bypass -File agent\install.ps1 -BrainIp 192.168.1.10 [-Service]
# Makes .venv, writes .env (DRY_RUN=1), makes the test folder. -Service installs a Windows service
# with NSSM (https://nssm.cc, nssm.exe on PATH) so the agent starts at boot.
param(
    [Parameter(Mandatory = $true)][string]$BrainIp,
    [switch]$Service
)
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this in an Administrator PowerShell (containment needs admin rights).'
}
$Dir = Split-Path -Parent $PSScriptRoot
$Watch = Join-Path $env:USERPROFILE 'ClinicFiles'
$Py = Join-Path $Dir '.venv\Scripts\python.exe'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Install Python 3.11+ from python.org first.' }
if (-not (Test-Path $Py)) { python -m venv (Join-Path $Dir '.venv') }
& $Py -m pip install -q -r (Join-Path $Dir 'requirements.txt')

$EnvFile = Join-Path $Dir '.env'
if (-not (Test-Path $EnvFile)) {
    @(
        "BRAIN_URL=http://${BrainIp}:8000",
        "BRAIN_IP=$BrainIp",
        'DEVICE_ID=frontdesk-pc',
        "WATCH_DIR=$Watch",
        'DRY_RUN=1',
        'AGENT_TOKEN=',
        'SUSPEND=1',
        'SIGNAL_METER=1'
    ) | Set-Content -Encoding ascii $EnvFile
    Write-Host "Wrote $EnvFile (DRY_RUN=1). Paste the brain's AGENT_TOKEN into it if the brain uses one."
} else {
    Write-Host "$EnvFile already exists: left unchanged."
}

if (-not (Test-Path $Watch)) { Push-Location $Dir; & $Py -m agent.testfolder make $Watch; Pop-Location }

# Containment uses Windows Firewall: make sure every profile is on.
netsh advfirewall set allprofiles state on | Out-Null

if ($Service) {
    if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) { throw 'nssm.exe not found on PATH (https://nssm.cc).' }
    nssm install ChakravyuhAgent $Py '-m' 'agent.agent' | Out-Null
    nssm set ChakravyuhAgent AppDirectory $Dir | Out-Null
    nssm set ChakravyuhAgent AppEnvironmentExtra 'SIGNAL_METER=0' | Out-Null
    nssm start ChakravyuhAgent | Out-Null
    Write-Host 'Service ChakravyuhAgent started (stop: nssm stop ChakravyuhAgent).'
} else {
    Write-Host "Next: in this Administrator window, cd $Dir and run: $Py -m agent.agent"
    Write-Host 'Note: python.exe is in SAFE in agent\upgrades.py, so the fake ransomware is never suspended on Windows.'
}
