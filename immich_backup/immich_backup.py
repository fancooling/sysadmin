#!/usr/bin/env python3

"""
################################################################################
# Immich Backup Script
################################################################################

Overview:
---------
This script takes nightly backups of an Immich server running on Docker Compose.
It supports:
  1. Reading configurations from a .env file.
  2. RSYNCing uploading paths to a remote server.
  3. Generating rolling 7z encrypted full & differential local backups.
  4. Automatically starting & stopping the Immich Docker Compose stack to ensure
     data consistency.
  5. Automatically cleaning up old backups.

Requirements:
-------------
- Python 3.6+
- `7z` (p7zip-full)
- `rsync`
- `docker compose`

Setup Instructions:
-------------------
1. Make this script executable: `chmod +x immich_backup.py`
2. Create a configuration `.env` file containing the necessary environment keys
   (see config parser inside script for required keys).
3. Ensure password-less SSH / authorized_keys are configured if you are syncing
   to a remote rsync path `user@server:/path`.

Cron Job Setup (daily execution):
----------------------------------
To run this automatically every day, open crontab: `crontab -e`
Add the following line to run every day at 2:00 AM, pointing logs to /var/log:
0 2 * * * /path/to/immich_backup.py --config /path/to/backup_config.env > /var/log/immich_backup/backup.log 2>&1

To automatically rotate and keep logs for 14 days, set up logrotate
by creating `/etc/logrotate.d/immich-backup` with the following:

/var/log/immich_backup/backup.log {
    daily
    rotate 14
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}

Restore Instructions:
---------------------
1. Bring the new (or existing) Immich server offline (`docker compose down`).
2. Restore your Full Backup FIRST to the target IMMICH_UPLOAD_PATH:
   `7z x immich_full_YYYY-MM-DD.7z -o<IMMICH_UPLOAD_PATH> -p<YOUR_PASSWORD>`
3. If the disaster happened AFTER an incremental backup, restore the LATEST
   incremental backup SECOND, overwriting any matching files:
   `7z x immich_inc_YYYY-MM-DD.7z -o<IMMICH_UPLOAD_PATH> -p<YOUR_PASSWORD> -y`
4. Bring the Immich server online (`docker compose up -d`).

Note: 7z differential backups `(-up0q3r2x2y2z0w2!)` contain ALL changes
since the original full backup. Therefore you ONLY need the Full Backup and
the LATEST Incremental backup to fully restore.
"""

import argparse
import concurrent.futures
import datetime
import json
import logging
import os
import shlex
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def parse_env_file(filepath):
    """Parses a simple .env file into a dictionary."""
    config = {}
    if not os.path.exists(filepath):
        logging.error(f"Configuration file not found: {filepath}")
        sys.exit(1)

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                # Remove surrounding quotes if present
                if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                    val = val[1:-1]
                config[key] = val
    return config


def print_config(config):
    """Prints the config to console, masking sensitive values."""
    logging.info("--- Configuration Loaded ---")
    for key, value in config.items():
        if "PASSWORD" in key.upper():
            logging.info(f"{key} = ***MASKED***")
        else:
            logging.info(f"{key} = {value}")
    logging.info("----------------------------\n")


