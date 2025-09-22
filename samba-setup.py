#!/usr/bin/env python3
import argparse
import getpass
import os
import pwd
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

SMB_CONF = "/etc/samba/smb.conf"
SMB_CONF_BAK = "/etc/samba/smb.conf.bak"


class ManagerError(Exception):
    """Base manager error."""


class Manager:
    """Base manager providing run() which prefixes sudo when needed."""

    def run(self, cmd, check=True, capture_output=False, input=None):
        """
        Run a command (cmd must be a list). If not running as root, prefix with sudo.
        Prints the command before running.
        Returns stdout when capture_output=True.
        """
        if not isinstance(cmd, (list, tuple)):
            raise ValueError("cmd must be a list (e.g. ['ls','-la'])")

        exec_cmd = list(cmd)
        if os.geteuid() != 0:
            exec_cmd = ["sudo"] + exec_cmd

        # Print a readable command
        print("Calling >>", " ".join(exec_cmd))
        try:
            result = subprocess.run(
                exec_cmd, check=check, text=True, capture_output=capture_output, input=input
            )
        except subprocess.CalledProcessError as e:
            raise ManagerError(f"Command failed: {e}") from e

        return result.stdout if capture_output else None

    # Helpers for privileged vs unprivileged file ops
    def privileged_copy(self, src, dst):
        """Copy file: use shutil when root, otherwise run cp via sudo."""
        if os.geteuid() == 0:
            shutil.copy2(src, dst)
        else:
            self.run(["cp", src, dst])

    def privileged_move(self, src, dst):
        if os.geteuid() == 0:
            shutil.move(src, dst)
        else:
            self.run(["mv", src, dst])

    def privileged_write_append(self, path: str, content: str):
        """Append content to path. If root, do direct write; else use sudo tee -a."""
        if os.geteuid() == 0:
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            # tee -a accepts stdin
            self.run(["tee", "-a", path], input=content)

    def privileged_replace_file(self, tmp_src: str, dst: str):
        """Replace dst with tmp_src (atomic-ish). Use move when root, cp via sudo otherwise."""
        if os.geteuid() == 0:
            shutil.move(tmp_src, dst)
        else:
            self.run(["cp", tmp_src, dst])
            os.unlink(tmp_src)


class AptManager(Manager):
    """Handles apt package management tasks (still uses system apt commands)."""

    def is_installed(self, package_name: str) -> bool:
        """Check if a package is installed."""
        try:
            # dpkg -s returns non-zero if not installed
            self.run(["dpkg", "-s", package_name], capture_output=True)
            return True
        except ManagerError:
            return False

    def install(self, package_name: str):
        """Install a package using apt-get."""
        print(f"$ Installing package: {package_name}")
        self.run(["apt-get", "install", "-y", package_name])

    def update(self):
        """apt-get update"""
        print("$ apt update")
        self.run(["apt-get", "update"])

    def upgrade(self):
        """apt-get upgrade"""
        print("$ apt upgrade")
        self.run(["apt-get", "upgrade", "-y"])


