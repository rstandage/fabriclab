# GitHub Repository Migration Guide

## Overview

This document guides you through replacing the contents of the existing fabriclab repository with fabriclab-ng.

**Repository:** https://github.com/rstandage/fabriclab

## Pre-Migration Checklist

- [ ] Backup existing repository (if needed)
  ```bash
  git clone https://github.com/rstandage/fabriclab.git fabriclab-backup
  ```

- [ ] Review all changes in fabriclab-ng
- [ ] Ensure no sensitive data in fabriclab-ng (check .gitignore)
- [ ] Test fabriclab-ng locally on Proxmox
- [ ] Prepare release notes

## Files to Migrate from fabriclab-ng

### Core Files
- [x] `fabriclab.py` - Main application (new)
- [x] `README.md` - Comprehensive documentation (updated)
- [x] `requirements.txt` - Python dependencies (updated)
- [x] `.gitignore` - Git ignore rules (new)
- [x] `enable_lldp.sh` - LLDP enablement (migrated)
- [x] `interfaces.txt` - Network configuration (migrated)
- [x] `convert_mist_adoption.py` - New utility script

### Library Files
- [x] `lib/__init__.py`
- [x] `lib/proxmox_vm.py`
- [x] `lib/mist_client.py`
- [x] `lib/config_templates.py`

### Templates
- [x] `templates/lab_switch_default.config`
- [x] `templates/make-config.sh`
- [x] `templates/mist-adopt-example.template`

### Config Examples
- [x] `config/README.md`
- [x] `config/example.conf`

## Files to Remove from Old Repository

### Deprecated Files
- [ ] `create_vswitch.py` - Replaced by fabriclab.py
- [ ] `switch_default.conf` - Replaced by templating system
- [ ] Any old configuration files with org-specific data

## Migration Steps

### Option A: Clean Replacement (Recommended)

This creates a clean history starting with fabriclab-ng.

```bash
# 1. Navigate to your local fabriclab repository
cd /path/to/local/fabriclab

# 2. Create a new branch for the migration
git checkout -b fabriclab-ng-migration

# 3. Remove all old files (except .git)
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

# 4. Copy all files from fabriclab-ng
cp -r /root/fabriclab-ng/* .
cp -r /root/fabriclab-ng/.gitignore .

# 5. Stage all changes
git add -A

# 6. Commit the changes
git commit -m "Migration to FabricLab-NG v2.0

Major rewrite with the following improvements:
- Modular Python architecture
- Automated Mist Cloud adoption
- Lab config disk generation
- Template-based configuration
- Comprehensive error handling and documentation
- Enhanced LLDP support
- Production-ready security practices

This replaces the original fabriclab with a next-generation version.

See README.md for complete documentation and migration guide.
"

# 7. Push to GitHub (creates new branch)
git push origin fabriclab-ng-migration

# 8. Create Pull Request on GitHub
# Go to: https://github.com/rstandage/fabriclab
# Create PR from fabriclab-ng-migration to main
# Review changes
# Merge when ready

# 9. After merge, update main branch locally
git checkout main
git pull origin main

# 10. Tag the release
git tag -a v2.0.0 -m "FabricLab-NG v2.0.0 - Major rewrite"
git push origin v2.0.0
```

### Option B: Preserve History

This keeps the git history but adds fabriclab-ng on top.

```bash
# 1. In your local fabriclab repository
cd /path/to/local/fabriclab

# 2. Create migration branch
git checkout -b fabriclab-ng-update

# 3. Remove deprecated files
git rm create_vswitch.py switch_default.conf
git rm config/*.conf  # If any exist

# 4. Copy new/updated files from fabriclab-ng
cp /root/fabriclab-ng/fabriclab.py .
cp /root/fabriclab-ng/README.md .
cp /root/fabriclab-ng/requirements.txt .
cp /root/fabriclab-ng/.gitignore .
cp /root/fabriclab-ng/convert_mist_adoption.py .

# Copy lib directory
rm -rf lib/
cp -r /root/fabriclab-ng/lib .

# Copy templates
rm -rf templates/
cp -r /root/fabriclab-ng/templates .

# Copy config examples
rm -rf config/
mkdir -p config
cp /root/fabriclab-ng/config/README.md config/
cp /root/fabriclab-ng/config/example.conf config/

# 5. Stage all changes
git add -A

# 6. Commit
git commit -m "Update to FabricLab-NG v2.0

Major improvements:
- New modular architecture
- Mist Cloud automation
- Template-based configuration
- Enhanced documentation
- Security improvements

See README.md for details.
"

# 7. Push and create PR
git push origin fabriclab-ng-update
```

## Post-Migration Tasks

### Update Repository Settings

- [ ] Update repository description:
  ```
  Automated vJunos-switch VM creation for Proxmox VE with Mist Cloud integration
  ```

- [ ] Update repository topics/tags:
  - proxmox
  - juniper
  - vjunos
  - mist
  - networking
  - automation
  - fabric
  - evpn-vxlan

- [ ] Update README badges (if using)

### Create Release

- [ ] Create GitHub Release v2.0.0
- [ ] Add release notes
- [ ] Attach any relevant files

### Update Documentation

- [ ] Ensure README.md is current
- [ ] Add CHANGELOG.md if desired
- [ ] Update any external documentation

### Notify Users

- [ ] Create announcement in Discussions or Issues
- [ ] Update any external references to the repository

## Security Verification

Before pushing to GitHub, verify:

```bash
# Check for sensitive data
cd /root/fabriclab-ng

# Search for device IDs
grep -r "device-id" . --exclude-dir=.git

# Search for secrets
grep -r "secret.*[a-f0-9]{64}" . --exclude-dir=.git

# Search for SSH keys (long base64 strings)
grep -r "ssh-rsa.*AAAA" . --exclude-dir=.git

# Verify .gitignore is working
git status
# Should NOT show:
# - templates/*adopt*.template (if they contain real data)
# - config/*.conf (except example.conf)
# - *.iso, *.raw files
```

## Rollback Plan

If something goes wrong:

```bash
# Option 1: Revert the commit
git revert <commit-hash>
git push origin main

# Option 2: Reset to previous state
git reset --hard <previous-commit-hash>
git push origin main --force  # Use with caution!

# Option 3: Restore from backup
# Use the backup created in pre-migration
```

## Testing After Migration

After migration, have someone clone the repo and test:

```bash
# Clone the repository
git clone https://github.com/rstandage/fabriclab.git
cd fabriclab

# Verify all files are present
ls -la

# Check README renders correctly on GitHub

# Install dependencies
pip3 install -r requirements.txt

# Test basic functionality (if on Proxmox)
./fabriclab.py --help
```

## Migration Timeline

**Estimated Time:** 30-60 minutes

1. Pre-migration checks: 10 min
2. Migration execution: 15 min
3. Verification: 10 min
4. Documentation updates: 15 min
5. Testing: 10 min

## Support

If you encounter issues during migration:
1. Check this guide
2. Review git output for errors
3. Check GitHub repository settings
4. Refer to Git documentation

## Checklist Summary

- [ ] Backup old repository
- [ ] Review fabriclab-ng for sensitive data
- [ ] Choose migration strategy (A or B)
- [ ] Execute migration steps
- [ ] Verify no sensitive data pushed
- [ ] Update repository settings
- [ ] Create release/tag
- [ ] Test cloned repository
- [ ] Update documentation
- [ ] Announce migration

---

**FabricLab-NG Migration Guide** - Version 1.0
