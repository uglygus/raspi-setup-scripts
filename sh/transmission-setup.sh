 
 
 
sudo apt update && sudo apt upgrade -y

sudo apt install transmission-daemon -y
sudo mkdir -p /media/external-drive/torrent-inprogress
sudo mkdir -p /media/external-drive/torrent-complete

sudo chown debian-transmission:debian-transmission /media/external-drive/torrent-inprogress
sudo chown debian-transmission:debian-transmission /media/external-drive/torrent-complete

sudo systemctl stop transmission-daemon

sudo nano /etc/transmission-daemon/settings.json
#Update thee following lines:
#    "incomplete-dir": "/media/external-drive/torrent-inprogress",
#    "incomplete-dir-enabled": true,
#    "download-dir": "/media/external-drive/torrent-complete",

sudo systemctl start transmission-daemon