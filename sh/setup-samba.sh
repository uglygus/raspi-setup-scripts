

SHARED_DIR="/home/cooper/shared"

sudo apt update && sudo apt upgrade -y
sudo apt install samba samba-common-bin -y
mkdir -p $SHARED_DIR
sudo chown -R pi:pi $SHARED_DIR

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


print(
""" 
Access the share

From Windows Explorer:
\\raspberrypi\Shared
(or replace raspberrypi with its IP, e.g. \\192.168.1.42\Shared)

From Linux:
smbclient //raspberrypi/Shared -U pi

Or mount with:
sudo mount -t cifs //raspberrypi/Shared /mnt -o username=pi,password=yourpassword
""")