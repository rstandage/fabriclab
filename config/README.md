# Config Directory

This directory is used by fabriclab-ng to store generated configuration files.

## Contents

- `example.conf` - Example configuration file showing the format
- Generated `.conf` files - Created by the lab config feature
- Generated `.raw` files - Config disk images
- Generated `.iso` files - Config disk ISO images

## Important

**DO NOT** commit user-specific or organization-specific configuration files to version control!

All `.conf`, `.raw`, and `.iso` files (except `example.conf`) are ignored by `.gitignore`.

## Usage

Configurations are automatically created when you use:

```bash
# Create a switch with lab config
./fabriclab.py create --id 201 --name spine-1 --with-lab-config

# Or create a standalone config disk
./fabriclab.py lab --name spine-1
```

Generated files will appear in this directory.
