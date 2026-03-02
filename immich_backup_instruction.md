# Immich Backup Instruction

Write a shell script to backup immich server. The script should be able to run on a daily basis. 

It does the following:

1. The script reads a configuration file, passed through argument --config.
2. The following keys are set in the configuration
    * IMMICH_UPLOAD_PATH, which is the path for Immich's upload folder.
    * LOCAL_BACKUP_PATH, which is the path to the local backup folder.
    * REMOTE_BACKUP_PATH, which is the path to the remote backup folder.
    * COMPRESSION_PASSWORD, which is the password for the compressed immich server files.
    * FULL_BACKUP_INTERVAL, which is the interval in days for full backup. Any run in-between full backup should be incremental backup.
    * STATE_FILE, which is the path to the state file. The state file should be used to track the last backup time.
    * OLD_FILE_RETENTION_DAYS, which is the number of days to keep old files.
3. The script can run in both regular terminal and cron job.
    * If run in regular terminal, it should prompt the user to confirm the backup.
    * If run in cron job, it should run without any user interaction.
4. The script shuts down immich server to have a consistent state. Immich is running as a docker container, the script should be able to stop and start the container.
5. The script uses rsync to copy files from UPLOAD_LOCATION to REMOTE_BACKUP_PATH. The command should preserve the file permissions and ownership, and delete the files in the destination that are not in the source.
6. The script produces either incremental or full backup files in LOCAL_BACKUP_PATH. The files are encrypted using password set in COMPRESSION_PASSWORD. It only backs up the sub-folders (library/, backups/, upload/, profile/) in IMMICH_UPLOAD_PATH, and ignores other sub-folders.
8. After backing up, the scripts cleans up LOCAL_BACKUP_PATH to delete backup files older than OLD_FILE_RETENTION_DAYS.
9. Start immich server after the backup is completed.
10. Echo "Backup completed on {DATE}" to the console.
11. Write complete instruction on how to use the script and how to set up cron job to run every N days in the script comments.

Ask me any questions you have. Do not make any assumptions.

