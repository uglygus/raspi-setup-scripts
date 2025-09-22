#!/bin/sh


SHARED_DIR="/home/cooper/shared"
USERNAME="cooper"


sudo apt update && sudo apt upgrade -y
sudo apt install samba samba-common-bin -y

mkdir -p $SHARED_DIR
sudo chown -R $USERNAME:$USERNAME $SHARED_DIR

sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
sudo tee -a /etc/samba/smb.conf > /dev/null <<EOF

[pishare]
   path = $SHARED_DIR
   browseable = yes
   writeable = yes
   only guest = no
   create mask = 0777
   directory mask = 0777
   public = yes
EOF

   sudo smbpasswd -a cooper
   sudo smbpasswd -e cooper

   sudo systemctl restart smbd


cat <<'EOF'

Access the share:
Windows Explorer:
\\raspberrypi\Shared
(or replace raspberrypi with its IP, e.g. \\192.168.1.42\Shared)

Linux commandline:
smbclient //raspberrypi/Shared -U pi

MacOS or Linux mount with:
sudo mount -t cifs //raspberrypi/Shared /mnt -o username=pi,password=yourpassword

EOF