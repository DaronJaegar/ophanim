#!/usr/bin/env bash
# Hand test of containment on the Linux front-desk PC (Ayan, Module C). Run BEFORE setting DRY_RUN=0.
#   sudo bash agent/hand_test_containment.sh <brain-ip> [port]
# Runs the same 7 nft commands as agent/contain.py, checks google.com fails and the brain still answers,
# then always deletes the table again (also on Ctrl+C or error).
set -u
IP="${1:?usage: sudo bash agent/hand_test_containment.sh <brain-ip> [port]}"
PORT="${2:-8000}"
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
command -v nft >/dev/null || { echo "nft not found: sudo apt install nftables"; exit 1; }

release() { nft delete table inet chakra 2>/dev/null && echo "released: table inet chakra deleted"; }
trap release EXIT

check() {  # $1 label, $2 url, $3 expected: ok|fail
  if curl -s -m 3 -o /dev/null "$2"; then got=ok; else got=fail; fi
  [ "$got" = "$3" ] && echo "PASS  $1 ($got)" || { echo "FAIL  $1 (got $got, want $3)"; FAILED=1; }
}
FAILED=0

echo "== before containment"
check "google reachable" https://google.com ok
check "brain reachable"  "http://$IP:$PORT/graph" ok

echo "== containing (same commands as agent/contain.py)"
nft add table inet chakra
nft add chain inet chakra out '{ type filter hook output priority 0 ; policy drop ; }'
nft add rule inet chakra out oif lo accept
nft add rule inet chakra out ip daddr "$IP" accept
nft add chain inet chakra in '{ type filter hook input priority 0 ; policy drop ; }'
nft add rule inet chakra in iif lo accept
nft add rule inet chakra in ip saddr "$IP" accept

echo "== while contained"
check "google blocked"         https://google.com fail
check "brain still reachable"  "http://$IP:$PORT/graph" ok

echo "== releasing"
release
trap - EXIT
check "google back"  https://google.com ok

[ "$FAILED" -eq 0 ] && echo "ALL PASS: safe to try DRY_RUN=0" || echo "SOME CHECKS FAILED: keep DRY_RUN=1"
exit "$FAILED"
