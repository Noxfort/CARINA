---
tags: [deployment, packaging, docker, debian, systemd]
aliases: [Deployment Guide, Packaging, Docker, Systemd]
---

# 🚀 Deployment, Packaging & Enterprise Containerization

This document details production deployment options for CARINA, including Systemd service setup, Docker containerization, Debian `.deb` packaging, and PyInstaller freezing.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md)

---

## 1. Production Docker Containerization (`Dockerfile.build`)

CARINA includes an optimized multi-stage build `Dockerfile.build` for GPU-accelerated container execution.

### 1.1 Build Docker Image
```bash
docker build -f Dockerfile.build -t carina-core:latest .
```

### 1.2 Run Container with GPU Acceleration
```bash
docker run -d \
  --name carina_app \
  --gpus all \
  -p 50051:50051 \
  -p 8001:8001 \
  -v /var/log/carina:/app/logs \
  carina-core:latest
```

---

## 2. Linux Systemd Daemon Configuration

To run CARINA as a system daemon on Ubuntu/Debian Linux:

Create `/etc/systemd/system/carina.service`:

```ini
[Unit]
Description=CARINA AI Real-Time Traffic Orchestrator
After=network.target postgresql.service

[Service]
Type=simple
User=carina
WorkingDirectory=/opt/carina
ExecStart=/usr/bin/python3 /opt/carina/carina.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable carina
sudo systemctl start carina
```

---

## 3. Building Debian Installers (`build_installer.sh`)

To build native `.deb` installation packages for Linux distributions:

```bash
chmod +x build_installer.sh
./build_installer.sh
```

The script packages binaries, systemd units, configuration templates, and desktop shortcuts into a production `.deb` package.
