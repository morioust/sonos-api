#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/pi/sonos-api"
SERVICE_NAME="sonos-api"

echo "=== Sonos API Installer ==="

# Check if running as root for systemd setup
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo for systemd installation"
    exit 1
fi

# Create venv and install
echo "Setting up Python environment..."
sudo -u pi python3 -m venv "$APP_DIR/.venv"
sudo -u pi "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u pi "$APP_DIR/.venv/bin/pip" install "$APP_DIR"

# Create static dir for TTS cache
sudo -u pi mkdir -p "$APP_DIR/static"

# Install systemd service
echo "Installing systemd service..."
cp "$APP_DIR/deploy/sonos-api.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo "=== Done ==="
echo "Check status: systemctl status $SERVICE_NAME"
echo "View logs:    journalctl -u $SERVICE_NAME -f"
echo "API docs:     http://$(hostname -I | awk '{print $1}'):5005/docs"
