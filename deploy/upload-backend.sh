#!/bin/bash
# Upload backend scripts to DigitalOcean droplet
# Usage: ./upload-backend.sh YOUR_DROPLET_IP

if [ -z "$1" ]; then
    echo "Usage: ./upload-backend.sh YOUR_DROPLET_IP"
    echo "Example: ./upload-backend.sh 143.198.123.45"
    exit 1
fi

DROPLET_IP=$1
SCRIPTS_DIR="../scripts"

echo "Uploading backend scripts to $DROPLET_IP..."

# Upload Python scripts
scp $SCRIPTS_DIR/realtime_feed.py root@$DROPLET_IP:/opt/projecthorizon/
scp $SCRIPTS_DIR/red_folder_service.py root@$DROPLET_IP:/opt/projecthorizon/

echo ""
echo "Upload complete! Now SSH into your droplet and run:"
echo "  ssh root@$DROPLET_IP"
echo "  systemctl daemon-reload"
echo "  systemctl restart horizon-realtime horizon-redfolder nginx"
echo ""
