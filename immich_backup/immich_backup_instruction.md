# Immich Backup Instruction

Write a Python script to backup immich server. The script should be able to run on a daily basis. 

It does the following:

1. The script reads a configuration file, passed through argument --config. Using simple .env style for the configuration file. The script should be able to read the configuration file and print the configuration to the console.
2. The following keys are set in the configuration
    * IMMICH_UPLOAD_PATH, which is the path for Immich's upload folder. 
    * IMMICH_DOCKER_COMPOSE_FILE, which is the path to the docker compose file for immich server.   
    * LOCAL_BACKUP_PATH, which is the path to the local backup folder.
    * RSYNC_MODULE, which is the path to the remote backup folder.
    * RSYNC_PASSWORD_FILE, which is the path to the rsync password file.
    * COMPRESSION_PASSWORD, which is the password for the compressed immich server files.
    * FULL_BACKUP_INTERVAL, which is the interval in days for full backup. Any run in-between full backup should be incremental backup.
    * STATE_FILE, which is the path to the state file. The state file should be used to track the last backup time.
    * OLD_FILE_RETENTION_DAYS, which is the number of days to keep old files.    
3. The script can run in both regular terminal and cron job.
    * If run in regular terminal, it should prompt the user to confirm the backup.
    * If run in cron job, it should run without any user interaction.
4. The script shuts down immich server to have a consistent state. Immich is running as a docker container, the script should be able to stop and start the container.
5. The script uses rsync to sync files from IMMICH_UPLOAD_PATH to RSYNC_MODULE. The command should preserve the file permissions and ownership, and delete the files in the destination that are not in the source.
    * RSYNC_MODULE is something like "user@<IP_ADDRESS>::module". The rsync command is like: rsync -avz --progress --password-file=RSYNC_PASSWORD_FILE IMMICH_UPLOAD_PATH/ RSYNC_MODULE
6. The script produces either incremental or full backup files in LOCAL_BACKUP_PATH, using tool 7z. The files are encrypted using password set in COMPRESSION_PASSWORD. It only backs up the following sub-folders (library/, backups/, upload/, and profile/) in IMMICH_UPLOAD_PATH, and ignores other sub-folders. The backup files should preserve the file permissions, ownership, and timestamps.
7. After backing up, the scripts cleans up LOCAL_BACKUP_PATH to delete backup files older than OLD_FILE_RETENTION_DAYS.
8. Start immich server after the backup is completed.
9. Echo "Backup completed on {DATE}" to the console.
10. Write complete instruction on how to use the script and how to set up cron job to run every N days in the script comments.
11. Also write comments on how to restore the backup files to a new immich server.

Ask me any questions you have. Do not make any assumptions.

