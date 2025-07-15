# UPnP Integration for Python VFS

## Overview

The Plex RAR Bridge now includes UPnP (Universal Plug and Play) integration to automatically configure port forwarding for the Python VFS HTTP server. This feature helps bypass firewall issues and enables remote access to streamed content without manual router configuration.

## Features

- **Automatic Router Discovery**: Discovers UPnP-enabled routers on the network
- **Port Forwarding Management**: Automatically opens and closes ports as needed
- **Automatic Port Renewal**: Maintains port leases automatically
- **Configurable Settings**: Timeout, retry count, and lease duration settings
- **Fallback Handling**: Graceful fallback for non-UPnP environments
- **Real-time Status**: Monitor UPnP status through the GUI

## How It Works

### 1. Router Discovery
- Uses SSDP (Simple Service Discovery Protocol) to find UPnP-enabled routers
- Searches for Internet Gateway Devices (IGD) on the network
- Parses router capabilities and control URLs

### 2. Port Forwarding
- Automatically requests port forwarding for the Python VFS HTTP server
- Maps external ports to internal server ports
- Handles both WANIPConnection and WANPPPConnection services

### 3. Port Renewal
- Maintains port leases through automatic renewal
- Prevents port mappings from expiring
- Handles network interruptions gracefully

### 4. Cleanup
- Automatically removes port mappings when service stops
- Prevents orphaned port forwarding rules
- Graceful shutdown handling

## Configuration

### Basic Configuration (config.yaml)

```yaml
# UPnP configuration for automatic port forwarding
upnp:
  enabled: true
  timeout: 10
  retry_count: 3
  lease_duration: 3600  # 1 hour in seconds
```

### Enhanced Configuration (config-enhanced.yaml)

```yaml
# UPnP Configuration for automatic port forwarding
upnp:
  enabled: true
  timeout: 10
  retry_count: 3
  lease_duration: 3600  # 1 hour in seconds
  discovery_timeout: 5
  renewal_interval: 1800  # 30 minutes
```

### Configuration Options

| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| `enabled` | Enable/disable UPnP | `true` | `true/false` |
| `timeout` | Discovery timeout (seconds) | `10` | `5-30` |
| `retry_count` | Number of retry attempts | `3` | `1-10` |
| `lease_duration` | Port lease duration (seconds) | `3600` | `300-86400` |
| `discovery_timeout` | Router discovery timeout | `5` | `1-15` |
| `renewal_interval` | Port renewal interval | `1800` | `300-3600` |

## GUI Integration

### Enhanced Setup Panel

The Enhanced Setup Panel includes a dedicated UPnP configuration section:

#### UPnP Settings
- **Enable UPnP**: Toggle UPnP functionality
- **Discovery Timeout**: How long to wait for router discovery
- **Retry Count**: Number of retry attempts for failed operations
- **Port Lease Duration**: How long port mappings remain active

#### UPnP Testing
- **Test UPnP**: Test current UPnP configuration
- **Discover Router**: Find and display router information
- **Real-time Status**: Visual feedback on UPnP status

#### Status Indicators
- ✅ **UPnP: Router discovered and ready** - UPnP is working
- ❌ **UPnP: No compatible router found** - Router doesn't support UPnP
- ❌ **UPnP: Error** - Configuration or network issue

## Usage

### Automatic Operation

When Python VFS processing mode is enabled, UPnP works automatically:

1. **Service Start**: UPnP discovers router and requests port forwarding
2. **Active Monitoring**: Port mappings are renewed automatically
3. **Service Stop**: Port mappings are cleaned up automatically

### Manual Testing

Use the Enhanced Setup Panel to test UPnP:

1. Open GUI and go to "Enhanced Setup" tab
2. Scroll to "UPnP Port Forwarding" section
3. Click "Test UPnP" to verify functionality
4. Click "Discover Router" to see router details

## Troubleshooting

### Common Issues

#### Router Not Found
**Symptoms**: "No compatible router found" error
**Causes**:
- Router doesn't support UPnP
- UPnP is disabled in router settings
- Network firewall blocking SSDP

**Solutions**:
1. Check router UPnP settings (enable if disabled)
2. Verify network connectivity
3. Try increasing discovery timeout
4. Check firewall settings

#### Port Mapping Failed
**Symptoms**: "Port mapping failed" error
**Causes**:
- Port already in use
- Router security restrictions
- Network configuration issues

