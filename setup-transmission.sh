#!/bin/sh

# --- Raspberry Pi check ---
if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model)
    case "$MODEL" in
        *"Raspberry Pi"*)
            echo "✅ Running on Raspberry Pi: $MODEL"
            ;;
        *)
            echo "⚠️  Warning: This script is intended for Raspberry Pi only."
            echo "Detected model: $MODEL"
            exit 1
            ;;
    esac
else
    echo "⚠️  Warning: This script is intended for Raspberry Pi only."
    echo "    Could not detect hardware model."
    exit 1
fi



TORRENTING_DIR="/home/shared/pishare/torrenting"
COMPLETED_DIR="$TORRENTING_DIR/complete"
INPROGRESS_DIR="$TORRENTING_DIR/inprogress"
TORRENTS_DIR="$TORRENTING_DIR/torrents"
 
CONFIG_FILE="/etc/transmission-daemon/settings.json"
LOCAL_CONFIG_FILE=configs/transmission/$(basename "$CONFIG_FILE")


sudo apt update && sudo apt upgrade -y
sudo apt install transmission-daemon -y
sudo apt autoremove -y

sudo systemctl stop transmission-daemon

mkdir -p $TORRENTS_DIR
mkdir -p $COMPLETED_DIR
mkdir -p $INPROGRESS_DIR
mkdir -p $TORRENTS_DIR

# Add the 'pi' user to the 'debian-transmission' group
sudo usermod -aG debian-transmission pi
sudo chmod g+s /home/shared/pishare/torrenting/torrents

sudo chown -R debian-transmission:debian-transmission $TORRENTING_DIR
sudo chmod -R 775 /home/shared/pishare/torrenting


sudo cp $CONFIG_FILE $CONFIG_FILE.bak
sudo cp $LOCAL_CONFIG_FILE $CONFIG_FILE

sudo systemctl start transmission-daemon
sudo systemctl enable transmission-daemon
systemctl status transmission-daemon