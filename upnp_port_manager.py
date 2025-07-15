"""
upnp_port_manager.py - Enhanced UPnP Port Management for Plex RAR Bridge

This module provides automatic port forwarding using UPnP (Universal Plug and Play)
to ensure the Python VFS HTTP server can work through firewalls and routers.

Features:
- Enhanced automatic UPnP router discovery with multiple compatibility modes
- Improved SSDP discovery with better router support
- Multiple service type detection and fallback mechanisms
- Port forwarding management with robust error handling
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
import re
import json

class EnhancedUPnPPortManager:
    """Enhanced UPnP Port Manager with improved router compatibility"""
    
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
        self.discovered_devices = []
        
        # Port management
        self.forwarded_ports = {}  # {port: description}
        self.renewal_thread = None
        self.shutdown_event = threading.Event()
        
    def is_enabled(self):
        """Check if UPnP is enabled"""
        return self.enabled
    
    def discover_router(self):
        """Enhanced UPnP router discovery with multiple compatibility modes"""
        if not self.enabled:
            return False
            
        # Try multiple discovery methods in order of preference
        discovery_methods = [
            ('enhanced_ssdp', self._discover_enhanced_ssdp),
            ('broadcast_discovery', self._discover_broadcast),
            ('multicast_discovery', self._discover_multicast),
            ('legacy_discovery', self._discover_legacy),
            ('aggressive_discovery', self._discover_aggressive)
        ]
        
        for method_name, method_func in discovery_methods:
            try:
                self.logger.info(f"Trying {method_name} discovery method...")
                if method_func():
                    self.logger.info(f"Successfully discovered router using {method_name}")
                    return True
            except Exception as e:
                self.logger.debug(f"{method_name} failed: {e}")
                continue
        
        self.logger.warning("All UPnP discovery methods failed")
        return False
    
    def _discover_enhanced_ssdp(self):
        """Enhanced SSDP discovery with better compatibility"""
        try:
            # Multiple SSDP requests with different formats
            ssdp_requests = [
                # Standard IGD request
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                "MAN: \"ssdp:discover\"\r\n"
                "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
                "MX: 3\r\n\r\n",
                
                # IGD version 2
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                "MAN: \"ssdp:discover\"\r\n"
                "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:2\r\n"
                "MX: 3\r\n\r\n",
                
                # Root device discovery
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                "MAN: \"ssdp:discover\"\r\n"
                "ST: upnp:rootdevice\r\n"
                "MX: 3\r\n\r\n",
                
                # All devices
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                "MAN: \"ssdp:discover\"\r\n"
                "ST: ssdp:all\r\n"
                "MX: 5\r\n\r\n"
            ]
            
            discovered_devices = []
            
            for i, ssdp_request in enumerate(ssdp_requests):
                self.logger.debug(f"Sending SSDP request {i+1}/{len(ssdp_requests)}")
                
                # Create socket with enhanced configuration
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(8)
                
                try:
                    # Enhanced socket configuration
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    
                    # Try different binding approaches
                    try:
                        sock.bind(('', 0))  # Bind to any available port
                    except:
                        try:
                            sock.bind(('0.0.0.0', 0))  # Alternative binding
                        except:
                            pass  # Continue without binding
                    
                    # Send request multiple times for better delivery
                    for attempt in range(3):
                        try:
                            sock.sendto(ssdp_request.encode('utf-8'), ('239.255.255.250', 1900))
                            time.sleep(0.1)  # Small delay between sends
                        except Exception as e:
                            self.logger.debug(f"Send attempt {attempt+1} failed: {e}")
                    
                    # Collect responses with longer timeout
                    start_time = time.time()
                    while time.time() - start_time < 8:
                        try:
                            remaining_time = 8 - (time.time() - start_time)
                            if remaining_time <= 0:
                                break
                            
                            sock.settimeout(min(remaining_time, 2.0))
                            response, addr = sock.recvfrom(2048)
                            
                            device_info = self._parse_ssdp_response(response, addr)
                            if device_info:
                                discovered_devices.append(device_info)
                                self.logger.debug(f"Found device: {device_info}")
                            
                        except socket.timeout:
                            continue
                        except Exception as e:
                            self.logger.debug(f"Response receive error: {e}")
                            break
                    
                finally:
                    sock.close()
                
                # Small delay between different request types
                time.sleep(0.5)
            
            # Process discovered devices
            if discovered_devices:
                self.logger.info(f"Found {len(discovered_devices)} UPnP devices")
                
                # Try to find a compatible router
                for device in discovered_devices:
                    if self._test_device_compatibility(device):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Enhanced SSDP discovery failed: {e}")
            return False
    
    def _discover_broadcast(self):
        """Broadcast-based discovery for stubborn routers"""
        try:
            self.logger.debug("Trying broadcast discovery...")
            
            # Get local network information
            local_ip = self._get_local_ip()
            if not local_ip:
                return False
            
            # Calculate broadcast address
            ip_parts = local_ip.split('.')
            broadcast_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
            
            # Enhanced broadcast request
            broadcast_request = (
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                "MAN: \"ssdp:discover\"\r\n"
                "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
                "MX: 3\r\n"
                "USER-AGENT: Plex RAR Bridge/1.0\r\n\r\n"
            )
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            try:
                # Send to both multicast and broadcast
                sock.sendto(broadcast_request.encode(), ('239.255.255.250', 1900))
                sock.sendto(broadcast_request.encode(), (broadcast_ip, 1900))
                
                # Listen for responses
                start_time = time.time()
                while time.time() - start_time < 5:
                    try:
                        response, addr = sock.recvfrom(2048)
                        device_info = self._parse_ssdp_response(response, addr)
                        if device_info and self._test_device_compatibility(device_info):
                            return True
                    except socket.timeout:
                        continue
                    except Exception as e:
                        self.logger.debug(f"Broadcast response error: {e}")
                        break
                        
            finally:
                sock.close()
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Broadcast discovery failed: {e}")
            return False
    
    def _discover_multicast(self):
        """Enhanced multicast discovery with better socket configuration"""
        try:
            self.logger.debug("Trying enhanced multicast discovery...")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            # Enhanced multicast configuration
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                # Join multicast group
                mreq = struct.pack('4sl', socket.inet_aton('239.255.255.250'), socket.INADDR_ANY)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                
                # Set multicast TTL
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                
                # Enhanced multicast request
                multicast_request = (
                    "M-SEARCH * HTTP/1.1\r\n"
                    "HOST: 239.255.255.250:1900\r\n"
                    "MAN: \"ssdp:discover\"\r\n"
                    "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
                    "MX: 3\r\n"
                    "USER-AGENT: Windows/10.0 UPnP/1.0 Plex RAR Bridge/1.0\r\n\r\n"
                )
                
                sock.sendto(multicast_request.encode(), ('239.255.255.250', 1900))
                
                # Listen for responses
                start_time = time.time()
                while time.time() - start_time < 5:
                    try:
                        response, addr = sock.recvfrom(2048)
                        device_info = self._parse_ssdp_response(response, addr)
                        if device_info and self._test_device_compatibility(device_info):
                            return True
                    except socket.timeout:
                        continue
                    except Exception as e:
                        self.logger.debug(f"Multicast response error: {e}")
                        break
                        
            finally:
                sock.close()
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Multicast discovery failed: {e}")
            return False
    
    def _discover_legacy(self):
        """Legacy discovery method for older routers"""
        try:
            self.logger.debug("Trying legacy discovery...")
            
            # Simple legacy request
            legacy_request = (
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                "MAN: \"ssdp:discover\"\r\n"
                "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
                "MX: 3\r\n\r\n"
            )
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)  # Longer timeout for legacy
            
            try:
                sock.sendto(legacy_request.encode(), ('239.255.255.250', 1900))
                
                # Wait longer for legacy routers
                response, addr = sock.recvfrom(1024)
                device_info = self._parse_ssdp_response(response, addr)
                if device_info and self._test_device_compatibility(device_info):
                    return True
                    
            finally:
                sock.close()
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Legacy discovery failed: {e}")
            return False
    
    def _discover_aggressive(self):
        """Aggressive discovery method as last resort"""
        try:
            self.logger.debug("Trying aggressive discovery...")
            
            # Try common router IPs directly
            router_ips = [
                self._get_default_gateway(),
                "192.168.1.1",
                "192.168.0.1", 
                "192.168.1.254",
                "10.0.0.1",
                "172.16.0.1"
            ]
            
            for router_ip in router_ips:
                if not router_ip:
                    continue
                    
                # Try common UPnP ports
                upnp_ports = [1900, 5000, 8080, 80]
                
                for port in upnp_ports:
                    try:
                        # Try to connect directly to potential UPnP service
                        potential_urls = [
                            f"http://{router_ip}:{port}/rootDesc.xml",
                            f"http://{router_ip}:{port}/description.xml",
                            f"http://{router_ip}:{port}/upnp/desc.xml",
                            f"http://{router_ip}:{port}/igd.xml"
                        ]
                        
                        for url in potential_urls:
                            try:
                                response = requests.get(url, timeout=3)
                                if response.status_code == 200:
                                    self.logger.debug(f"Found potential UPnP service at: {url}")
                                    if self._parse_router_info(url):
                                        return True
                            except:
                                continue
                                
                    except Exception as e:
                        self.logger.debug(f"Aggressive discovery error for {router_ip}:{port}: {e}")
                        continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Aggressive discovery failed: {e}")
            return False
    
    def _parse_ssdp_response(self, response, addr):
        """Parse SSDP response and extract device information"""
        try:
            response_str = response.decode('utf-8', errors='ignore')
            device_info = {'addr': addr}
            
            # Parse response headers
            for line in response_str.split('\r\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().upper()
                    value = value.strip()
                    
                    if key == 'LOCATION':
                        device_info['location'] = value
                    elif key == 'ST':
                        device_info['service_type'] = value
                    elif key == 'USN':
                        device_info['usn'] = value
                    elif key == 'SERVER':
                        device_info['server'] = value
            
            return device_info if 'location' in device_info else None
            
        except Exception as e:
            self.logger.debug(f"Error parsing SSDP response: {e}")
            return None
    
    def _test_device_compatibility(self, device_info):
        """Test if a discovered device is a compatible UPnP router"""
        try:
            location = device_info.get('location')
            if not location:
                return False
            
            self.logger.debug(f"Testing device compatibility: {location}")
            
            # Try to parse the device description
            return self._parse_router_info(location)
            
        except Exception as e:
            self.logger.debug(f"Device compatibility test failed: {e}")
            return False
    
    def _parse_router_info(self, location):
        """Enhanced router information parsing with better compatibility"""
        try:
            self.logger.debug(f"Parsing router info from: {location}")
            
            # Get device description with enhanced headers
            headers = {
                'User-Agent': 'Windows/10.0 UPnP/1.0 Plex RAR Bridge/1.0',
                'Accept': 'text/xml, application/xml, */*',
                'Connection': 'close'
            }
            
            response = requests.get(location, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            
            # Parse XML with enhanced error handling
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError as e:
                self.logger.debug(f"XML parsing error: {e}")
                return False
            
            # Enhanced service discovery with multiple approaches
            services = self._find_services_enhanced(root)
            
            if not services:
                self.logger.debug("No services found in device description")
                return False
            
            self.logger.debug(f"Found {len(services)} services")
            
            # Try to find compatible service with priority order
            service_priorities = [
                'WANIPConnection',
                'WANPPPConnection', 
                'WANCommonInterfaceConfig',
                'Layer3Forwarding'
            ]
            
            for priority_service in service_priorities:
                for service in services:
                    if self._test_service_compatibility(service, priority_service, location):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Router info parsing failed: {e}")
            return False
    
    def _find_services_enhanced(self, root):
        """Enhanced service discovery with multiple XML parsing strategies"""
        services = []
        
        # Multiple parsing strategies
        parsing_strategies = [
            # Strategy 1: Direct service search
            lambda root: root.findall('.//service'),
            
            # Strategy 2: Namespace-aware search
            lambda root: root.findall('.//{urn:schemas-upnp-org:device-1-0}service'),
            
            # Strategy 3: Device-specific search
            lambda root: root.findall('.//device/serviceList/service'),
            
            # Strategy 4: Nested device search
            lambda root: root.findall('.//deviceList/device/serviceList/service'),
            
            # Strategy 5: Alternative namespace
            lambda root: root.findall('.//{urn:schemas-upnp-org:device:1:0}service')
        ]
        
        for strategy in parsing_strategies:
            try:
                found_services = strategy(root)
                if found_services:
                    services.extend(found_services)
            except Exception as e:
                self.logger.debug(f"Service parsing strategy failed: {e}")
                continue
        
        # Remove duplicates
        unique_services = []
        seen_services = set()
        
        for service in services:
            service_id = self._get_service_id(service)
            if service_id and service_id not in seen_services:
                unique_services.append(service)
                seen_services.add(service_id)
        
        return unique_services
    
    def _get_service_id(self, service):
        """Get a unique identifier for a service"""
        try:
            service_type = self._get_service_element_text(service, 'serviceType')
            service_id = self._get_service_element_text(service, 'serviceId')
            return f"{service_type}:{service_id}" if service_type and service_id else None
        except:
            return None
    
    def _get_service_element_text(self, service, element_name):
        """Get text from service element with multiple fallback strategies"""
        try:
            # Try direct find
            elem = service.find(element_name)
            if elem is not None and elem.text:
                return elem.text.strip()
            
            # Try with namespace
            elem = service.find(f'.//{{urn:schemas-upnp-org:device-1-0}}{element_name}')
            if elem is not None and elem.text:
                return elem.text.strip()
            
            # Try recursive search
            for child in service.iter():
                if child.tag.endswith(element_name) and child.text:
                    return child.text.strip()
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error getting service element {element_name}: {e}")
            return None
    
    def _test_service_compatibility(self, service, target_service, location):
        """Test if a service is compatible for port forwarding"""
        try:
            service_type = self._get_service_element_text(service, 'serviceType')
            control_url = self._get_service_element_text(service, 'controlURL')
            
            if not service_type or not control_url:
                return False
            
            # Check if this is the service we're looking for
            if target_service not in service_type:
                return False
            
            # Build full control URL
            if control_url.startswith('/'):
                base_url = '/'.join(location.split('/')[:-1])
                self.control_url = f"{base_url}{control_url}"
            else:
                self.control_url = control_url
            
            self.service_type = service_type
            
            self.logger.info(f"Found compatible UPnP service: {service_type}")
            self.logger.info(f"Control URL: {self.control_url}")
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Service compatibility test failed: {e}")
            return False
    
    def _get_default_gateway(self):
        """Get the default gateway IP address"""
        try:
            import subprocess
            import re
            
            # Windows route command
            result = subprocess.run(['route', 'print', '0.0.0.0'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Look for default route
                for line in result.stdout.split('\n'):
                    if '0.0.0.0' in line and 'Gateway' not in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            gateway = parts[2]
                            if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', gateway):
                                return gateway
            
            # Fallback to ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Default Gateway' in line:
                        parts = line.split(':')
                        if len(parts) > 1:
                            gateway = parts[1].strip()
                            if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', gateway):
                                return gateway
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Gateway detection failed: {e}")
            return None
    
    def add_port_mapping(self, port, description="Plex RAR Bridge VFS"):
        """Enhanced port mapping with better compatibility"""
        if not self.enabled or not self.control_url:
            return False
            
        try:
            # Get local IP
            local_ip = self._get_local_ip()
            if not local_ip:
                self.logger.error("Could not determine local IP address")
                return False
            
            # Enhanced SOAP request with better compatibility
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
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
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': f'"{self.service_type}#AddPortMapping"',
                'User-Agent': 'Windows/10.0 UPnP/1.0 Plex RAR Bridge/1.0',
                'Connection': 'close'
            }
            
            response = requests.post(self.control_url, data=soap_body, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                self.forwarded_ports[port] = description
                self.logger.info(f"Successfully opened port {port} via UPnP")
                return True
            else:
                self.logger.error(f"UPnP port mapping failed: {response.status_code}")
                self.logger.debug(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to add port mapping: {e}")
            return False
    
    def remove_port_mapping(self, port):
        """Enhanced port removal with better compatibility"""
        if not self.enabled or not self.control_url:
            return False
            
        try:
            # Enhanced SOAP request for removing port mapping
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
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
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': f'"{self.service_type}#DeletePortMapping"',
                'User-Agent': 'Windows/10.0 UPnP/1.0 Plex RAR Bridge/1.0',
                'Connection': 'close'
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
            'renewal_active': self.renewal_thread is not None and self.renewal_thread.is_alive(),
            'discovered_devices': len(self.discovered_devices)
        }

# Maintain backward compatibility
class UPnPPortManager(EnhancedUPnPPortManager):
    """Backward compatibility wrapper"""
    pass

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