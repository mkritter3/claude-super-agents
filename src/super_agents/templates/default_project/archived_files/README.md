# Archived Files Directory

This directory contains organized backups and archives created by super-agents.

## Structure

```
archived_files/
├── super_agents_backup_YYYYMMDD_HHMMSS/   # Initialization conflict backups
├── super_agents_upgrade_YYYYMMDD_HHMMSS/  # Upgrade backups
└── [other_backup_types]/                  # Future backup types
```

## Backup Types

### Initialization Backups (`super_agents_backup_*`)
Created when super-agents encounters existing files during project initialization.
- Contains original files that would be overwritten
- Includes `backup_manifest.json` with details about the backup

### Upgrade Backups (`super_agents_upgrade_*`)
Created during project upgrades to preserve existing configurations.
- Contains previous version files before upgrade
- Includes `backup_info.json` with upgrade details

## Cleanup

These directories can be safely deleted after you've verified your project is working correctly. The system does not automatically clean them up to preserve your data.

To remove old backups:
```bash
# Remove backups older than 30 days
find archived_files -name "*_backup_*" -type d -mtime +30 -exec rm -rf {} \;
```