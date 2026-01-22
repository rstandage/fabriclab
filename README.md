# FabricLab-NG

Automated vJunos-switch VM creation for Proxmox VE with auto-deployment to Mist Cloud.

## Features

- ✅ Automated VM creation with proper disk import and attachment
- ✅ **Auto-configuration for Mist Cloud adoption**
- ✅ **Lab config disk generation using Juniper's make-config.sh**
- ✅ Serial console access via telnet (port 5XXX based on VM ID)
- ✅ Configurable CPU, memory, and network bridges
- ✅ Single switch or full topology deployment
- ✅ Boot order configuration for reliable startup
- ✅ LLDP-enabled bridges for topology discovery
- ✅ Template-based switch adoption configuration

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Proxmox Setup](#initial-proxmox-setup)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware/Software Requirements

- Proxmox VE 8.x installed and running
- Minimum 32GB RAM (recommended 64GB+ for multi-switch fabrics)
- 100GB+ free storage on local-lvm
- Network connectivity for downloads and Mist Cloud access
- Root access to Proxmox host

### Required Downloads

1. **vJunos-switch Images**: Download from [Juniper Support Portal](https://support.juniper.net/support/downloads/?p=vjunos)
   - Recommended: Latest vJunos-switch qcow2 image
   - Place in `/var/lib/vz/template/qcow/`

2. **Mist Organization Setup**: 
   - Active Mist Cloud account
   - Organization with switch licenses
   - API token (for optional Mist API integration)

## Initial Proxmox Setup

This section covers setting up a fresh Proxmox installation to be ready for FabricLab-NG.

### 1. Install Proxmox VE

Install [Proxmox VE 8.x](https://www.proxmox.com/en/downloads/proxmox-virtual-environment/iso/proxmox-ve-8-0-iso-installer) following the official installation guide.

During installation:
- Set a static IP address on the management interface (e.g., `10.38.110.15/24`)
- Configure DNS and gateway appropriately
- Set a secure root password

### 2. Update System and Install Dependencies

After installation, update Proxmox and install required packages:

```bash
apt-get update && apt-get -y upgrade
apt-get install -y nmap python3-pip git telnet
```

### 3. Create Required Directories

```bash
# Directory for storing qcow2 images
mkdir -p /var/lib/vz/template/qcow/

# Directory for ISO files (if using other VM types)
mkdir -p /var/lib/vz/template/iso/
```

### 4. Download vJunos Images

Download vJunos-switch qcow2 images and place them in the qcow directory:

```bash
# Example - adjust path/filename as needed
# Upload via web GUI or use wget/scp
ls -lh /var/lib/vz/template/qcow/
# Should show: vJunos-switch-*.qcow2
```

### 5. Configure Network Interfaces

FabricLab requires specific bridge configurations for LLDP to work properly.

**Important**: Modify `interfaces.txt` in the fabriclab-ng directory to match your network settings before copying.

```bash
# Backup current network configuration
cp /etc/network/interfaces /etc/network/interfaces.bak

# Edit interfaces.txt to match your management IP settings
nano ~/fabriclab-ng/interfaces.txt
# Update vmbr0 address, gateway, and other settings as needed

# Copy network configuration
cp ~/fabriclab-ng/interfaces.txt /etc/network/interfaces

# Restart networking (WARNING: This may disconnect your session)
# Best to do this from console or IPMI
systemctl restart networking
```

**Key Bridge Configurations:**
- `vmbr0`: Host management (connected to physical interface)
- `vmbr101`: VM management network
- `vmbr102-105`: Physical uplink bridges
- `vmbr500+`: Virtual fabric interconnects

### 6. Enable LLDP on Bridges

LLDP (Link Layer Discovery Protocol) is essential for Mist to auto-discover fabric topology.

```bash
# Make script executable
chmod +x ~/fabriclab-ng/enable_lldp.sh

# Run once to enable LLDP immediately
~/fabriclab-ng/enable_lldp.sh

# Configure to run on every boot
crontab -e
```

Add this line to the crontab:

```cron
# Enable LLDP for Linux bridges on boot
@reboot /root/fabriclab-ng/enable_lldp.sh
```

**Verify LLDP is enabled:**
```bash
cat /sys/class/net/vmbr500/bridge/group_fwd_mask
# Should show: 0x4000
```

## Installation

### Clone FabricLab-NG

```bash
cd /root
git clone https://github.com/rstandage/fabriclab.git fabriclab-ng
cd fabriclab-ng
```

### Install Python Dependencies

```bash
# Install optional Mist API support
pip3 install -r requirements.txt

# Or install manually
pip3 install mistapi pyyaml colorama
```

### Make Scripts Executable

```bash
chmod +x /root/fabriclab-ng/fabriclab.py
chmod +x /root/fabriclab-ng/enable_lldp.sh
```

### Verify Installation

```bash
./fabriclab.py --help
```

You should see the FabricLab-NG command-line interface help text.

## Configuration

### Mist Adoption Template

To automatically configure switches for Mist Cloud adoption, create an adoption template file from the Mist dashboard commands.

**IMPORTANT**: Never commit adoption templates with real credentials to version control!

#### Creating Your Adoption Template

1. In Mist Dashboard, go to Organization > Inventory
2. Click "Adopt Switches" and copy the configuration commands (set commands)
3. Save to a template file in the `templates/` directory (e.g., `templates/my-org-adopt.template`)
4. The template should contain the actual set commands from Mist

**Example template content:**
```bash
set system services ssh protocol-version v2
set system authentication-order password
set system login user mist class super-user
set system login user mist authentication encrypted-password $6$xxxxx...
set system login user mist authentication ssh-rsa "ssh-rsa AAAAB3..."
set system services outbound-ssh client mist device-id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
set system services outbound-ssh client mist secret abc123def456...
set system services outbound-ssh client mist services netconf keep-alive retry 12 timeout 5
set system services outbound-ssh client mist oc-term.eu.mist.com port 2200 timeout 60 retry 1000
delete system phone-home
```

The script will automatically convert these set commands to proper Junos configuration format.

**Security Note:** Files matching `templates/*adopt*.template` and `templates/*mist*.template` are automatically ignored by git to prevent accidental commits of sensitive data.

### Topology Configuration Files

Pre-defined topology configurations are in the `config/` directory. You can create custom topologies or modify existing ones.

Example topology files:
- `config/test-full.conf` - Full test topology
- `config/access1.conf` - Access switch configuration
- `config/core2.conf` - Core switch configuration

## Usage

### Quick Start - Single Switch

Create a basic vJunos switch VM without Mist integration:

```bash
cd /root/fabriclab-ng

# Create VM 201 named 'leaf1' and start it
./fabriclab.py create --id 201 --name leaf1 --start

# Access the console
telnet localhost 5201
```

### Quick Start - Mist Cloud Adoption

Create a switch with automatic Mist Cloud adoption configuration:

```bash
cd /root/fabriclab-ng

# Create switch with Mist adoption - auto-enables lab config
./fabriclab.py create --id 201 --name spine-1 \
  --adopt-template templates/my-org-adopt.template \
  --start

# The switch will boot and automatically:
# 1. Load the base configuration
# 2. Apply Mist adoption settings from template
# 3. Connect to Mist Cloud
# 4. Appear in your Mist inventory
```

**Note:** When you provide `--adopt-template`, lab config is automatically enabled. You don't need to specify `--with-lab-config`.

### Command Reference

#### Create a Single Switch

```bash
# Basic creation with defaults (4 cores, 8GB RAM)
./fabriclab.py create --id 201 --name leaf1 --start

# Create with Mist adoption (lab config auto-enabled)
./fabriclab.py create --id 202 --name leaf2 \
  --adopt-template templates/my-org-adopt.template \
  --start

# Create with custom resources
./fabriclab.py create --id 203 --name spine1 --cores 4 --memory 8192 --start

# Create with specific vJunos version
./fabriclab.py create --id 204 --name spine2 --version 23.2R1.14 --start

# Create with custom network bridges
./fabriclab.py create --id 205 --name spine3 \
  --bridges vmbr101 vmbr501 vmbr502 vmbr503 \
  --start
```

#### Lab Configuration Diskbasic config only)
./fabriclab.py lab --name spine-1

# Create config disk with Mist adoption
./fabriclab.py lab --name spine-1 \
  --adopt-template templates/my-org-adopt.template

# Create VM with Mist adoption in one command (recommended)
./fabriclab.py create --id 201 --name spine-1 \
  --adopt-template templates/my-org-adopt.template \
  --start
```

**Note:** The `--adopt-template` flag automatically enables lab config generation, so you don't need `--with-lab-config`.reate VM with integrated lab config in one command
./fabriclab.py create --id 201 --name spine-1 \
  --with-lab-config \
  --adopt-template templates/mist-adopt.template \
  --start
```

#### Deploy Fabric Topologies

```bash
# List available topologies
./fabriclab.py topology --list

# Show topology details
./fabriclab.py topology --show 2spine

# Deploy entire topology (auto-assigns VM IDs starting from 201)
./fabriclab.py topology --name 2spine --start

# Deploy without auto-start
./fabriclab.py topology --name 2spine
```

### Accessing Switch Console

Once a VM is created, you can access the serial console via telnet:

```bash
# VM ID 201 = telnet port 5201
# VM ID 202 = telnet port 5202, etc.
telnet localhost 5201

# Default login credentials on first boot:
# Username: root
# Password: (none - press Enter)
# 
# After first login, you'll be in "amnesiac" mode
# Load configuration or paste startup config
```

### Adopting Switches to Mist

#### Method 1: Using Lab Config Disk (Recommended)

The easiest method is to create VMs with `--with-lab-config` flag (see above). Switches will auto-adopt on first boot.

#### Method 2: Manual Console Configuration

1. Access switch console:
   ```bash
   telnet localhost 52XX  # XX = last 2 digits of VM ID
   ```

2. Login as root (no password)

3. Enter configuration mode:
   ```
   cli
   configure
   ```

4. Paste your adoption configuration (from Mist dashboard)

5. Commit and verify:
   ```
   commit and-quit
   show system commit
   ```

6. Switch should appear in Mist inventory within 2-3 minutes

### Building a Fabric in Mist

After switches are adopted to Mist:

1. **Verify LLDP**: Ensure enable_lldp.sh has run on Proxmox
   ```bash
   ~/fabriclab-ng/enable_lldp.sh
   ```

2. **Create Site**: In Mist dashboard, create a site for your lab

3. **Assign Switches**: Assign all switches to the site

4. **Create Switch Template**: Configure switch template with:
   - Port profiles
   - VLANs
   - IP addressing

5. **Build Fabric**: Use Mist's fabric builder to:
   - Discover LLDP topology
   - Configure EVPN/VXLAN
   - Deploy configuration

## VM Configuration Details

Each VM is created with the following specifications:

**Compute Resources:**
- CPU: 4 cores (default, configurable)
- CPU Type: host (best performance)
- Memory: 8192 MB (default, configurable)
- Machine Type: q35

**Storage:**
- Disk 0: vJunos-switch qcow2 (imported to local-lvm)
- Disk 1: Lab config disk (optional, ISO format)

**Network Interfaces:**
- net0 (fxp0): Management - typically vmbr101
- net1-4 (ge-0/0/0 to ge-0/0/3): Fabric links - typically vmbr500+

**Console:**
- Serial console enabled
- Telnet access on port 5XXX (where XXX = VM ID)
- Boot order: disk,net (PXE fallback)

**Default Credentials:**
- Username: root
- Password: Juniper123! (after config load)
- No password on first boot (amnesiac mode)

## Network Bridges

FabricLab-NG expects the following Proxmox bridge configuration:

| Bridge | Purpose | LLDP | Notes |
|--------|---------|------|-------|
| vmbr0 | Host management | No | Physical uplink for Proxmox host |
| vmbr101 | VM management | Yes | Switch fxp0 management |
| vmbr102-105 | Physical uplinks | Yes | Optional physical device connections |
| vmbr500+ | Virtual fabric | Yes | Point-to-point switch interconnects |

All bridges used for switch connectivity **must** have LLDP forwarding enabled.

## Available Topologies

Pre-defined fabric topologies for quick deployment:

### 2-Spine Topology (2spine)
- 2 spine switches (VM 201-202)
- 4 leaf switches (VM 203-206)
- Full mesh spine-leaf connectivity
- Best for: Small fabric testing

### 4-Spine Topology (4spine)
- 4 spine switches (VM 201-204)
- 8 leaf switches (VM 205-212)
- Full mesh spine-leaf connectivity
- Best for: Large-scale fabric testing

### Simple Spine-Leaf (spine-leaf)
- 2 spine switches (VM 201-202)
- 2 leaf switches (VM 203-204)
- Minimal fabric for basic testing
- Best for: Quick tests, learning

## Architecture

```
fabriclab-ng/
├── fabriclab.py              # Main CLI orchestrator
├── enable_lldp.sh            # LLDP forwarding enabler
├── interfaces.txt            # Proxmox network config template
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore rules (protects sensitive files)
├── lib/
│   ├── __init__.py
│   ├── proxmox_vm.py        # VM creation and management
│   ├── mist_client.py       # Mist API integration
│   └── config_templates.py  # Junos config and topology definitions
├── templates/
│   ├── lab_switch_base.config         # Base switch config (non-sensitive)
│   ├── make-config.sh                 # Juniper's config disk builder
│   ├── example-mist-adoption.template # Example template format
│   └── *.template                     # Your org adoption templates (gitignored)
├── config/                   # Generated configs (gitignored)
│   ├── README.md
│   ├── example.conf
│   └── *.conf, *.raw, *.iso  # Generated files
├── README.md                 # Complete documentation
└── QUICK_REFERENCE.md        # Command quick reference
```

## Troubleshooting

### Pre-Installation Issues

#### Cannot Access Proxmox Web GUI
- Verify network configuration: `ip addr show`
- Check firewall: `iptables -L`
- Verify Proxmox services: `systemctl status pveproxy pvedaemon`

#### Missing Dependencies
```bash
# Install missing packages
apt-get update
apt-get install -y python3-pip git telnet qemu-utils
```

### VM Creation Issues

#### VM Won't Create - Disk Import Failed
- **Verify qcow2 file exists:**
  ```bash
  ls -lh /var/lib/vz/template/qcow/
  ```
- **Check storage space:**
  ```bash
  pvs
  lvs
  df -h
  ```
- **Check file permissions:**
  ```bash
  chmod 644 /var/lib/vz/template/qcow/*.qcow2
  ```

#### VM Creation Fails - ID Already Exists
```bash
# Check if VM exists
qm list | grep <VM_ID>

# Destroy existing VM if needed
qm stop <VM_ID>
qm destroy <VM_ID>
```

#### Disk Import Hangs or Takes Forever
- Check storage I/O: `iostat -x 1`
- Verify local-lvm has space: `lvs`
- Try different storage: Modify `proxmox_vm.py` to use different storage pool

### VM Runtime Issues

#### VM Won't Start
- **Check VM status:**
  ```bash
  qm status <VM_ID>
  ```
- **Check VM configuration:**
  ```bash
  qm config <VM_ID>
  ```
- **View Proxmox logs:**
  ```bash
  journalctl -xe | tail -50
  tail -f /var/log/syslog
  ```
- **Try manual start:**
  ```bash
  qm start <VM_ID>
  ```

#### Can't Access Console via Telnet
- **Verify VM is running:**
  ```bash
  qm status <VM_ID>
  ```
- **Check telnet port is listening:**
  ```bash
  netstat -ln | grep 52XX  # XX = last digits of VM ID
  ```
- **Try stopping and restarting VM:**
  ```bash
  qm stop <VM_ID>
  sleep 5
  qm start <VM_ID>
  ```
- **Connect to console directly:**
  ```bash
  qm terminal <VM_ID>
  ```

#### Console Shows Garbled Text
- Press Enter several times
- The switch may be booting - wait 2-3 minutes
- Try different terminal: `TERM=vt100 telnet localhost 52XX`

### Network and LLDP Issues

#### LLDP Not Working Between Switches
- **Verify LLDP forwarding is enabled:**
  ```bash
  cat /sys/class/net/vmbr500/bridge/group_fwd_mask
  # Should show: 0x4000
  ```
- **Re-run LLDP script:**
  ```bash
  ~/fabriclab-ng/enable_lldp.sh
  ```
- **Verify on switch:**
  ```
  show lldp neighbors
  ```
- **Check bridge configuration:**
  ```bash
  brctl show
  ```

#### Switches Can't Reach Mist Cloud
- **Verify Proxmox has internet:**
  ```bash
  ping 8.8.8.8
  ping oc-term.eu.mist.com
  ```
- **Check vmbr101 configuration**
- **Verify switch management IP:**
  ```
  show configuration interfaces fxp0
  ```
- **Test from switch:**
  ```
  ping 8.8.8.8 source fxp0.0
  ```

### Mist Adoption Issues

#### Switch Not Appearing in Mist Inventory
- **Verify outbound-ssh config:**
  ```
  show configuration system services outbound-ssh
  ```
- **Check device-id and secret are correct**
- **Verify Mist user exists:**
  ```
  show configuration system login user mist
  ```
- **Check switch can reach Mist:**
  ```
  ping oc-term.eu.mist.com
  ```
- **Review logs:**
  ```
  show log messages | match mist
  show log messages | match outbound-ssh
  ```

#### Switch Shows as "Disconnected" in Mist
- Check network connectivity from switch
- Verify system clock is correct: `show system uptime`
- Check for certificate issues in logs
- Try deleting and re-adding device in Mist

#### Lab Config Disk Not Loading
- **Verify disk is attached:**
  ```bash
  qm config <VM_ID> | grep ide
  ```
- **Check disk file exists:**
  ```bash
  ls -lh /tmp/vjunos-config-*.iso
  ```
- **Try manual config:**
  - Access console
  - Load config from CLI manually

### Performance Issues

#### VMs Running Slowly
- **Check host CPU usage:**
  ```bash
  top
  htop
  ```
- **Reduce number of VMs or cores per VM**
- **Check disk I/O:**
  ```bash
  iostat -x 1
  ```
- **Verify no memory swapping:**
  ```bash
  free -h
  vmstat 1
  ```

#### High Memory Usage
- Reduce memory allocation per VM (minimum 6GB recommended)
- Limit number of concurrent VMs
- Check for memory leaks: `top` then press 'M'

### Cleanup and Recovery

#### Remove Failed/Stuck VMs
```bash
# Force stop VM
qm stop <VM_ID> --skiplock

# Destroy VM completely
qm destroy <VM_ID> --purge

# Remove orphaned disks
lvremove /dev/pve/vm-<VM_ID>-disk-*

# Remove config disk if exists
rm -f /tmp/vjunos-config-<VM_NAME>.iso
```

#### Reset FabricLab Environment
```bash
# Stop all VMs (201-212)
for i in {201..212}; do qm stop $i; done

# Destroy all VMs
for i in {201..212}; do qm destroy $i --purge; done

# Clean up any orphaned resources
lvs | grep "vm-20[1-9]" | awk '{print $1}' | xargs -I {} lvremove -y /dev/pve/{}

# Start fresh
./fabriclab.py topology --name 2spine --start
```

#### Network Configuration Rollback
```bash
# If network changes break connectivity
# From console/IPMI:
cp /etc/network/interfaces.bak /etc/network/interfaces
systemctl restart networking
```

### Getting Help

#### Enable Debug Logging
Edit [fabriclab.py](fabriclab.py) line 20:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    ...
)
```

#### Collect Diagnostic Information
```bash
# System info
proxmox-ve --version
pveversion -v

# VM info
qm list
qm config <VM_ID>

# Network info
brctl show
cat /sys/class/net/vmbr*/bridge/group_fwd_mask

# Storage info
pvs
lvs
df -h
```

## Common Workflows

### Deploying a New Fabric from Scratch

1. **Prepare Proxmox** (one-time setup):
   ```bash
   # Update and install dependencies
   apt-get update && apt-get -y upgrade
   apt-get install -y nmap python3-pip git telnet
   
   # Download vJunos images
   # Place in /var/lib/vz/template/qcow/
   
   # Clone fabriclab-ng
   cd /root
   git clone https://github.com/rstandage/fabriclab.git fabriclab-ng
   
   # Configure network (edit first!)
   cp ~/fabriclab-ng/interfaces.txt /etc/network/interfaces
   systemctl restart networking
   
   # Enable LLDP
   chmod +x ~/fabriclab-ng/enable_lldp.sh
   ~/fabriclab-ng/enable_lldp.sh
   crontab -e  # Add @reboot entry
   ```

2. **Create Mist Adoption Template**:
   ```bash
   # Get adoption commands from Mist dashboard
   # Save to templates/mist-adopt.template
   ```

3. **Deploy Fabric**:
   ```bash
   cd /root/fabriclab-ng
   
   # Deploy 2-spine topology with Mist adoption
   ./fabriclab.py topology --name 2spine --start
   
   # OR create individual switches with adoption
   ./fabriclab.py create --id 201 --name spine-1 \
     --with-lab-config \
     --adopt-template templates/mist-adopt.template \
     --start
   ```

4. **Verify and Build in Mist**:
   - Wait 2-3 minutes for switches to appear in Mist
   - Create site and assign switches
   - Build fabric using Mist UI

### Adding Switches to Existing Fabric

```bash
# Create new leaf switch
./fabriclab.py create --id 210 --name leaf-5 \
  --with-lab-config \
  --adopt-template templates/mist-adopt.template \
  --bridges vmbr101 vmbr510 vmbr511 \
  --start

# Connect to existing spines via Proxmox GUI:
# - Attach appropriate vmbr bridges for uplinks
# - Wait for LLDP discovery
# - Add to fabric in Mist
```

### Upgrading vJunos Version

```bash
# Download new vJunos version to /var/lib/vz/template/qcow/

# Create new switch with specific version
./fabriclab.py create --id 220 --name test-switch \
  --version 24.2R1.17 \
  --start

# Verify version
telnet localhost 5220
# Login and run: show version
```

## Differences from Original FabricLab

### Major Improvements in FabricLab-NG

1. **Automated Mist Adoption**
   - Lab config disk generation
   - Template-based adoption configuration
   - Zero-touch deployment support

2. **Enhanced Reliability**
   - Fixed disk import and attachment issues
   - Proper boot order configuration
   - Better error handling and logging

3. **Modern Architecture**
   - Modular Python design
   - Comprehensive CLI interface
   - Extensible topology system

4. **Better User Experience**
   - Single-command deployments
   - Interactive and non-interactive modes
   - Clear progress indicators

5. **Production Ready**
   - Template-based configuration
   - Security-focused design
   - Documentation and examples

### Fixed Issues from Original

- **Disk Import**: Reliable disk detection and attachment
- **Serial Console**: Fixed duplicate console configuration
- **Boot Order**: Explicit configuration for consistent startup
- **Resource Management**: Better CPU and memory allocation
- **LLDP Integration**: Automated LLDP enablement

## Additional Documentation

- **LAB_CONFIG_GUIDE.md** - Detailed guide for lab configuration feature (if available)
- **QUICK_REFERENCE.md** - Command quick reference (if available)
- **IMPLEMENTATION_SUMMARY.md** - Technical implementation details (if available)

## Security Considerations

### Protecting Sensitive Information

**NEVER commit these files to version control:**
- `templates/*adopt*.template` - Contains Mist secrets
- `config/*.conf` - May contain organization-specific data
- Any file with actual device-ids, secrets, or SSH keys

**Add to .gitignore:**
```gitignore
# Sensitive Mist adoption files
templates/*adopt*.template
templates/*mist*.template

# User-specific configurations
config/*.conf
!config/example.conf

# Lab config ISOs
*.iso
/tmp/vjunos-config-*.iso
```

### Best Practices

1. **Use Template Files**: Create template files with placeholders
2. **Separate Credentials**: Keep credentials in separate, non-committed files
3. **Rotate Secrets**: Periodically regenerate Mist adoption credentials
4. **Limit Access**: Restrict access to Proxmox host and templates directory
5. **Secure Storage**: Use encrypted storage for sensitive configuration files

## Contributing

Contributions are welcome! Please ensure:

- Code follows existing Python style (PEP 8)
- Test on Proxmox VE 8.x before submitting
- Update documentation for new features
- No breaking changes to existing functionality
- Add tests for new functionality where applicable

### Development Setup

```bash
# Fork and clone repository
git clone https://github.com/your-fork/fabriclab-ng.git
cd fabriclab-ng

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test

# Submit pull request
```

## References and Resources

- [Juniper vJunos-switch Documentation](https://www.juniper.net/documentation/us/en/software/nce/nce-510-virtual-switches-mist-cloud-managed/)
- [Mist Cloud Dashboard](https://manage.mist.com/)
- [Mist API Documentation](https://api.mist.com/api/v1/docs/)
- [vJunos Downloads](https://support.juniper.net/support/downloads/?p=vjunos)
- [Proxmox VE Documentation](https://pve.proxmox.com/wiki/Main_Page)
- [EVPN-VXLAN Architecture Guide](https://www.juniper.net/documentation/us/en/software/evpn-vxlan/)

## License

MIT License - See LICENSE file for details.

## Support and Contact

For issues, questions, or contributions:
- Open an issue on GitHub
- Submit a pull request
- Contact: rstandage (GitHub)

## Changelog

### Version 2.0 (FabricLab-NG)
- Complete rewrite with modular architecture
- Added Mist Cloud adoption automation
- Lab config disk generation
- Template-based configuration
- Enhanced error handling and logging
- Comprehensive documentation

### Version 1.0 (Original FabricLab)
- Basic VM creation for vJunos-switch
- Manual configuration workflow
- Simple topology support

---

**FabricLab-NG** - Making virtual fabric labs simple and reliable.
