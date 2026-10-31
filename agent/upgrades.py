"""Level 3 upgrades for the PC agent (Ayan, Module C): freeze the writing process, check backup age.
Tested: picks the process that wrote most in the last second and suspends it (status: stopped)."""
import json, os, time, psutil, subprocess, sys
SAFE = {"system", "explorer.exe", "svchost.exe", "csrss.exe", "winlogon.exe", "systemd", "python.exe"}

def top_writer_now(sample=1.0):
    """The process that wrote the most bytes in the last `sample` seconds (not since boot)."""
    before = {}
    for p in psutil.process_iter(["pid", "name"]):
        try: before[p.pid] = (p, p.io_counters().write_bytes)
        except (psutil.Error, AttributeError): pass
    time.sleep(sample)
    best = None
    for pid, (p, w0) in before.items():
        try:
            d = p.io_counters().write_bytes - w0
            if pid != os.getpid() and p.name().lower() not in SAFE and (best is None or d > best[1]):
                best = (p, d)
        except (psutil.Error, AttributeError): pass
    return best[0] if best and best[1] > 0 else None

def backup_age_days(folder):
    newest = 0
    for root, _, files in os.walk(folder):
        for n in files:
            newest = max(newest, os.path.getmtime(os.path.join(root, n)))
    return None if newest == 0 else round((time.time() - newest) / 86400, 1)

PC_HEALTH_PS = ("$m = Get-MpComputerStatus; "
                "$h = Get-HotFix | Where-Object InstalledOn | Sort-Object InstalledOn -Descending | Select-Object -First 1; "
                "@{defender_on = [bool]$m.AntivirusEnabled; realtime_on = [bool]$m.RealTimeProtectionEnabled; "
                "signature_age_days = [int]$m.AntivirusSignatureAge; "
                "days_since_update = $(if ($h) { [int]((Get-Date) - $h.InstalledOn).TotalDays } else { -1 })} "
                "| ConvertTo-Json -Compress")

def pc_health():
    """Windows only, read-only: virus protection on? signatures fresh? days since the last Windows update.
    Returns a dict, or None (not Windows, or PowerShell/Defender unavailable)."""
    if os.name != "nt":
        return None
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", PC_HEALTH_PS],
                           capture_output=True, text=True, timeout=60)
        h = json.loads(r.stdout.strip())
        if h.get("days_since_update", -1) < 0:
            h["days_since_update"] = None
        return h
    except Exception:
        return None

if __name__ == "__main__":
    w = subprocess.Popen([sys.executable, "-c", "import os,time\nf=open('/tmp/claude-0/-home-claude/18b9976a-7343-53b1-8ba4-d83da710722e/scratchpad/big','wb')\nfor i in range(400):\n f.write(os.urandom(100000)); f.flush(); os.fsync(f.fileno()); time.sleep(0.01)"])
    time.sleep(0.3)
    p = top_writer_now()
    print("top writer pid", p and p.pid, "expected", w.pid)
    if p and p.pid == w.pid:
        p.suspend(); time.sleep(0.2); print("status", p.status()); p.resume()
    w.wait()