def run_cmd(cmd, shell=False, fatal=True, timeout=None):
    """Helper to run a subprocess command. Returns True on success, False on
    non-fatal failure/timeout."""
    pretty = cmd if shell else shlex.join(cmd)
    logging.info(f"Running command: {pretty}")
    try:
        subprocess.run(cmd, shell=shell, check=True, timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        msg = f"Command timed out after {timeout}s: {pretty}"
        if fatal:
            logging.error(msg)
            sys.exit(1)
        logging.error(msg + ", continuing anyway...")
        return False
    except subprocess.CalledProcessError as e:
        if fatal:
            logging.error(f"Command failed with exit code {e.returncode}: {e.cmd}")
            sys.exit(e.returncode)
        logging.warning(
            f"Command failed with exit code {e.returncode}: {e.cmd}, continuing anyway..."
        )
        return False


def load_configuration(config_path):
    """Loads, validates, and parses the configuration file."""
    config = parse_env_file(config_path)
    print_config(config)

    # Required Config Keys Extraction
    required_keys = [
        "IMMICH_UPLOAD_PATH",
        "IMMICH_DOCKER_COMPOSE_FILE",
        "LOCAL_BACKUP_PATH",
        "RSYNC_MODULE",
        "RSYNC_PASSWORD_FILE",
        "COMPRESSION_PASSWORD",
        "FULL_BACKUP_INTERVAL",
        "STATE_FILE",
        "OLD_FILE_RETENTION_DAYS",
    ]

    missing_keys = [k for k in required_keys if k not in config]
    if missing_keys:
        logging.error(f"Missing required configuration keys: {missing_keys}")
        sys.exit(1)

    # Convert types
    config["FULL_BACKUP_INTERVAL"] = int(config["FULL_BACKUP_INTERVAL"])
    config["OLD_FILE_RETENTION_DAYS"] = int(config["OLD_FILE_RETENTION_DAYS"])

    return config


def main():
    parser = argparse.ArgumentParser(description="Immich Server Backup Script")
    parser.add_argument(
        "--config", required=True, help="Path to the .env configuration file"
    )
    args = parser.parse_args()

    config = load_configuration(args.config)

    immich_upload = config["IMMICH_UPLOAD_PATH"]
    compose_file = config["IMMICH_DOCKER_COMPOSE_FILE"]
    local_backup_path = config["LOCAL_BACKUP_PATH"]
    rsync_module = config["RSYNC_MODULE"]
    rsync_password_file = config["RSYNC_PASSWORD_FILE"]
    compression_password = config["COMPRESSION_PASSWORD"]
    full_backup_interval = config["FULL_BACKUP_INTERVAL"]
    state_file = config["STATE_FILE"]
    retention_days = config["OLD_FILE_RETENTION_DAYS"]

    # Ensure directories exist
    os.makedirs(local_backup_path, exist_ok=True)
    os.makedirs(os.path.dirname(state_file), exist_ok=True)

    # Sub-folders to backup via 7z
    TARGET_FOLDERS = ["library/", "upload/", "profile/", "backups/"]

    # 1. Terminal vs Cron Check
    if sys.stdin.isatty():
        logging.info("Running in interactive terminal mode.")
        confirm = input("Are you sure you want to proceed with the backup? (y/n): ")
        if confirm.lower() != "y":
            logging.info("Backup cancelled by user.")
            sys.exit(0)
    else:
        logging.info("Running in cron/non-interactive mode. Proceeding automatically.")

    # 2. Determine Backup Type (Full vs Differential)
    now = datetime.datetime.now()
    current_date_str = now.strftime("%Y-%m-%d_%H%M%S")

    state = {}
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                logging.warning("State file corrupted, defaulting to full backup.")

    last_full_ts = state.get("last_full_timestamp", 0)
    last_full_filename = state.get("last_full_filename", "")

    days_since_full = (now.timestamp() - last_full_ts) / 86400
    is_full_backup = False

    if (
        days_since_full >= full_backup_interval
        or not last_full_filename
        or not os.path.exists(os.path.join(local_backup_path, last_full_filename))
    ):
        logging.info("Conditions met for FULL BACKUP.")
        is_full_backup = True
    else:
        logging.info("Conditions met for INCREMENTAL (DIFFERENTIAL) BACKUP.")

    # 3. Shutdown Immich Server
    logging.info("Shutting down Immich server...")
    run_cmd(["docker", "compose", "-f", compose_file, "down"])

    # Steps 4 and 5 run in parallel; each is independently capped at 1 hour.
    STEP_TIMEOUT_SECONDS = 14400

    def step_4_rsync():
        # Trailing slash is important for local rsync src!
        rsync_src = (
            immich_upload if immich_upload.endswith("/") else immich_upload + "/"
        )
        logging.info(f"[rsync] Syncing files to remote rsync module: {rsync_module}")
        # -a: archive mode, -v: verbose, --delete: delete extraneous files from dest dirs
        return run_cmd(
            [
                "rsync",
                "-avz",
                "--progress",
                "--delete",
                f"--password-file={rsync_password_file}",
                rsync_src,
                rsync_module,
            ],
            fatal=False,
            timeout=STEP_TIMEOUT_SECONDS,
        )

    def step_5_local_backup():
        folders_to_compress = [
            os.path.join(immich_upload, f)
            for f in TARGET_FOLDERS
            if os.path.exists(os.path.join(immich_upload, f))
        ]

        if not folders_to_compress:
            logging.warning(
                "[7z] None of the specified target folders were found in the upload path!"
            )
            return False

        if is_full_backup:
            backup_filename = f"immich_full_{current_date_str}.7z"
            backup_filepath = os.path.join(local_backup_path, backup_filename)
            logging.info(f"[7z] Creating Full 7z Backup: {backup_filepath}")

            cmd = [
                "7z",
                "a",
                "-t7z",
                f"-p{compression_password}",
                "-mhe=on",
                backup_filepath,
            ] + folders_to_compress
            ok = run_cmd(cmd, fatal=False, timeout=STEP_TIMEOUT_SECONDS)
            if ok:
                state["last_full_timestamp"] = now.timestamp()
                state["last_full_filename"] = backup_filename
                with open(state_file, "w") as f:
                    json.dump(state, f)
            return ok

        backup_filename = f"immich_inc_{current_date_str}.7z"
        backup_filepath = os.path.join(local_backup_path, backup_filename)
        base_filepath = os.path.join(local_backup_path, last_full_filename)
        logging.info(
            f"[7z] Creating Incremental 7z Backup: {backup_filepath} based on {base_filepath}"
        )

        cmd = [
            "7z",
            "u",
            base_filepath,
            "-u-",
            f"-up0q3r2x2y2z0w2!{backup_filepath}",
            f"-p{compression_password}",
            "-mhe=on",
        ] + folders_to_compress
        return run_cmd(cmd, fatal=False, timeout=STEP_TIMEOUT_SECONDS)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                "rsync": executor.submit(step_4_rsync),
                "7z backup": executor.submit(step_5_local_backup),
            }
            for name, fut in futures.items():
                try:
                    if not fut.result():
                        logging.error(f"Step ({name}) failed or timed out.")
                except Exception:
                    logging.exception(f"Step ({name}) raised unexpected exception.")

    finally:
        # 6. Start Immich Server
        logging.info("Starting Immich server...")
        run_cmd(["docker", "compose", "-f", compose_file, "up", "-d"])

    # 7. Cleanup Old Local Backups
    logging.info(f"Cleaning up backups older than {retention_days} days...")
    cutoff_time = now.timestamp() - (retention_days * 86400)
    for filename in os.listdir(local_backup_path):
        if not filename.endswith(".7z"):
            continue
        filepath = os.path.join(local_backup_path, filename)
        if os.path.isfile(filepath):
            file_mtime = os.path.getmtime(filepath)
            if file_mtime < cutoff_time:
                # Do not delete the last full backup if it is being retained as a reference but older than retention
                if filename == state.get("last_full_filename") and not is_full_backup:
                    logging.info(
                        f"Skipping deletion of {filename} as it is the current base for incrementals."
                    )
                    continue
                logging.info(f"Deleting old backup: {filename}")
                os.remove(filepath)

    # 8. Echo completion
    logging.info(f"Backup completed on {now.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
