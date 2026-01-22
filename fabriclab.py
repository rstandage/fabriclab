#!/usr/bin/env python3
"""
FabricLab-NG - Next Generation Virtual Fabric Lab Builder
Automates creation of vJunos-switch VMs on Proxmox and adoption into Mist
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Optional, List, Dict

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from proxmox_vm import ProxmoxVMManager
from mist_client import MistClient, MISTAPI_AVAILABLE
from config_templates import JunosConfigTemplate, FabricTopology, LabConfigManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class FabricLabNG:
    """Main orchestrator for fabric lab creation"""
    
    def __init__(self):
        self.vm_manager = ProxmoxVMManager()
        self.mist_client: Optional[MistClient] = None
    
    def setup_mist(self, config_file: Optional[Path] = None) -> bool:
        """Setup Mist API connection"""
        if not MISTAPI_AVAILABLE:
            logger.warning("Mist API not available - will skip adoption steps")
            return False
        
        try:
            self.mist_client = MistClient(config_file)
            return self.mist_client.connect()
        except Exception as e:
            logger.error(f"Failed to setup Mist: {e}")
            return False
    
    def create_switch(
        self,
        vm_id: int,
        vm_name: str,
        qcow_version: Optional[str] = None,
        cores: int = 4,
        memory: int = 8192,
        bridges: Optional[List[str]] = None,
        auto_start: bool = False,
        with_lab_config: bool = False,
        junos_version: Optional[str] = None,
        adopt_template: Optional[Path] = None
    ) -> bool:
        """
        Create a single virtual switch
        
        Args:
            vm_id: Unique VM ID
            vm_name: Switch hostname
            qcow_version: Specific qcow version or None for latest
            cores: Number of CPU cores
            memory: Memory in MB
            bridges: List of bridge names
            auto_start: Whether to auto-start the VM
            with_lab_config: Whether to create and attach lab config disk
            junos_version: Junos version for lab config
            adopt_template: Path to Mist adopt template for lab config
            
        Returns:
            True if successful
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Creating virtual switch: {vm_name} (ID: {vm_id})")
        logger.info(f"{'='*60}")
        
        # Create lab config disk if requested
        config_disk_path = None
        if with_lab_config:
            logger.info("\nCreating lab configuration disk...")
            success, config_disk_path = LabConfigManager.create_lab_config(
                vm_name=vm_name,
                junos_version=junos_version,
                adopt_template=adopt_template
            )
            if not success:
                logger.error("Failed to create lab config disk")
                return False
        
        # Create the VM
        success = self.vm_manager.create_vm(
            vm_id=vm_id,
            vm_name=vm_name,
            qcow_version=qcow_version,
            cores=cores,
            memory=memory,
            bridges=bridges,
            onboot=True,
            config_disk=config_disk_path
        )
        
        if not success:
            logger.error(f"Failed to create VM {vm_id}")
            return False
        
        # Start if requested
        if auto_start:
            logger.info("Starting VM...")
            self.vm_manager.start_vm(vm_id)
        
        logger.info(f"\n✓ Switch {vm_name} created successfully!")
        logger.info(f"  VM ID: {vm_id}")
        logger.info(f"  Console: telnet localhost 5{vm_id}")
        logger.info(f"  Status: {'Running' if auto_start else 'Stopped'}")
        if with_lab_config:
            logger.info(f"  Config: Auto-configuration enabled")
        
        return True
    
    def create_topology(
        self,
        topology_name: str,
        qcow_version: Optional[str] = None,
        auto_start: bool = False
    ) -> bool:
        """
        Create a complete fabric topology
        
        Args:
            topology_name: Name of the topology to create
            qcow_version: Specific qcow version or None for latest
            auto_start: Whether to auto-start all VMs
            
        Returns:
            True if successful
        """
        topo = FabricTopology.get_topology(topology_name)
        if not topo:
            logger.error(f"Topology '{topology_name}' not found")
            logger.info("Available topologies:")
            for name, desc in FabricTopology.list_topologies().items():
                logger.info(f"  - {name}: {desc}")
            return False
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Creating topology: {topology_name}")
        logger.info(f"Description: {topo['description']}")
        logger.info(f"{'='*60}\n")
        
        # Create all switches
        failed = []
        for switch in topo["switches"]:
            success = self.create_switch(
                vm_id=switch["id"],
                vm_name=switch["name"],
                qcow_version=qcow_version,
                auto_start=auto_start
            )
            
            if not success:
                failed.append(switch["name"])
        
        if failed:
            logger.error(f"\nFailed to create: {', '.join(failed)}")
            return False
        
        logger.info(f"\n{'='*60}")
        logger.info("✓ Topology created successfully!")
        logger.info(f"{'='*60}")
        
        logger.info("\nNext steps:")
        logger.info("1. Configure bridge connections in Proxmox UI based on topology")
        logger.info("2. Start the VMs if not auto-started")
        logger.info("3. Console into each switch and apply configuration")
        logger.info("4. Run adoption process to connect to Mist")
        
        return True
    
    def generate_adoption_config(
        self,
        vm_name: str,
        device_id: str,
        secret: str,
        ssh_key: str,
        output_dir: Optional[Path] = None
    ) -> bool:
        """
        Generate adoption configuration for a switch
        
        Args:
            vm_name: Switch hostname
            device_id: Mist device ID
            secret: Mist secret
            ssh_key: SSH RSA public key
            output_dir: Directory to save config (default: ./configs)
            
        Returns:
            True if successful
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "configs"
        
        config = JunosConfigTemplate.generate_full_config(
            hostname=vm_name,
            device_id=device_id,
            secret=secret,
            ssh_key=ssh_key,
            enable_lldp=True
        )
        
        output_file = output_dir / f"{vm_name}.conf"
        return JunosConfigTemplate.save_config(config, output_file)
    
    def create_lab_config(
        self,
        vm_name: str,
        junos_version: Optional[str] = None,
        adopt_template: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ) -> bool:
        """
        Create a lab configuration disk for auto-deployment to Mist
        
        This creates a configuration disk image that can be attached to a vJunos-switch VM
        to automatically configure it on first boot and adopt it into Mist Cloud.
        
        Args:
            vm_name: Switch hostname
            junos_version: Optional Junos version to set in config
            adopt_template: Optional path to Mist adopt-template.txt file
            output_dir: Directory to save files (default: ./config)
            
        Returns:
            True if successful
        """
        success, config_disk = LabConfigManager.create_lab_config(
            vm_name=vm_name,
            junos_version=junos_version,
            adopt_template=adopt_template,
            output_dir=output_dir
        )
        
        if success:
            logger.info("\n" + "="*60)
            logger.info("✓ Lab configuration disk created successfully!")
            logger.info("="*60)
            logger.info(f"\nConfig disk: {config_disk}")
            logger.info("\nNext steps:")
            logger.info("1. Copy the config disk to your hypervisor:")
            logger.info(f"   scp {config_disk} root@hypervisor:/var/lib/libvirt/images/")
            logger.info("2. Attach it to your VM during creation:")
            logger.info(f"   --disk path=/var/lib/libvirt/images/{config_disk.name}")
            logger.info("3. Start the VM - it will auto-configure and adopt to Mist")
            
        return success
    
    def list_vms(self):
        """List all VMs and their status"""
        logger.info("\nListing Proxmox VMs...")
        # This would query qm list, but for now just show how to check
        logger.info("Run: qm list")
    
    def interactive_create(self):
        """Interactive mode for creating a single switch"""
        print("\n" + "="*60)
        print("FabricLab-NG - Virtual Switch Creator")
        print("="*60 + "\n")
        
        # Get VM ID
        while True:
            vm_id_str = input("Enter VM ID (3 digits, e.g., 201): ").strip()
            if vm_id_str.isdigit() and len(vm_id_str) == 3:
                vm_id = int(vm_id_str)
                if self.vm_manager.vm_exists(vm_id):
                    print(f"  ⚠ VM {vm_id} already exists!")
                    continue
                break
            print("  ✗ Invalid ID (must be 3 digits)")
        
        # Get VM name
        vm_name = input("Enter VM name (e.g., spine-1): ").strip()
        if not vm_name:
            print("  ✗ Name cannot be empty")
            return False
        
        # Ask about auto-start
        auto_start_str = input("Auto-start VM after creation? (y/N): ").strip().lower()
        auto_start = auto_start_str in ['y', 'yes']
        
        # Create the switch
        return self.create_switch(
            vm_id=vm_id,
            vm_name=vm_name,
            auto_start=auto_start
        )


def main():
    parser = argparse.ArgumentParser(
        description="FabricLab-NG - Virtual Fabric Lab Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  %(prog)s create

  # Create a single switch
  %(prog)s create --id 201 --name spine-1 --start

  # Create switch with auto-configuration for Mist
  %(prog)s create --id 201 --name spine-1 --with-lab-config --start
  %(prog)s create --id 201 --name spine-1 --with-lab-config --adopt-template adopt.txt --start

  # Create a topology
  %(prog)s topology --name spine-leaf-2x2 --start

  # List available topologies
  %(prog)s topology --list

  # Create lab config disk only (for existing VMs)
  %(prog)s lab --name spine-1
  %(prog)s lab --name spine-1 --version 25.4R1.12 --adopt-template adopt-template.txt

  # Generate adoption config
  %(prog)s adopt --name spine-1 --device-id xxx --secret yyy --ssh-key "ssh-rsa ..."
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a virtual switch")
    create_parser.add_argument("--id", type=int, help="VM ID (3 digits)")
    create_parser.add_argument("--name", help="VM name")
    create_parser.add_argument("--version", help="Specific qcow version")
    create_parser.add_argument("--cores", type=int, default=4, help="CPU cores (default: 4)")
    create_parser.add_argument("--memory", type=int, default=8192, help="Memory in MB (default: 8192)")
    create_parser.add_argument("--start", action="store_true", help="Auto-start VM")
    create_parser.add_argument(
        "--with-lab-config",
        action="store_true",
        help="Create and attach lab configuration disk for auto-deploy to Mist"
    )
    create_parser.add_argument(
        "--junos-version",
        help="Junos version for lab config (e.g., 25.4R1.12)"
    )
    create_parser.add_argument(
        "--adopt-template",
        type=Path,
        help="Path to Mist adopt-template.txt for automatic adoption"
    )
    
    # Topology command
    topo_parser = subparsers.add_parser("topology", help="Create a fabric topology")
    topo_parser.add_argument("--name", help="Topology name")
    topo_parser.add_argument("--list", action="store_true", help="List available topologies")
    topo_parser.add_argument("--show", help="Show topology details")
    topo_parser.add_argument("--version", help="Specific qcow version")
    topo_parser.add_argument("--start", action="store_true", help="Auto-start all VMs")
    
    # Adopt command
    adopt_parser = subparsers.add_parser("adopt", help="Generate adoption configuration")
    adopt_parser.add_argument("--name", required=True, help="VM name")
    adopt_parser.add_argument("--device-id", help="Mist device ID")
    adopt_parser.add_argument("--secret", help="Mist secret")
    adopt_parser.add_argument("--ssh-key", help="Mist SSH RSA key")
    adopt_parser.add_argument("--output", type=Path, help="Output directory")
    
    # Lab command - NEW
    lab_parser = subparsers.add_parser(
        "lab",
        help="Create lab configuration disk for auto-deploy to Mist",
        description="""Create a configuration disk image for vJunos-switch that includes
        the default lab configuration customized with hostname and optional Mist adoption.
        This disk can be attached to a VM for automatic configuration on first boot."""
    )
    lab_parser.add_argument("--name", required=True, help="Switch hostname")
    lab_parser.add_argument("--version", help="Junos OS version (e.g., 25.4R1.12)")
    lab_parser.add_argument(
        "--adopt-template",
        type=Path,
        help="Path to adopt-template.txt from Mist (for auto-adoption)"
    )
    lab_parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default: ./config)"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List VMs")
    
    args = parser.parse_args()
    
    # Initialize FabricLab
    lab = FabricLabNG()
    
    # Execute command
    if args.command == "create":
        if args.id and args.name:
            success = lab.create_switch(
                vm_id=args.id,
                vm_name=args.name,
                qcow_version=args.version,
                cores=args.cores,
                memory=args.memory,
                auto_start=args.start,
                with_lab_config=args.with_lab_config,
                junos_version=args.junos_version,
                adopt_template=args.adopt_template
            )
            sys.exit(0 if success else 1)
        else:
            # Interactive mode
            success = lab.interactive_create()
            sys.exit(0 if success else 1)
    
    elif args.command == "topology":
        if args.list:
            print("\nAvailable Topologies:")
            print("-" * 60)
            for name, desc in FabricTopology.list_topologies().items():
                print(f"  {name:20} - {desc}")
            print()
            sys.exit(0)
        
        if args.show:
            FabricTopology.print_topology(args.show)
            sys.exit(0)
        
        if args.name:
            success = lab.create_topology(
                topology_name=args.name,
                qcow_version=args.version,
                auto_start=args.start
            )
            sys.exit(0 if success else 1)
        else:
            print("Error: --name required (or use --list to see options)")
            sys.exit(1)
    
    elif args.command == "adopt":
        if not all([args.device_id, args.secret, args.ssh_key]):
            print("Error: --device-id, --secret, and --ssh-key are required")
            print("Get these from: Mist Organization > Settings > Device Adoption")
            sys.exit(1)
        
        success = lab.generate_adoption_config(
            vm_name=args.name,
            device_id=args.device_id,
            secret=args.secret,
            ssh_key=args.ssh_key,
            output_dir=args.output
        )
        sys.exit(0 if success else 1)
    
    elif args.command == "lab":
        success = lab.create_lab_config(
            vm_name=args.name,
            junos_version=args.version,
            adopt_template=args.adopt_template,
            output_dir=args.output
        )
        sys.exit(0 if success else 1)
    
    elif args.command == "list":
        lab.list_vms()
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
