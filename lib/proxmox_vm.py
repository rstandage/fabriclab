#!/usr/bin/env python3
"""
Proxmox VM Manager for vJunos-switch
Handles VM creation, disk import, and configuration
"""

import os
import subprocess
import time
import random
import logging
import tempfile
import re
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class ProxmoxVMManager:
    """Manages Proxmox VMs for vJunos-switch instances"""
    
    QCOW_DIR = Path("/var/lib/vz/template/qcow")
    VM_CONFIG_DIR = Path("/etc/pve/qemu-server")
    
    def __init__(self):
        self.validate_environment()
    
    def validate_environment(self):
        """Validate that we're running on Proxmox with required directories"""
        if not self.QCOW_DIR.exists():
            raise RuntimeError(f"QCOW directory not found: {self.QCOW_DIR}")
        if not self.VM_CONFIG_DIR.exists():
            raise RuntimeError(f"VM config directory not found: {self.VM_CONFIG_DIR}")
    
    def gen_mac(self) -> str:
        """Generate a random MAC address"""
        first_byte = random.randint(0x00, 0xFE) & 0xFE
        mac = [first_byte] + [random.randint(0x00, 0xFF) for _ in range(5)]
        mac_address = ':'.join([f'{byte:02X}' for byte in mac])
        return mac_address
    
    def find_vjunos_image(self, version: Optional[str] = None) -> Path:
        """
        Find vJunos-switch qcow2 image
        
        Args:
            version: Specific version to look for (e.g., "25.4R1.12")
                    If None, returns the newest version found
        
        Returns:
            Path to the qcow2 file
        """
        pattern = "vJunos-switch-*.qcow2"
        images = list(self.QCOW_DIR.glob(pattern))
        
        if not images:
            raise FileNotFoundError(
                f"No vJunos-switch images found in {self.QCOW_DIR}\n"
                f"Download from: https://support.juniper.net/support/downloads/?p=vjunos"
            )
        
        if version:
            # Look for specific version
            for img in images:
                if version in img.name:
                    logger.info(f"Found requested version: {img.name}")
                    return img
            raise FileNotFoundError(f"Version {version} not found. Available: {[i.name for i in images]}")
        
        # Return newest (sort by modification time)
        newest = max(images, key=lambda p: p.stat().st_mtime)
        logger.info(f"Using newest image: {newest.name}")
        return newest
    
    def vm_exists(self, vm_id: int) -> bool:
        """Check if a VM with the given ID already exists"""
        config_file = self.VM_CONFIG_DIR / f"{vm_id}.conf"
        return config_file.exists()
    
    def get_vm_status(self, vm_id: int) -> Optional[str]:
        """Get the status of a VM"""
        try:
            result = subprocess.run(
                ["qm", "status", str(vm_id)],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                # Output is like "status: running" or "status: stopped"
                return result.stdout.strip().split(": ")[1]
            return None
        except Exception as e:
            logger.warning(f"Could not get VM status: {e}")
            return None
    
    def wait_for_disk_import(self, vm_id: int, timeout: int = 180) -> bool:
        """
        Wait for disk import to complete by checking if disk exists
        
        Args:
            vm_id: VM ID
            timeout: Maximum seconds to wait
            
        Returns:
            True if disk was imported successfully
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if VM has an imported disk (shows as unused0, unused1, etc. or vm-XXX-disk-N)
            result = subprocess.run(
                ["qm", "config", str(vm_id)],
                capture_output=True,
                text=True,
                check=False
            )
            # Check for unused disk or already attached disk with vm-XXX-disk pattern
            if result.returncode == 0 and (f"vm-{vm_id}-disk-" in result.stdout or "unused" in result.stdout):
                logger.info(f"Disk successfully imported for VM {vm_id}")
                return True
            time.sleep(3)
        
        logger.error(f"Timeout waiting for disk import for VM {vm_id}")
        return False
    
    def create_vm(
        self,
        vm_id: int,
        vm_name: str,
        qcow_version: Optional[str] = None,
        cores: int = 4,
        memory: int = 8192,
        bridges: Optional[List[str]] = None,
        onboot: bool = True,
        config_disk: Optional[Path] = None
    ) -> bool:
        """
        Create a vJunos-switch VM
        
        Args:
            vm_id: Unique VM ID (also used for console port 5XXX)
            vm_name: VM hostname (will append .switch)
            qcow_version: Specific qcow version or None for latest
            cores: Number of CPU cores
            memory: Memory in MB
            bridges: List of bridge names (default: vmbr101 + 4x vmbr500)
            onboot: Whether to start VM on Proxmox boot
            config_disk: Optional path to config disk image (RAW format) for auto-configuration
            
        Returns:
            True if successful
        """
        if self.vm_exists(vm_id):
            logger.error(f"VM {vm_id} already exists!")
            return False
        
        full_name = f"{vm_name}.switch"
        
        if bridges is None:
            bridges = ["vmbr101", "vmbr500", "vmbr500", "vmbr500", "vmbr500"]
        
        try:
            # Find the qcow image
            qcow_image = self.find_vjunos_image(qcow_version)
            logger.info(f"Creating VM {vm_id} ({full_name}) using {qcow_image.name}")
            
            # Step 1: Create VM with basic config
            logger.info("Step 1: Creating VM...")
            create_cmd = [
                "qm", "create", str(vm_id),
                "--name", full_name,
                "--cores", str(cores),
                "--memory", str(memory),
                "--cpu", "host",
                "--ostype", "l26",  # Linux 2.6+
                "--scsihw", "virtio-scsi-single",
                "--numa", "1",
                "--onboot", "1" if onboot else "0",
                # SMBIOS for vJunos detection and serial console for telnet access
                "--args", f"-smbios type=1,product=VM-VEX -chardev socket,id=serial0,port=5{vm_id},host=0.0.0.0,server=on,wait=off,telnet=on -device isa-serial,chardev=serial0"
            ]
            
            subprocess.run(create_cmd, check=True, capture_output=True)
            logger.info(f"✓ VM {vm_id} created")
            
            # Step 2: Import disk
            logger.info("Step 2: Importing disk (this may take 30-60 seconds)...")
            import_cmd = [
                "qm", "importdisk",
                str(vm_id),
                str(qcow_image),
                "local-lvm",
                "--format", "raw"
            ]
            
            result = subprocess.run(import_cmd, check=True, capture_output=True, text=True)
            logger.info("✓ Disk import command completed")
            
            # Step 3: Wait for import to complete
            if not self.wait_for_disk_import(vm_id, timeout=180):
                logger.error("Disk import did not complete in time")
                return False
            
            # Step 4: Attach the imported disk
            logger.info("Step 3: Attaching disk to VM...")
            
            # Find the unused disk
            config_result = subprocess.run(
                ["qm", "config", str(vm_id)],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse config to find unused disk
            unused_disk = None
            for line in config_result.stdout.split('\n'):
                if line.startswith('unused') and f'vm-{vm_id}-disk-' in line:
                    # Line format: "unused0: local-lvm:vm-201-disk-0"
                    # Extract everything after "unused0: "
                    parts = line.split(':', 1)  # Split only on first colon
                    if len(parts) >= 2:
                        # Remove 'unusedN: ' prefix and strip whitespace
                        unused_disk = parts[1].strip()
                        break
            
            if not unused_disk:
                logger.error("Could not find imported disk to attach")
                return False
            
            attach_cmd = [
                "qm", "set", str(vm_id),
                "--virtio0", f"{unused_disk},iothread=1"
            ]
            subprocess.run(attach_cmd, check=True, capture_output=True)
            logger.info("✓ Disk attached")
            
            # Step 5: Set boot order
            logger.info("Step 4: Configuring boot order...")
            boot_cmd = [
                "qm", "set", str(vm_id),
                "--boot", "order=virtio0"
            ]
            subprocess.run(boot_cmd, check=True, capture_output=True)
            logger.info("✓ Boot order set")
            
            # Step 6: Add network interfaces
            logger.info("Step 5: Adding network interfaces...")
            for idx, bridge in enumerate(bridges[:5]):  # Max 5 interfaces (net0-net4)
                net_cmd = [
                    "qm", "set", str(vm_id),
                    f"--net{idx}", f"virtio={self.gen_mac()},bridge={bridge}"
                ]
                subprocess.run(net_cmd, check=True, capture_output=True)
            logger.info(f"✓ Added {len(bridges)} network interfaces")
            
            # Step 7: Attach config disk if provided
            if config_disk and config_disk.exists():
                logger.info("Step 6: Attaching configuration disk...")
                try:
                    # Following Juniper Proxmox documentation:
                    # Import config disk to local-lvm storage (NOT local)
                    # Use --ide0 for config disk (following Juniper's example)
                    import_config_cmd = [
                        "qm", "disk", "import",
                        str(vm_id),
                        str(config_disk),
                        "local-lvm",
                        "--format", "raw"
                    ]
                    result = subprocess.run(
                        import_config_cmd,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    logger.info("✓ Config disk imported to local-lvm")
                    
                    # Extract the disk location from output
                    # Output format: "Successfully imported disk as 'unused0:local-lvm:vm-XXX-disk-1'"
                    import re
                    match = re.search(r"'unused\d+:(local-lvm:vm-\d+-disk-\d+)'", result.stdout)
                    if match:
                        config_disk_location = match.group(1)
                        logger.info(f"Config disk location: {config_disk_location}")
                        
                        # Attach as IDE0 (following Juniper documentation)
                        attach_config_cmd = [
                            "qm", "set", str(vm_id),
                            "--ide0", f"{config_disk_location},size=16M"
                        ]
                        subprocess.run(attach_config_cmd, check=True, capture_output=True)
                        logger.info("✓ Config disk attached as ide0")
                    else:
                        logger.warning("Could not parse config disk location from import output")
                        logger.info("Check 'qm config {}' and manually attach the unused disk".format(vm_id))
                        
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to attach config disk (non-fatal): {e}")
                    logger.warning(f"Error output: {e.stderr if e.stderr else 'N/A'}")
                    logger.info(f"You can manually attach it later with:")
                    logger.info(f"  qm disk import {vm_id} {config_disk} local-lvm --format raw")
                    logger.info(f"  qm set {vm_id} --ide0 <disk-location>,size=16M")
                except Exception as e:
                    logger.warning(f"Failed to attach config disk (non-fatal): {e}")
                    logger.info(f"You can manually attach it later")
            logger.info(f"✓ VM {vm_id} ({full_name}) created successfully!")
            logger.info(f"  Console: telnet localhost 5{vm_id}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.cmd}")
            logger.error(f"Output: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
            logger.error(f"Error: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
            return False
        except Exception as e:
            logger.error(f"Failed to create VM: {e}")
            return False
    
    def start_vm(self, vm_id: int) -> bool:
        """Start a VM"""
        try:
            subprocess.run(["qm", "start", str(vm_id)], check=True, capture_output=True)
            logger.info(f"✓ VM {vm_id} started")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start VM {vm_id}: {e}")
            return False
    
    def stop_vm(self, vm_id: int) -> bool:
        """Stop a VM"""
        try:
            subprocess.run(["qm", "stop", str(vm_id)], check=True, capture_output=True)
            logger.info(f"✓ VM {vm_id} stopped")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop VM {vm_id}: {e}")
            return False
    
    def delete_vm(self, vm_id: int, purge: bool = True) -> bool:
        """Delete a VM and optionally purge all data"""
        try:
            status = self.get_vm_status(vm_id)
            if status == "running":
                logger.info(f"Stopping VM {vm_id} before deletion...")
                self.stop_vm(vm_id)
                time.sleep(2)
            
            cmd = ["qm", "destroy", str(vm_id)]
            if purge:
                cmd.append("--purge")
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"✓ VM {vm_id} deleted")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete VM {vm_id}: {e}")
            return False