class SambaManager(Manager):
    """Encapsulates all Samba share management functionality."""

    def __init__(self, smb_conf=SMB_CONF, smb_conf_bak=SMB_CONF_BAK):
        self.smb_conf = smb_conf
        self.smb_conf_bak = smb_conf_bak

    # ---------- helpers that prefer stdlib when running as root ----------
    def backup_conf(self):
        """Backup smb.conf."""
        if os.path.exists(self.smb_conf):
            print(f"Backing up {self.smb_conf} -> {self.smb_conf_bak}")
            self.privileged_copy(self.smb_conf, self.smb_conf_bak)
        else:
            print(f"Warning: {self.smb_conf} does not exist; skipping backup.")

    def _chown_recursive(self, path: str, username: str):
        """Recursively chown path to username (when root), else fall back to chown -R via run()."""
        self.run(["chown", "-R", f"{username}:{username}", path])

    def _chmod_recursive(self, path: str, mode: int):
        """Recursively set mode; when root use os.chmod on files/dirs, otherwise use chmod -R."""
            self.run(["chmod", "-R", oct(mode)[2:], path])

    # ---------- public methods ----------
    def ensure_system_user(self, username):
        """Create a Linux user if it doesn't exist."""
        try:
            pwd.getpwnam(username)
            print(f"✅ System user '{username}' exists")
        except KeyError:
            print(f"⚠️ System user '{username}' does not exist. Creating...")
            # use adduser to create the account (requires sudo if not root)
            self.run(["adduser", "--gecos", "", "--disabled-password", username])
            print(f"✅ Created system user '{username}'")

    def list_shares(self):
        """Return dict of share_name -> path."""
        shares = {}
        current_share = None
        if not os.path.exists(self.smb_conf):
            return shares
        with open(self.smb_conf, "r", encoding="utf-8") as f:
            for line in f:
                line_strip = line.strip()
                if line_strip.startswith("[") and line_strip.endswith("]"):
                    name = line_strip.strip("[]")
                    if name.lower() != "global":
                        current_share = name
                        shares[current_share] = ""
                elif current_share and line_strip.lower().startswith("path"):
                    m = re.match(r"path\s*=\s*(.*)", line_strip, re.IGNORECASE)
                    if m:
                        shares[current_share] = m.group(1)
        return shares

    def restart_samba(self):
        """Restart the smbd service."""
        self.run(["systemctl", "restart", "smbd"])

    def add_share(self, username: str, shared_dir: str, share_name: str, guest: bool = False):
        """Create a Samba share: create dir, set perms, append smb.conf, optionally add samba user."""
        shared_dir = Path(shared_dir)
        shared_dir.mkdir(parents=True, exist_ok=True)

        if not guest:
            self.ensure_system_user(username)
            self._chown_recursive(str(shared_dir), username)

        # Make writable for guests if desired (777 like before)
        self._chmod_recursive(str(shared_dir), 0o777)

        # Backup config
        self.backup_conf()

        # Build block
        if guest:
            smb_conf_block = f"""

[{share_name}]
   path = {shared_dir}
   browseable = yes
   writeable = yes
   guest ok = yes
   create mask = 0777
   directory mask = 0777
"""
        else:
            smb_conf_block = f"""

[{share_name}]
   path = {shared_dir}
   browseable = yes
   writeable = yes
   only guest = no
   create mask = 0777
   directory mask = 0777
   public = yes
"""

        # Append using privileged method
        self.privileged_write_append(self.smb_conf, smb_conf_block)

        # If not guest, add samba password for user
        if not guest:
            print(f"\nSetting Samba password for user '{username}'...")
            self.run(["smbpasswd", "-a", username])
            self.run(["smbpasswd", "-e", username])

    def remove_share(self, share_name: str):
        """Remove a Samba share from smb.conf (writes a temp file then replaces conf)."""
        if not os.path.exists(self.smb_conf):
            raise ManagerError(f"{self.smb_conf} does not exist")

        self.backup_conf()

        with open(self.smb_conf, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        in_block = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"[{share_name}]"):
                in_block = True
                continue
            # if we're in a block and we find a new [section], stop skipping
            if in_block and stripped.startswith("[") and stripped.endswith("]"):
                in_block = False
            if not in_block:
                new_lines.append(line)

        # Write to temp file
        tmp = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        tmp.writelines(new_lines)
        tmp.close()

        # Replace smb.conf atomically / with privilege
        self.privileged_replace_file(tmp.name, self.smb_conf)

    def interactive_add_share(self):
        """Interactively ask user for share details and create it."""
        username = (
            input(f"Enter Samba username [{getpass.getuser()}]: ").strip() or getpass.getuser()
        )
        shared_dir = (
            input(f"Enter shared directory [/home/{username}/shared]: ").strip()
            or f"/home/{username}/shared"
        )
        share_name = (
            input(f"Enter share name [{Path(shared_dir).name}]: ").strip() or Path(shared_dir).name
        )
        guest_input = input("Is this a guest share (no password)? [y/N]: ").strip().lower()
        guest = guest_input == "y"

        self.add_share(username, shared_dir, share_name, guest)
        self.restart_samba()
        print(f"\n✅ Share [{share_name}] created at {shared_dir}")
        if guest:
            print("🔓 Guest access enabled (no password required)")


def main():
    parser = argparse.ArgumentParser(description="Manage Samba shares")
    parser.add_argument("--username", "-u", help="Samba username (default: current user)")
    parser.add_argument("--shared-dir", "-d", help="Path to the shared directory")
    parser.add_argument("--share-name", "-s", help="Name of the Samba share")
    parser.add_argument("--remove-share", "-r", help="Remove a Samba share by name")
    parser.add_argument("--list-shares", "-l", action="store_true", help="List all shares")
    parser.add_argument("--restart", action="store_true", help="Restart Samba service")
    parser.add_argument(
        "--guest", action="store_true", help="Create a guest share (no password required)"
    )
    args = parser.parse_args()

    apt_manager = AptManager()
    apt_manager.update()
    apt_manager.upgrade()
    apt_manager.install("samba")
    apt_manager.install("samba-common-bin")

    manager = SambaManager()

    # If no arguments provided, go interactive
    if len(vars(args)) == 0 or all(v is False or v is None for v in vars(args).values()):
        manager.interactive_add_share()
        return

    if args.restart:
        manager.restart_samba()
        return

    if args.list_shares:
        shares = manager.list_shares()
        if not shares:
            print("⚠️ No shares defined.")
        else:
            print("📂 Samba shares:")
            for name, path in shares.items():
                print(f"  - {name}: {path}")
        return

    if args.remove_share:
        confirm = input(
            f"⚠️ Are you sure you want to remove the share '{args.remove_share}'? [y/N] "
        ).lower()
        if confirm == "y":
            manager.remove_share(args.remove_share)
            manager.restart_samba()
            print(f"✅ Share '{args.remove_share}' removed.")
        else:
            print("❌ Aborted removal.")
        return

    username = args.username or getpass.getuser()
    shared_dir = args.shared_dir or f"/home/{username}/shared"
    share_name = args.share_name or Path(shared_dir).name or "Shared"

    manager.add_share(username, shared_dir, share_name, guest=args.guest)
    manager.restart_samba()

    print(f"\n✅ Share [{share_name}] created at {shared_dir}")
    if args.guest:
        print("🔓 Guest access enabled (no password required)")


if __name__ == "__main__":
    main()
