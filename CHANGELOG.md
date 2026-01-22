# Changelog

All notable changes to FabricLab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-22

### Major Rewrite - FabricLab-NG

Complete rewrite of FabricLab with modern architecture and automated Mist Cloud integration.

### Added

#### Core Features
- Modular Python architecture with separate VM, Mist, and config modules
- Automated Mist Cloud adoption configuration
- Lab config disk generation using Juniper's make-config.sh
- Template-based switch configuration system
- Pre-defined fabric topology support (spine-leaf, linear)
- Comprehensive CLI interface with argparse

#### Automation Tools
- `convert_mist_adoption.py` - Convert Mist set commands to secure templates
- Automatic placeholder extraction for sensitive data
- Interactive and non-interactive modes for template creation

#### Documentation
- Comprehensive README with start-to-finish setup guide
- Initial Proxmox setup instructions
- Detailed troubleshooting section
- Common workflows and examples
- Quick reference guide
- Migration guide from v1.0
- Security best practices documentation

#### Security
- .gitignore with comprehensive rules for sensitive files
- Template-based configuration to separate secrets
- Clear documentation on security practices
- Placeholder system for sensitive values

### Changed

#### Architecture
- Python scripts reorganized into `lib/` modules:
  - `proxmox_vm.py` - VM creation and management
  - `mist_client.py` - Mist API integration  
  - `config_templates.py` - Junos configs and topologies
- Single entry point: `fabriclab.py`
- Configuration templates moved to `templates/`
- Generated configs stored in `config/` (gitignored)

#### Workflow Improvements
- Single-command VM creation with auto-adoption
- Integrated lab config disk creation
- Better error handling and logging
- Progress indicators for long-running operations
- Automatic version detection for vJunos images

#### Network Configuration
- Enhanced LLDP forwarding support
- Clearer bridge naming and documentation
- Network configuration template included

### Fixed

- **Disk Import**: Reliable disk detection and attachment
- **Serial Console**: Removed duplicate console configuration causing boot failures
- **Boot Order**: Explicit configuration for consistent startup
- **Disk Detection**: Handles both disk-0 and disk-1 scenarios
- **Resource Management**: Better CPU and memory allocation
- **Error Handling**: Comprehensive exception handling throughout

### Removed

- `create_vswitch.py` - Replaced by `fabriclab.py create`
- `switch_default.conf` - Replaced by template system
- User-specific configuration files
- Organization-specific data from repository

### Security

- All sensitive data removed from tracked files
- Template system prevents accidental credential commits
- Comprehensive .gitignore rules
- Security verification documentation

### Migration

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for upgrade instructions from v1.0.

---

## [1.0.0] - 2024 (Original FabricLab)

### Initial Release

- Basic vJunos-switch VM creation on Proxmox
- Manual configuration workflow
- LLDP enablement script
- Network interface configuration template
- Basic documentation

### Features

- `create_vswitch.py` - Create individual switch VMs
- `enable_lldp.sh` - Enable LLDP on bridges
- `interfaces.txt` - Network configuration template
- `switch_default.conf` - Default switch configuration
- Basic README with setup instructions

### Known Issues

- Disk import reliability issues
- Serial console boot problems
- Limited error handling
- Manual Mist adoption process
- No template support for configurations

---

## Migration Notes

### From v1.0 to v2.0

**Breaking Changes:**
- `create_vswitch.py` replaced with `fabriclab.py create`
- Configuration file format changed to templates
- Directory structure reorganized

**Migration Path:**
1. Install fabriclab-ng alongside fabriclab
2. Test new workflows
3. Migrate custom configurations to templates
4. Switch to fabriclab-ng for new deployments
5. Decommission v1.0 when ready

**Compatibility:**
- VMs created with v1.0 continue to work
- Network configuration compatible
- LLDP script compatible
- Manual adoption process still works

---

## Upcoming (Future Releases)

### Planned Features
- [ ] Full Mist API integration for claiming devices
- [ ] Automated fabric deployment via Mist API
- [ ] Switch firmware upgrade automation
- [ ] Configuration backup and restore
- [ ] Multi-site topology support
- [ ] GUI dashboard (optional)
- [ ] Docker container support
- [ ] Terraform provider integration

### Under Consideration
- Integration with Ansible for configuration management
- Support for other vJunos types (router, evolved)
- Integration with EVE-NG or GNS3
- REST API for automation
- Web-based console access

---

## Release Versioning

- **Major (X.0.0)**: Breaking changes, major architecture changes
- **Minor (0.X.0)**: New features, non-breaking changes
- **Patch (0.0.X)**: Bug fixes, documentation updates

---

[2.0.0]: https://github.com/rstandage/fabriclab/releases/tag/v2.0.0
[1.0.0]: https://github.com/rstandage/fabriclab/releases/tag/v1.0.0
