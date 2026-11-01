"""Level 3 upgrades for the PC agent (Ayan, Module C): freeze the writing process, check backup age.
Tested on Windows: picks the demo ransomware (not a busier IDE/browser) and suspends it (status: stopped)."""
import json, os, time, psutil, subprocess, sys, tempfile
# Never frozen: the OS, the desktop, the antivirus, and a few busy Windows services.
# python.exe is NOT here: the demo ransomware is a Python script. The agent itself is skipped by pid instead.
SAFE = {"system", "registry", "memory compression", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
        "services.exe", "lsass.exe", "svchost.exe", "explorer.exe", "dwm.exe", "msmpeng.exe", "nissrv.exe",
        "searchindexer.exe", "systemd"}

def _agent_family():
    """The agent's own pid and its Python parents (on Windows the venv launcher starts python.exe as a child)."""
    me = psutil.Process()
    out = {me.pid}
    try:
        for p in me.parents():
            if not p.name().lower().startswith("python"):
                break
            out.add(p.pid)
    except psutil.Error:
        pass
    return out

def _in_folder(p, folder):
    """Does this process point at the watched folder (command line or an open file)?"""
    f = os.path.normcase(os.path.abspath(folder))
    try:
        if any(f in os.path.normcase(a) for a in p.cmdline()):
            return True
        return any(os.path.normcase(o.path).startswith(f) for o in p.open_files())
    except (psutil.Error, OSError):
        return False

def top_writer_now(sample=1.0, folder=None, since=None):
    """The process to freeze: of those that wrote in the last `sample` seconds, first one working in `folder`,
    else one started after `since` (programs already running before the agent are not suspects), else None.
    Without folder/since: simply the top writer (self-test). Raw bytes alone are not enough: a busy browser or
    IDE out-writes the slow demo ransomware, and freezing the wrong program is worse than freezing none."""
    skip = _agent_family()
    before = {}
    for p in psutil.process_iter(["pid", "name"]):
        try: before[p.pid] = (p, p.io_counters().write_bytes)
        except (psutil.Error, AttributeError): pass
    time.sleep(sample)
    writing = []
    for pid, (p, w0) in before.items():
        try:
            d = p.io_counters().write_bytes - w0
            if d > 0 and pid not in skip and p.name().lower() not in SAFE:
                writing.append((d, p))
        except (psutil.Error, AttributeError): pass
    writing.sort(key=lambda x: -x[0])
    if folder is None and since is None:
        return writing[0][1] if writing else None
    if folder:
        for d, p in writing:
            if _in_folder(p, folder):
                return p
    if since:
        for d, p in writing:
            try:
                if p.create_time() >= since:
                    return p
            except psutil.Error:
                pass
    return None

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
    # Self-test (Windows or Linux): a Python child writes fast; it must be picked, frozen and resumed.
    big = os.path.join(tempfile.gettempdir(), "chakravyuh_writer_test.bin")
    w = subprocess.Popen([sys.executable, "-c", f"import os,time\nf=open({big!r},'wb')\nfor i in range(1500):\n f.seek(0); f.write(os.urandom(100000)); f.flush(); os.fsync(f.fileno()); time.sleep(0.01)"])
    time.sleep(0.5)
    expected = {w.pid} | {c.pid for c in psutil.Process(w.pid).children(recursive=True)}   # venv launcher + its child
    p = top_writer_now()
    print("top writer pid", p and p.pid, "expected one of", sorted(expected), "(python.exe)")
    if p and p.pid in expected:
        p.suspend(); time.sleep(0.2); print("status", p.status()); p.resume(); print("PASS")
    else:
        print("FAIL")
    w.wait()
    os.remove(big)
