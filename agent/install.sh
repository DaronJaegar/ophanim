#!/usr/bin/env bash
# One-line install of the PC agent on Linux (Ayan, Module C).
#   sudo bash agent/install.sh <brain-ip> [--service]
# Installs packages, makes .venv, writes .env (DRY_RUN=1), makes the test folder.
# --service also installs a systemd service so the agent starts at boot (stop: systemctl stop chakravyuh-agent).
set -euo pipefail
IP="${1:?usage: sudo bash agent/install.sh <brain-ip> [--service]}"
SERVICE="${2:-}"
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="${SUDO_USER:-$(whoami)}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"
WATCH="$USER_HOME/ClinicFiles"

apt-get update -qq
apt-get install -y -qq git curl nftables python3-venv python3-pip >/dev/null
sudo -u "$USER_NAME" python3 -m venv "$DIR/.venv"
sudo -u "$USER_NAME" "$DIR/.venv/bin/pip" install -q -r "$DIR/requirements.txt"

if [ ! -f "$DIR/.env" ]; then
  TOKEN_LINE="AGENT_TOKEN="
  cat > "$DIR/.env" <<EOF
BRAIN_URL=http://$IP:8000
BRAIN_IP=$IP
DEVICE_ID=frontdesk-pc
WATCH_DIR=$WATCH
DRY_RUN=1
$TOKEN_LINE
SUSPEND=1
SIGNAL_METER=1
EOF
  chown "$USER_NAME" "$DIR/.env"
  echo "Wrote $DIR/.env (DRY_RUN=1). Paste the brain's AGENT_TOKEN into it if the brain uses one."
else
  echo "$DIR/.env already exists: left unchanged."
fi

[ -d "$WATCH" ] || sudo -u "$USER_NAME" "$DIR/.venv/bin/python" -m agent.testfolder make "$WATCH"

if [ "$SERVICE" = "--service" ]; then
  cat > /etc/systemd/system/chakravyuh-agent.service <<EOF
[Unit]
Description=Chakravyuh PC agent
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$DIR
Environment=SIGNAL_METER=0
ExecStart=$DIR/.venv/bin/python -m agent.agent
Restart=on-failure
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now chakravyuh-agent
  echo "Service running: journalctl -u chakravyuh-agent -f   (stop: systemctl stop chakravyuh-agent)"
else
  echo "Next: sudo bash agent/hand_test_containment.sh $IP   then   sudo -E $DIR/.venv/bin/python -m agent.agent"
fi
