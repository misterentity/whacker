"""
upnp_port_manager.py - UPnP Port Management for Plex RAR Bridge

This module provides automatic port forwarding using UPnP (Universal Plug and Play)
to ensure the Python VFS HTTP server can work through firewalls and routers.

Features:
- Automatic UPnP router discovery
- Port forwarding management
- Automatic cleanup on shutdown
- Configurable timeout and retry settings
- Fallback handling for non-UPnP environments
"""

import socket
import time
import threading
import logging
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from datetime import datetime, timedelta
import struct

class UPnPPortManager:
    """Manages UPnP port forwarding for the RAR VFS HTTP server"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.upnp_config = config.get('upnp', {})
        self.enabled = self.upnp_config.get('enabled', True)
        self.timeout = self.upnp_config.get('timeout', 10)
        self.retry_count = self.upnp_config.get('retry_count', 3)
        self.lease_duration = self.upnp_config.get('lease_duration', 3600)  # 1 hour
        
        # Router discovery
        self.router_info = None
        self.control_url = None
        self.service_type = None
        
        # Port management
        self.forwarded_ports = {}  # {port: description}
        self.renewal_thread = None
        self.shutdown_event = threading.Event()
        
    def is_enabled(self):
        """Check if UPnP is enabled"""
        return self.enabled
    
    def discover_router(self):
        """Discover UPnP-enabled router on the network"""
        if not self.enabled:
            return False
            
        try:
            self.logger.info("Discovering UPnP router...")
            
            # SSDP discover message
            ssdp_request = (
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                "MAN: \"ssdp:discover\"\r\n"
                "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
                "MX: 3\r\n\r\n"
            )
            
            # Send SSDP request
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            sock.sendto(ssdp_request.encode(), ('239.255.255.250', 1900))
            
            # Wait for response
            response, addr = sock.recvfrom(1024)
            sock.close()
            
            # Parse response
            response_str = response.decode()
            location = None
            for line in response_str.split('\r\n'):
                if line.startswith('LOCATION:'):
                    location = line.split(':', 1)[1].strip()
                    break
            
            if location:
                self.logger.info(f"Found UPnP router at: {location}")
                return self._parse_router_info(location)
            
        except socket.timeout:
            self.logger.warning("UPnP router discovery timed out")
        except Exception as e:
            self.logger.error(f"UPnP router discovery failed: {e}")
        
        return False
    
    def _parse_router_info(self, location):
        """Parse router information from UPnP location"""
        try:
            # Get device description
            response = requests.get(location, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Find service information
            namespaces = {'device': 'urn:schemas-upnp-org:device-1-0'}
            
            # Look for WANIPConnection service
            services = root.findall('.//device:service', namespaces)
            for service in services:
                service_type = service.find('device:serviceType', namespaces)
                if service_type is not None and 'WANIPConnection' in service_type.text:
                    control_url = service.find('device:controlURL', namespaces)
                    if control_url is not None:
                        # Build full control URL
                        base_url = location.rsplit('/', 1)[0]
                        self.control_url = f"{base_url}{control_url.text}"
                        self.service_type = service_type.text
                        
                        self.logger.info(f"UPnP control URL: {self.control_url}")
                        return True
            
            # Fallback to WANPPPConnection
            for service in services:
                service_type = service.find('device:serviceType', namespaces)
                if service_type is not None and 'WANPPPConnection' in service_type.text:
                    control_url = service.find('device:controlURL', namespaces)
                    if control_url is not None:
                        base_url = location.rsplit('/', 1)[0]
                        self.control_url = f"{base_url}{control_url.text}"
                        self.service_type = service_type.text
                        
                        self.logger.info(f"UPnP control URL (PPP): {self.control_url}")
                        return True
                        
        except Exception as e:
            self.logger.error(f"Failed to parse router info: {e}")
        
        return False
    
    def add_port_mapping(self, port, description="Plex RAR Bridge VFS"):
        """Add port forwarding rule"""
        if not self.enabled or not self.control_url:
            return False
            
        try:
            # Get local IP
            local_ip = self._get_local_ip()
            if not local_ip:
                self.logger.error("Could not determine local IP address")
                return False
            
            # SOAP request for port mapping
            soap_body = f"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:AddPortMapping xmlns:u="{self.service_type}">
      <NewRemoteHost></NewRemoteHost>
      <NewExternalPort>{port}</NewExternalPort>
      <NewProtocol>TCP</NewProtocol>
      <NewInternalPort>{port}</NewInternalPort>
      <NewInternalClient>{local_ip}</NewInternalClient>
      <NewEnabled>1</NewEnabled>
      <NewPortMappingDescription>{description}</NewPortMappingDescription>
      <NewLeaseDuration>{self.lease_duration}</NewLeaseDuration>
    </u:AddPortMapping>
  </s:Body>
</s:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset="utf-8"',
                'SOAPAction': f'"{self.service_type}#AddPortMapping"'
            }
            
            response = requests.post(self.control_url, data=soap_body, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                self.forwarded_ports[port] = description
                self.logger.info(f"Successfully opened port {port} via UPnP")
                return True
            else:
                self.logger.error(f"UPnP port mapping failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to add port mapping: {e}")
            return False
    
    def remove_port_mapping(self, port):
        """Remove port forwarding rule"""
        if not self.enabled or not self.control_url:
            return False
            
        try:
            # SOAP request for removing port mapping
            soap_body = f"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:DeletePortMapping xmlns:u="{self.service_type}">
      <NewRemoteHost></NewRemoteHost>
      <NewExternalPort>{port}</NewExternalPort>
      <NewProtocol>TCP</NewProtocol>
    </u:DeletePortMapping>
  </s:Body>
</s:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset="utf-8"',
                'SOAPAction': f'"{self.service_type}#DeletePortMapping"'
            }
            
            response = requests.post(self.control_url, data=soap_body, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                if port in self.forwarded_ports:
                    del self.forwarded_ports[port]
                self.logger.info(f"Successfully removed port {port} via UPnP")
                return True
            else:
                self.logger.error(f"UPnP port removal failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove port mapping: {e}")
            return False
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            # Connect to a remote address to determine local IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            sock.close()
            return local_ip
        except Exception:
            return None
    
    def start_renewal_thread(self):
        """Start thread to renew port mappings"""
        if not self.enabled or self.renewal_thread:
            return
            
        self.renewal_thread = threading.Thread(target=self._renewal_worker, daemon=True)
        self.renewal_thread.start()
        self.logger.info("UPnP port renewal thread started")
    
    def _renewal_worker(self):
        """Worker thread for renewing port mappings"""
        renewal_interval = self.lease_duration // 2  # Renew at half lease time
        
        while not self.shutdown_event.wait(renewal_interval):
            if self.forwarded_ports:
                self.logger.debug("Renewing UPnP port mappings...")
                
                # Renew all active port mappings
                ports_to_renew = list(self.forwarded_ports.keys())
                for port in ports_to_renew:
                    description = self.forwarded_ports.get(port, "Plex RAR Bridge VFS")
                    self.add_port_mapping(port, description)
    
    def setup_vfs_port(self, port, description="Plex RAR Bridge VFS Server"):
        """Setup port forwarding for VFS HTTP server"""
        if not self.enabled:
            self.logger.info("UPnP disabled, skipping port forwarding")
            return False
            
        # Try to discover router if not already done
        if not self.control_url:
            if not self.discover_router():
                self.logger.warning("No UPnP router found, port forwarding unavailable")
                return False
        
        # Add port mapping with retries
        for attempt in range(self.retry_count):
            if self.add_port_mapping(port, description):
                # Start renewal thread if successful
                if not self.renewal_thread:
                    self.start_renewal_thread()
                return True
            
            if attempt < self.retry_count - 1:
                self.logger.warning(f"UPnP port mapping attempt {attempt + 1} failed, retrying...")
                time.sleep(2)
        
        self.logger.error("All UPnP port mapping attempts failed")
        return False
    
    def cleanup_all_ports(self):
        """Clean up all port mappings"""
        if not self.enabled:
            return
            
        self.logger.info("Cleaning up UPnP port mappings...")
        
        # Stop renewal thread
        if self.renewal_thread:
            self.shutdown_event.set()
            self.renewal_thread.join(timeout=5)
            self.renewal_thread = None
        
        # Remove all port mappings
        ports_to_remove = list(self.forwarded_ports.keys())
        for port in ports_to_remove:
            self.remove_port_mapping(port)
        
        self.logger.info("UPnP cleanup completed")
    
    def get_status(self):
        """Get UPnP status information"""
        return {
            'enabled': self.enabled,
            'router_discovered': self.control_url is not None,
            'control_url': self.control_url,
            'service_type': self.service_type,
            'forwarded_ports': dict(self.forwarded_ports),
            'renewal_active': self.renewal_thread is not None and self.renewal_thread.is_alive()
        }

class UPnPIntegratedVFS:
    """Wrapper class that integrates UPnP with the RAR VFS"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.upnp_manager = UPnPPortManager(config, logger)
        self.vfs_port = None
        
    def setup_port_forwarding(self, port):
        """Setup UPnP port forwarding for VFS server"""
        self.vfs_port = port
        
        if self.upnp_manager.is_enabled():
            success = self.upnp_manager.setup_vfs_port(port, "Plex RAR Bridge VFS Server")
            if success:
                self.logger.info(f"UPnP port forwarding active for port {port}")
                return True
            else:
                self.logger.warning(f"UPnP port forwarding failed for port {port}")
                return False
        else:
            self.logger.info("UPnP disabled, manual port forwarding may be required")
            return False
    
    def cleanup_port_forwarding(self):
        """Clean up UPnP port forwarding"""
        if self.upnp_manager.is_enabled():
            self.upnp_manager.cleanup_all_ports()
    
    def get_upnp_status(self):
        """Get UPnP status"""
        return self.upnp_manager.get_status() 