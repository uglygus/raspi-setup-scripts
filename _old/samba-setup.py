#!/usr/bin/env python3
import argparse
import getpass
import re
import subprocess
import tempfile
from pathlib import Path

SMB_CONF = "/etc/samba/smb.conf"
SMB_CONF_BAK = "/etc/samba/smb.conf.bak"


def run(cmd, **kwargs):
    """
    Run a shell command, printing it first.
    """
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def backup_conf():
    """
      $ sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
    """
    run(["sudo", "cp", SMB_CONF, SMB_CONF_BAK])


def add_share(username, shared_dir, share_name):
    """
    
    """
    shared_dir.mkdir(parents=True, exist_ok=True)
    run(["sudo", "chown", "-R", f"{username}:{username}", str(shared_dir)])
    backup_conf()
    smb_conf = f"""
[{share_name}]
   path = {shared_dir}
   browseable = yes
   writeable = yes
   only guest = no
   create mask = 0777
   directory mask = 0777
   public = yes
"""
    run(["sudo", "tee", "-a", SMB_CONF], input=smb_conf.encode())
    print(f"\nSetting Samba password for user '{username}'...")
    run(["sudo", "smbpasswd", "-a", username])
    run(["sudo", "smbpasswd", "-e", username])


def remove_share(share_name):
    backup_conf()
    with open(SMB_CONF, "r") as f:
        lines = f.readlines()
    new_lines = []
    in_block = False
    for line in lines:
        if line.strip().startswith(f"[{share_name}]"):
            in_block = True
            continue
        if in_block and line.strip().startswith("[") and line.strip().endswith("]"):
            in_block = False
        if not in_block:
            new_lines.append(line)
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.writelines(new_lines)
        tmp_path = tmp.name
    run(["sudo", "cp", tmp_path, SMB_CONF])
    Path(tmp_path).unlink(missing_ok=True)
    print(f"✅ Removed share [{share_name}] from {SMB_CONF}")


def list_shares():
    shares = {}
    current_share = None
    with open(SMB_CONF, "r") as f:
        for line in f:
            line_strip = line.strip()
            if line_strip.startswith("[") and line_strip.endswith("]"):
                name = line_strip.strip("[]")
                if name.lower() != "global":
                    current_share = name
                    shares[current_share] = ""
            elif current_share and line_strip.lower().startswith("path"):
                path_match = re.match(r"path\s*=\s*(.*)", line_strip, re.IGNORECASE)
                if path_match:
                    shares[current_share] = path_match.group(1)
    if shares:
        print("📂 Current Samba shares:")
        for name, path in shares.items():
            print(f"  - {name}: {path}")
    else:
        print("⚠️  No shares defined (other than [global]).")


def restart_samba():
    run(["sudo", "systemctl", "restart", "smbd"])
    print("✅ Samba service restarted.")


def main():
    parser = argparse.ArgumentParser(
        description="Setup, remove, list, or restart Samba shares on Raspberry Pi"
    )
    parser.add_argument("--username", "-u", help="Samba username (default: current login user)")
    parser.add_argument(
        "--shared-dir", "-d", help="Path to the shared directory (when creating a share)"
    )
    parser.add_argument("--share-name", "-s", help="Name of the Samba share (default: 'Shared')")
    parser.add_argument("--remove-share", "-r", help="Remove a Samba share by name")
    parser.add_argument(
        "--list-shares", "-l", action="store_true", help="List all Samba shares with paths"
    )
    parser.add_argument("--restart", action="store_true", help="Restart the Samba service")
    args = parser.parse_args()

    if args.restart:
        restart_samba()
        return

    if args.list_shares:
        list_shares()
        return

    if args.remove_share:
        remove_share(args.remove_share)
        restart_samba()
        return

    # Otherwise: create a new share
    default_user = getpass.getuser()
    username = (
        args.username or input(f"Enter Samba username [{default_user}]: ").strip() or default_user
    )
    shared_dir = Path(
        args.shared_dir
        or input(f"Enter shared directory [/home/{default_user}/shared]: ").strip()
        or f"/home/{default_user}/shared"
    )
    share_name = args.share_name or input("Enter share name [Shared]: ").strip() or "Shared"

    run(["sudo", "apt", "update"])
    run(["sudo", "apt", "install", "-y", "samba", "samba-common-bin"])

    add_share(username, shared_dir, share_name)
    restart_samba()

    print(
        f"""
✅ Samba share setup complete!

Access the share:

From Windows Explorer:
  \\\\raspberrypi\\{share_name}
  (or use IP, e.g. \\\\192.168.1.42\\{share_name})

From Linux:
  smbclient //raspberrypi/{share_name} -U {username}

Or mount with:
  sudo mount -t cifs //raspberrypi/{share_name} /mnt -o username={username},password=yourpassword
"""
    )


if __name__ == "__main__":
    main()