**Solutions**:
1. Check if port is available
2. Try different port range
3. Verify router security settings
4. Restart router and try again

#### Authentication Errors
**Symptoms**: HTTP 401/403 errors
**Causes**:
- Router authentication requirements
- Service type mismatch
- Incorrect control URL

**Solutions**:
1. Check router authentication settings
2. Verify service type detection
3. Try router restart
4. Manual port forwarding as fallback

### Network Requirements

#### Router Requirements
- UPnP/IGD support enabled
- WANIPConnection or WANPPPConnection service
- SSDP multicast support
- No strict firewall blocking UPnP

#### Network Requirements
- Multicast support (239.255.255.250:1900)
- HTTP access to router control URL
- No network isolation between devices

### Debugging

#### Enable Debug Logging

```yaml
logging:
  level: DEBUG
  file: "logs/plex_rar_bridge.log"
```

#### Check UPnP Status

```python
# Get UPnP status through Python VFS
vfs = RarVirtualFileSystem(config, logger)
status = vfs.get_upnp_status()
print(f"UPnP Status: {status}")
```

#### Manual UPnP Testing

```python
from upnp_port_manager import UPnPPortManager
import logging

# Create logger
logger = logging.getLogger('upnp_test')
logger.setLevel(logging.DEBUG)

# Create console handler
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

# Test UPnP
config = {'upnp': {'enabled': True, 'timeout': 10}}
upnp = UPnPPortManager(config, logger)

# Discover router
if upnp.discover_router():
    print("Router discovered successfully")
    print(f"Control URL: {upnp.control_url}")
    print(f"Service Type: {upnp.service_type}")
    
    # Test port mapping
    if upnp.add_port_mapping(8765, "Test Port"):
        print("Port mapping successful")
        upnp.remove_port_mapping(8765)
    else:
        print("Port mapping failed")
else:
    print("No UPnP router found")
```

## Security Considerations

### Port Forwarding Security
- UPnP automatically opens ports to the internet
- Only opens ports when service is running
- Automatically closes ports when service stops
- Uses descriptive port mapping names

### Network Security
- UPnP uses local network discovery only
- No external network access required
- Router authentication respected
- Firewall rules not bypassed

### Best Practices
1. **Enable UPnP only when needed** for remote access
2. **Monitor active port mappings** through router interface
3. **Use secure network configurations** with proper firewall rules
4. **Regularly update router firmware** for security patches
5. **Consider manual port forwarding** for high-security environments

## Alternatives

### Manual Port Forwarding
If UPnP is not available or desired:

1. **Access router configuration** (usually http://192.168.1.1)
2. **Find port forwarding section** (may be called "Virtual Servers")
3. **Add port forwarding rule**:
   - External Port: 8765 (or configured port)
   - Internal IP: [Server IP Address]
   - Internal Port: 8765 (same as external)
   - Protocol: TCP
   - Description: Plex RAR Bridge VFS

### Firewall Configuration
Configure Windows Firewall:

```powershell
# Allow inbound traffic for Python VFS
New-NetFirewallRule -DisplayName "Plex RAR Bridge VFS" -Direction Inbound -Protocol TCP -LocalPort 8765-8865 -Action Allow
```

## Integration with Other Features

### Python VFS
- UPnP is automatically enabled with Python VFS mode
- Port forwarding configured for HTTP server port
- Automatic cleanup when switching modes

### Processing Mode Selection
- UPnP only active when Python VFS is selected
- Disabled for extraction and rar2fs modes
- Per-directory UPnP configuration possible

### Service Management
- UPnP integrated with service startup/shutdown
- Automatic port management during service lifecycle
- Status monitoring through GUI

## Performance Impact

### Minimal Overhead
- UPnP operations run in background threads
- No impact on file processing performance
- Automatic port renewal uses minimal resources

### Network Traffic
- SSDP discovery uses minimal bandwidth
- Port renewal requests are small HTTP calls
- No continuous network activity required

## Conclusion

UPnP integration provides seamless automatic port forwarding for the Python VFS HTTP server, eliminating the need for manual router configuration in most home and small office environments. While not required for local network access, it significantly improves the user experience for remote access scenarios.

The feature is designed to be:
- **Automatic**: Works without user intervention
- **Safe**: Proper cleanup and security considerations
- **Configurable**: Adjustable for different network environments
- **Fallback-friendly**: Graceful degradation when UPnP is unavailable

For environments where UPnP is not available or desired, manual port forwarding remains a viable alternative. 