#!/bin/bash
# Project Horizon - DigitalOcean Server Setup Script
# Run this on your new droplet: bash setup-server.sh

set -e

echo "=== Project Horizon Server Setup ==="
echo ""

# Update system
echo "[1/6] Updating system packages..."
apt update && apt upgrade -y

# Install Python and dependencies
echo "[2/6] Installing Python and dependencies..."
apt install -y python3 python3-pip python3-venv ffmpeg git nginx certbot python3-certbot-nginx

# Create app directory
echo "[3/6] Setting up application directory..."
mkdir -p /opt/projecthorizon
cd /opt/projecthorizon

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "[4/6] Installing Python packages..."
pip install --upgrade pip
pip install databento websockets aiohttp requests yt-dlp

# Create systemd services
echo "[5/6] Creating systemd services..."

# Realtime Feed Service
cat > /etc/systemd/system/horizon-realtime.service << 'EOF'
[Unit]
Description=Project Horizon Realtime Feed
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/projecthorizon
Environment="DATABENTO_API_KEY=db-pJKmpW8EMSpyrgnkkBQVFauttkicd"
ExecStart=/opt/projecthorizon/venv/bin/python3 realtime_feed.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Red Folder Service
cat > /etc/systemd/system/horizon-redfolder.service << 'EOF'
[Unit]
Description=Project Horizon Red Folder
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/projecthorizon
Environment="DEEPGRAM_API_KEY=76c2874a31e7f07102d526a6f3bd5f0e949c5281"
ExecStart=/opt/projecthorizon/venv/bin/python3 red_folder_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Nginx configuration
echo "[6/6] Configuring Nginx reverse proxy..."

cat > /etc/nginx/sites-available/projecthorizon << 'EOF'
server {
    listen 80;
    server_name api.projecthorizon.online;

    # Realtime Feed API
    location /api/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
    }

    # Red Folder API
    location /redfolder/ {
        proxy_pass http://127.0.0.1:8081/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
    }
}
EOF

ln -sf /etc/nginx/sites-available/projecthorizon /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Upload your Python scripts to /opt/projecthorizon/"
echo "2. Run: systemctl daemon-reload"
echo "3. Run: systemctl enable horizon-realtime horizon-redfolder"
echo "4. Run: systemctl start horizon-realtime horizon-redfolder"
echo "5. Run: systemctl restart nginx"
echo "6. Point api.projecthorizon.online DNS to this server IP"
echo "7. Run: certbot --nginx -d api.projecthorizon.online (for HTTPS)"
echo ""
