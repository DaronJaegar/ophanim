"""Network containment (Ayan, Module C): cut the PC off from everything EXCEPT the brain,
so the agent can still report and be released. Needs admin rights. DRY_RUN=1 only prints."""
import platform, subprocess
from common.config import BRAIN_IP, DRY_RUN

def _linux_contain(ip):
    return [
        "nft add table inet chakra",
        "nft add chain inet chakra out '{ type filter hook output priority 0 ; policy drop ; }'",
        "nft add rule inet chakra out oif lo accept",
        f"nft add rule inet chakra out ip daddr {ip} accept",
        "nft add chain inet chakra in '{ type filter hook input priority 0 ; policy drop ; }'",
        "nft add rule inet chakra in iif lo accept",
        f"nft add rule inet chakra in ip saddr {ip} accept",
    ]

def _linux_release():
    return ["nft delete table inet chakra"]

def _windows_contain(ip):
    return [
        f'netsh advfirewall firewall add rule name="chakra-brain-out" dir=out action=allow remoteip={ip}',
        f'netsh advfirewall firewall add rule name="chakra-brain-in" dir=in action=allow remoteip={ip}',
        "netsh advfirewall set allprofiles firewallpolicy blockinbound,blockoutbound",
    ]

def _windows_release():
    return [
        "netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound",
        'netsh advfirewall firewall delete rule name="chakra-brain-out"',
        'netsh advfirewall firewall delete rule name="chakra-brain-in"',
    ]

def _run(cmds):
    for c in cmds:
        if DRY_RUN:
            print("[DRY RUN]", c)
        else:
            subprocess.run(c, shell=True, check=False)
    return cmds

def contain():
    return _run(_windows_contain(BRAIN_IP) if platform.system() == "Windows" else _linux_contain(BRAIN_IP))

def release():
    return _run(_windows_release() if platform.system() == "Windows" else _linux_release())
