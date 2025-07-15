#!/usr/bin/env python3
"""
UPnP Troubleshooting Guide
Provides step-by-step instructions to enable UPnP on routers
"""

import socket
import requests
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('upnp_troubleshoot')

def get_router_ip():
    """Get the router's IP address using proper default gateway detection"""
    try:
        # Get local IP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        
        # Get actual default gateway
        router_ip = get_default_gateway()
        
        return router_ip, local_ip
    except Exception as e:
        logger.error(f"Could not determine router IP: {e}")
        return None, None

def get_default_gateway():
    """Get the default gateway IP address"""
    try:
        import subprocess
        import re
        
        # Try Windows route command
        result = subprocess.run(['route', 'print', '0.0.0.0'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            # Look for default route (0.0.0.0)
            lines = result.stdout.split('\n')
            for line in lines:
                if '0.0.0.0' in line and 'Gateway' not in line:
                    # Extract gateway IP from route table
                    parts = line.split()
                    if len(parts) >= 3:
                        gateway_ip = parts[2]
                        # Validate IP format
                        if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', gateway_ip):
                            return gateway_ip
        
        # Fallback: try ipconfig
        result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Look for "Default Gateway"
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Default Gateway' in line and ':' in line:
                    gateway_ip = line.split(':')[1].strip()
                    if gateway_ip and re.match(r'^(\d{1,3}\.){3}\d{1,3}$', gateway_ip):
                        return gateway_ip
        
        # Last resort: test common router IPs
        common_gateways = ['192.168.1.254', '192.168.1.1', '192.168.0.1', '10.0.0.1']
        for gateway in common_gateways:
            try:
                # Quick connectivity test
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((gateway, 80))
                sock.close()
                if result == 0:
                    return gateway
            except:
                continue
        
        # Default fallback
        return '192.168.1.1'
        
    except Exception as e:
        logger.error(f"Error detecting gateway: {e}")
        return '192.168.1.1'

def test_router_access(router_ip):
    """Test if we can access the router's web interface"""
    common_ports = [80, 8080, 443, 8443]
    
    for port in common_ports:
        for protocol in ['http', 'https']:
            url = f"{protocol}://{router_ip}:{port}" if port != 80 else f"{protocol}://{router_ip}"
            try:
                response = requests.get(url, timeout=3, verify=False)
                if response.status_code == 200:
                    logger.info(f"Router web interface accessible at: {url}")
                    return url
            except:
                continue
    
    logger.warning("Could not access router web interface")
    return None

def quick_upnp_test():
    """Quick UPnP test to see if anything responds"""
    logger.info("=== Quick UPnP Test ===")
    
    try:
        # Simple SSDP request
        ssdp_request = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            "ST: ssdp:all\r\n"
            "MX: 3\r\n\r\n"
        )
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        sock.sendto(ssdp_request.encode(), ('239.255.255.250', 1900))
        
        try:
            response, addr = sock.recvfrom(1024)
            logger.info(f"✅ UPnP device found at {addr}")
            return True
        except socket.timeout:
            logger.warning("❌ No UPnP devices responded")
            return False
        finally:
            sock.close()
            
    except Exception as e:
        logger.error(f"UPnP test failed: {e}")
        return False

def print_router_instructions():
    """Print common router UPnP enabling instructions"""
    print("\n" + "="*60)
    print("UPnP TROUBLESHOOTING GUIDE")
    print("="*60)
    
    print("\n1. CHECK ROUTER SETTINGS:")
    print("   - Open your router's web interface")
    print("   - Look for 'UPnP' or 'Universal Plug and Play' settings")
    print("   - Common locations:")
    print("     • Advanced → UPnP")
    print("     • Network → UPnP")
    print("     • Firewall → UPnP")
    print("     • Services → UPnP")
    
    print("\n2. COMMON ROUTER BRANDS:")
    print("   NETGEAR:")
    print("     • Login → Advanced → Dynamic DNS/UPnP → Enable UPnP")
    print("   ASUS:")
    print("     • Login → Adaptive QoS → Traditional QoS → Enable UPnP")
    print("   LINKSYS:")
    print("     • Login → Smart Wi-Fi Tools → Media Prioritization → Enable UPnP")
    print("   TP-LINK:")
    print("     • Login → Advanced → NAT Forwarding → UPnP → Enable")
    print("   D-LINK:")
    print("     • Login → Tools → UPnP → Enable UPnP")
    
    print("\n3. WINDOWS FIREWALL:")
    print("   - Open Windows Defender Firewall")
    print("   - Click 'Allow an app through firewall'")
    print("   - Check 'UPnP Device Host' and 'UPnP Device Discovery'")
    print("   - Enable for both Private and Public networks")
    
    print("\n4. NETWORK DISCOVERY:")
    print("   - Open Control Panel → Network and Internet → Network Center")
    print("   - Click 'Change advanced sharing settings'")
    print("   - Turn on 'Network discovery' for current profile")
    
    print("\n5. ROUTER REBOOT:")
    print("   - After enabling UPnP, reboot your router")
    print("   - Wait 2-3 minutes for it to fully restart")
    print("   - Test UPnP again")

def main():
    """Main troubleshooting function"""
    print("UPnP Troubleshooting Tool")
    print("========================")
    
    # Test network connectivity
    router_ip, local_ip = get_router_ip()
    if router_ip and local_ip:
        print(f"Your IP: {local_ip}")
        print(f"Router IP: {router_ip}")
        
        # Test router access
        router_url = test_router_access(router_ip)
        if router_url:
            print(f"Router web interface: {router_url}")
        else:
            print("Could not access router web interface")
            print("Common router IPs to try: 192.168.1.1, 192.168.0.1, 10.0.0.1")
    
    # Quick UPnP test
    upnp_working = quick_upnp_test()
    
    if not upnp_working:
        print_router_instructions()
        
        print("\n" + "="*60)
        print("TESTING STEPS:")
        print("="*60)
        print("1. Enable UPnP on your router (see instructions above)")
        print("2. Reboot your router")
        print("3. Run this script again to test")
        print("4. If still not working, try manual port forwarding")
        print("\nMANUAL PORT FORWARDING:")
        print("- Port: 8765 (or your configured port)")
        print("- Protocol: TCP")
        print("- Internal IP: " + (local_ip or "YOUR_COMPUTER_IP"))
        print("- External Port: 8765")
        print("- Internal Port: 8765")
    else:
        print("✅ UPnP is working! The issue may be elsewhere.")

if __name__ == "__main__":
    main() 