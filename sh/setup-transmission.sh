#!/bin/sh

TORRENTING_DIR="/home/cooper/torrenting"
COMPLETED_DIR="$TORRENTING_DIR/complete"
INPROGRESS_DIR="$TORRENTING_DIR/inprogress"
TORRENTS_DIR="$TORRENTING_DIR/torrents"
 
sudo apt update && sudo apt upgrade -y

sudo apt install transmission-daemon -y

mkdir -p $TORRENTS_DIR
mkdir -p $COMPLETED_DIR
mkdir -p $INPROGRESS_DIR
mkdir -p $TORRENTS_DIR

sudo chown debian-transmission:debian-transmission $INPROGRESS_DIR
sudo chown debian-transmission:debian-transmission $COMPLETED_DIR

sudo systemctl stop transmission-daemon

#sudo nano /etc/transmission-daemon/settings.json
#Update thee following lines:
#    "incomplete-dir": "/media/external-drive/torrent-inprogress",
#    "incomplete-dir-enabled": true,
#    "download-dir": "/media/external-drive/torrent-complete",

#sudo systemctl start transmission-daemon