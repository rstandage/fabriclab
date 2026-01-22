# FabricLab-NG - Quick Reference

## Installation Commands

```bash
# Update Proxmox
apt-get update && apt-get -y upgrade
apt-get install -y nmap python3-pip git telnet

# Clone repository
cd /root
git clone https://github.com/rstandage/fabriclab.git fabriclab-ng
cd fabriclab-ng

# Install dependencies
pip3 install -r requirements.txt

# Make scripts executable
chmod +x fabriclab.py enable_lldp.sh convert_mist_adoption.py

# Configure network (edit first!)
nano interfaces.txt
cp /etc/network/interfaces /etc/network/interfaces.bak
cp interfaces.txt /etc/network/interfaces
systemctl restart networking

# Enable LLDP
./enable_lldp.sh
crontab -e  # Add: @reboot /root/fabriclab-ng/enable_lldp.sh
```

## Common Commands

### Create Single Switch
```bash
# Basic
./fabriclab.py create --id 201 --name leaf1 --start

# With Mist adoption (auto-enables lab config)
./fabriclab.py create --id 201 --name leaf1 \
  --adopt-template templates/my-org-adopt.template \
  --start

# Custom resources
./fabriclab.py create --id 202 --name spine1 \
  --cores 4 --memory 8192 --start
```

### Deploy Topology
```bash
# List topologies
./fabriclab.py topology --list

# Deploy
./fabriclab.py topology --name spine-leaf-2x2 --start
```

### Access Console
```bash
# VM 201 = port 5201, VM 202 = port 5202, etc.
telnet localhost 5201
```

### Mist Adoption Template
```bash
# Convert set commands to template
./convert_mist_adoption.py \
  -i mist-commands.txt \
  -o templates/my-adopt.template \
  --values extracted-values.txt

# OR just save set commands directly to a template file
# Copy from Mist UI > Paste into templates/my-org-adopt.template
# The script will auto-convert set commands to Junos config
```

## Management Commands

### VM Operations
```bash
# List VMs
qm list

# VM status
qm status 201

# Stop VM
qm stop 201

# Start VM
qm start 201

# Destroy VM
qm destroy 201
```

### Cleanup
```bash
# Remove specific VM
qm stop 201 && qm destroy 201

# Remove all fabric VMs (201-212)
for i in {201..212}; do qm stop $i; qm destroy $i; done
```

### LLDP Verification
```bash
# Check LLDP is enabled
cat /sys/class/net/vmbr500/bridge/group_fwd_mask
# Should show: 0x4000

# Re-enable LLDP
./enable_lldp.sh

# On switch console
show lldp neighbors
```

## File Locations

```
/root/fabriclab-ng/              # Main directory
/var/lib/vz/template/qcow/       # vJunos images
/etc/network/interfaces          # Network config
/tmp/vjunos-config-*.iso         # Temp config disks
```

## Default Credentials

**Switch Login (after config load):**
- Username: `root`
- Password: `Juniper123!`

**Switch First Boot (amnesiac):**
- Username: `root`
- Password: (none - press Enter)

## VM ID to Console Port

| VM ID | Telnet Port |
|-------|-------------|
| 201   | 5201        |
| 202   | 5202        |
| 203   | 5203        |
| ...   | ...         |
| 212   | 5212        |

## Troubleshooting Quick Fixes

```bash
# VM won't start
qm stop 201 && sleep 2 && qm start 201

# Can't access console
systemctl restart pveproxy

# LLDP not working
./enable_lldp.sh

# Disk import failed
qm config 201  # Check disk status
lvs  # Check disk exists

# Network broken
cp /etc/network/interfaces.bak /etc/network/interfaces
systemctl restart networking
```

## Useful One-Liners

```bash
# List all vJunos images
ls -lh /var/lib/vz/template/qcow/vJunos*.qcow2

# Check Proxmox version
pveversion

# View running VMs
qm list | grep running

# Check storage space
pvs && lvs && df -h

# Test internet connectivity
ping -c 3 8.8.8.8

# Check all LLDP bridge masks
for br in $(ls /sys/class/net/ | grep vmbr); do 
  echo "$br: $(cat /sys/class/net/$br/bridge/group_fwd_mask 2>/dev/null || echo 'N/A')"
done
```

## Help and Documentation

```bash
# Main help
./fabriclab.py --help

# Create command help
./fabriclab.py create --help

# Topology help
./fabriclab.py topology --help

# Conversion script help
./convert_mist_adoption.py --help
```

## Quick Links

- Repository: https://github.com/rstandage/fabriclab
- Juniper vJunos Downloads: https://support.juniper.net/support/downloads/?p=vjunos
- Mist Dashboard: https://manage.mist.com/
- Proxmox Docs: https://pve.proxmox.com/wiki/Main_Page

---

**FabricLab-NG Quick Reference** - Always available at [README.md](README.md)
