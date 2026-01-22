#!/usr/bin/env python3
"""
Mist API Client for vJunos-switch adoption and management
"""

import os
import logging
import time
from typing import Optional, Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import mistapi
    from mistapi import APISession
    from mistapi.cli import Cli
    MISTAPI_AVAILABLE = True
except ImportError:
    MISTAPI_AVAILABLE = False
    logger.warning("mistapi not installed. Run: pip3 install mistapi")


class MistClient:
    """Handles Mist API interactions for switch adoption"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize Mist API client
        
        Args:
            config_file: Path to mistapi config file (default: ~/.mist_env)
        """
        if not MISTAPI_AVAILABLE:
            raise RuntimeError(
                "mistapi package not installed.\n"
                "Install with: pip3 install mistapi"
            )
        
        self.config_file = config_file or Path.home() / ".mist_env"
        self.session: Optional[APISession] = None
        self.org_id: Optional[str] = None
        self.site_id: Optional[str] = None
    
    def connect(self, org_id: Optional[str] = None) -> bool:
        """
        Connect to Mist API
        
        Args:
            org_id: Organization ID (will use from config if not provided)
            
        Returns:
            True if successful
        """
        try:
            # Load configuration
            if self.config_file.exists():
                logger.info(f"Loading Mist config from {self.config_file}")
                cli = Cli(env_file=str(self.config_file))
                self.session = cli.session
            else:
                logger.warning(f"Config file not found: {self.config_file}")
                logger.info("Create it with: mist_library init")
                # Try to create session from environment variables
                self.session = APISession()
            
            # Verify connection
            response = mistapi.api.v1.self.getSelf(self.session)
            if response.status_code == 200:
                user_info = response.data
                logger.info(f"✓ Connected to Mist as: {user_info.get('email', 'Unknown')}")
                
                # Set org_id
                if org_id:
                    self.org_id = org_id
                elif hasattr(self.session, 'org_id') and self.session.org_id:
                    self.org_id = self.session.org_id
                
                if self.org_id:
                    logger.info(f"  Using Org ID: {self.org_id}")
                else:
                    logger.warning("  No org_id set - will need to specify for operations")
                
                return True
            else:
                logger.error(f"Failed to authenticate: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Mist: {e}")
            return False
    
    def list_orgs(self) -> List[Dict[str, Any]]:
        """List all organizations the user has access to"""
        try:
            response = mistapi.api.v1.orgs.listOrgs(self.session)
            if response.status_code == 200:
                return response.data
            return []
        except Exception as e:
            logger.error(f"Failed to list orgs: {e}")
            return []
    
    def list_sites(self, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sites in an organization"""
        org_id = org_id or self.org_id
        if not org_id:
            logger.error("No org_id provided")
            return []
        
        try:
            response = mistapi.api.v1.orgs.sites.listOrgSites(self.session, org_id)
            if response.status_code == 200:
                return response.data
            return []
        except Exception as e:
            logger.error(f"Failed to list sites: {e}")
            return []
    
    def get_adoption_command(
        self,
        org_id: Optional[str] = None,
        site_id: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Get the adoption command configuration for switches
        
        Returns:
            Dict with 'device_id', 'secret', and 'config' (full Junos config)
        """
        org_id = org_id or self.org_id
        site_id = site_id or self.site_id
        
        if not org_id:
            logger.error("No org_id provided")
            return None
        
        try:
            # Get org device adoption info
            response = mistapi.api.v1.orgs.setting.getOrgSettings(self.session, org_id)
            if response.status_code != 200:
                logger.error(f"Failed to get org settings: {response.status_code}")
                return None
            
            settings = response.data
            
            # Extract outbound SSH settings
            device_id = None
            secret = None
            
            # Try to get from device adoption API (preferred method)
            # Note: The actual API endpoint may vary - this is a common pattern
            response = mistapi.api.v1.orgs.inventory.getOrgInventory(
                self.session, 
                org_id,
                type="switch",
                limit=1
            )
            
            if response.status_code == 200 and len(response.data) > 0:
                # Get adoption details from first switch or from org settings
                pass
            
            # For now, generate the config template
            # In production, you'd get device_id and secret from Mist
            config_template = """
#sets password as Juniper123!
set system root-authentication encrypted-password $6$.tMirbxZ$/BIGvrB/JknHxubYMtQa38iuaAH4ii5mcD5Atjuh.ZDcmQYNIZRZEKsHNryMs/cGML5PqkWouWwL9TKA/l0cC/
delete chassis auto-image-upgrade
set system services ssh protocol-version v2
set system authentication-order password
set system login user mist class super-user
set system login user mist authentication encrypted-password $6$xo.kDu2lveY4mNUv$bgi/yh98Pg48wIihHrs6DCYwOLMh5Pz5xKzkT8Vfl.E1vhQTw163PkrwekAXKomtFfF/u93hVLLVLx66pKS9q.
set system login user mist authentication ssh-rsa "<SSH_KEY>"
set system services outbound-ssh client mist device-id <DEVICE_ID>
set system services outbound-ssh client mist secret <SECRET>
set system services outbound-ssh client mist services netconf keep-alive retry 12 timeout 5
set system services outbound-ssh client mist oc-term.mistsys.net port 2200 timeout 60 retry 1000
""".strip()
            
            logger.info("✓ Generated adoption config template")
            logger.warning("  You'll need to get device_id and secret from Mist UI")
            logger.warning("  Go to: Organization > Settings > Device Adoption")
            
            return {
                "config_template": config_template,
                "org_id": org_id,
                "site_id": site_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get adoption command: {e}")
            return None
    
    def claim_device(
        self,
        mac_address: str,
        org_id: Optional[str] = None,
        site_id: Optional[str] = None
    ) -> bool:
        """
        Claim a device to the organization and optionally assign to site
        
        Args:
            mac_address: MAC address of the device
            org_id: Organization ID
            site_id: Site ID (optional)
            
        Returns:
            True if successful
        """
        org_id = org_id or self.org_id
        if not org_id:
            logger.error("No org_id provided")
            return False
        
        try:
            # Claim device to org
            response = mistapi.api.v1.orgs.inventory.addOrgInventory(
                self.session,
                org_id,
                body=[{"mac": mac_address}]
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✓ Device {mac_address} claimed to org")
                
                # Assign to site if provided
                if site_id:
                    response = mistapi.api.v1.orgs.inventory.updateOrgInventoryAssignment(
                        self.session,
                        org_id,
                        body={
                            "op": "assign",
                            "site_id": site_id,
                            "macs": [mac_address]
                        }
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"✓ Device assigned to site {site_id}")
                    else:
                        logger.warning(f"Failed to assign to site: {response.status_code}")
                
                return True
            else:
                logger.error(f"Failed to claim device: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to claim device: {e}")
            return False
    
    def get_device_status(
        self,
        mac_address: str,
        org_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get device status from inventory
        
        Args:
            mac_address: MAC address of the device
            org_id: Organization ID
            
        Returns:
            Device info dict or None
        """
        org_id = org_id or self.org_id
        if not org_id:
            logger.error("No org_id provided")
            return None
        
        try:
            response = mistapi.api.v1.orgs.inventory.getOrgInventory(
                self.session,
                org_id,
                mac=mac_address
            )
            
            if response.status_code == 200 and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get device status: {e}")
            return None
    
    def wait_for_device_connection(
        self,
        mac_address: str,
        timeout: int = 300,
        org_id: Optional[str] = None
    ) -> bool:
        """
        Wait for device to connect to Mist
        
        Args:
            mac_address: MAC address of the device
            timeout: Maximum seconds to wait
            org_id: Organization ID
            
        Returns:
            True if device connects within timeout
        """
        org_id = org_id or self.org_id
        if not org_id:
            logger.error("No org_id provided")
            return False
        
        logger.info(f"Waiting for device {mac_address} to connect (timeout: {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            device = self.get_device_status(mac_address, org_id)
            
            if device and device.get("connected"):
                logger.info(f"✓ Device {mac_address} connected!")
                logger.info(f"  Status: {device.get('status', 'unknown')}")
                logger.info(f"  Model: {device.get('model', 'unknown')}")
                return True
            
            time.sleep(10)
        
        logger.error(f"Timeout waiting for device {mac_address} to connect")
        return False
