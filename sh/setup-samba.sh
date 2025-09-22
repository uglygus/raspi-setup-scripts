#!/bin/sh


SHARED_DIR="/home/cooper/shared"
SHARE_NAME="pishare"  # Name of the share as seen externally
USERNAME= $(whoami) # MUST be an existing user, $(whoami) to get current user 

HOSTNAME=$(hostname).local
SAMBA_CONF="/etc/samba/smb.conf"
SAMBA_CONF_BAK="/etc/samba/smb.conf.bak"

# Global array of substitutions (orig=new)
SUBS=()

queue_replacement() {
  local orig="$1"
  local new="$2"
  SUBS+=("$orig=$new")
}

apply_replacements() {
  local file="$1"
  local tmpfile
  tmpfile=$(mktemp)

  awk -v subs="${SUBS[*]}" '
    BEGIN {
      n = split(subs, arr, " ")
      for (i=1; i<=n; i++) {
        split(arr[i], kv, "=")
        origs[kv[1]] = kv[2]
      }
    }
    {
      for (o in origs) {
        if ($0 ~ "\"" o "\"") {
          sub(/"[^"]*"/, "\"" origs[o] "\"")
        }
      }
      print
    }
  ' "$file" > "$tmpfile"

  mv "$tmpfile" "$file"
}





sudo apt update && sudo apt upgrade -y
sudo apt install samba samba-common-bin -y

mkdir -p $SHARED_DIR
sudo chown -R $USERNAME:$USERNAME $SHARED_DIR

sudo cp $SAMBA_CONF $SAMBA_CONF_BAK

queue_replace "shared" "$SHARE_NAME"
queue_replace "Shared" "$SHARED_DIR"

apply_replacements settings.json


# sudo tee -a /etc/samba/smb.conf > /dev/null <<EOF

# [pishare]
#    path = $SHARED_DIR
#    browseable = yes
#    writeable = yes
#    only guest = no
#    create mask = 0777
#    directory mask = 0777
#    public = yes
# EOF

sudo smbpasswd -a $USERNAME
sudo smbpasswd -e $USERNAME

sudo systemctl restart smbd
sudo systemctl enable smbd

cat <<'EOF'

Access the share:
Windows Explorer:
\\$HOSTNAME\Shared
(or replace $HOSTNAME with its IP, e.g. \\192.168.1.42\Shared)

Linux commandline:
smbclient //$HOSTNAME/Shared -U pi

MacOS or Linux mount with:
sudo mount -t cifs //$HOSTNAME/Shared /mnt -o username=$USERNAME,password=yourpassword

EOF