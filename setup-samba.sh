#!/bin/bash


SHARED_DIR="/home/shared/pishare"
SHARE_NAME="pishare"  # Name of the share as seen externally
USERNAME=$(whoami) # MUST be an existing user, $(whoami) to get current user 

HOSTNAME=$(hostname).local


CONFIG_FILE="/etc/samba/smb.conf"
LOCAL_CONFIG_FILE=configs/samba/$(basename "$CONFIG_FILE")


sudo apt update && sudo apt upgrade -y
sudo apt install samba samba-common-bin -y
sudo apt autoremove -y


echo "mkdir -p $SHARED_DIR"

mkdir -p $SHARED_DIR
sudo chown -R $USERNAME:$USERNAME $SHARED_DIR

sudo cp $CONFIG_FILE $CONFIG_FILE.bak
sudo cp $LOCAL_CONFIG_FILE $CONFIG_FILE

sudo smbpasswd -a $USERNAME
sudo smbpasswd -e $USERNAME

sudo systemctl restart smbd
sudo systemctl enable smbd
systemctl status smbd