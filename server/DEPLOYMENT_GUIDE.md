# Omni Downloader - Oracle Cloud Server Deployment Guide

This guide details how to deploy the server adapter to your Oracle Cloud Ampere ARM instance.

---

### 1. Prerequisites on the Oracle VM
Once connected via SSH to your Oracle Cloud Ubuntu instance:

```bash
# Update package repositories
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y python3-pip python3-venv ffmpeg git curl debian-keyring debian-archive-keyring apt-transport-https
```

---

### 2. Install Caddy (Automatic HTTPS)
```bash
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

---

### 3. Clone Repository & Setup Virtual Environment
```bash
# Clone to /opt/omni-downloader
sudo git clone https://github.com/hexvish/omni-downloader.git /opt/omni-downloader
sudo chown -R ubuntu:ubuntu /opt/omni-downloader

# Create runtime download directory
sudo mkdir -p /var/lib/omni-downloader/downloads
sudo chown -R ubuntu:ubuntu /var/lib/omni-downloader

# Setup Python Virtual Environment
cd /opt/omni-downloader
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements-server.txt
```

---

### 4. Configure Caddy & DNS
1. Ensure your DuckDNS domain `omnidl.duckdns.org` points to your Oracle VM public IP.
2. Copy the Caddyfile:
```bash
sudo cp /opt/omni-downloader/server/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

---

### 5. Setup Systemd Service (Auto-Start on Boot)
```bash
sudo cp /opt/omni-downloader/server/omni-downloader.service /etc/systemd/system/omni-downloader.service
sudo systemctl daemon-reload
sudo systemctl enable --now omni-downloader
```

---

### 6. Verification
* Check service status: `sudo systemctl status omni-downloader`
* View live logs: `journalctl -u omni-downloader -f`
* Open in browser: `https://omnidl.duckdns.org`
