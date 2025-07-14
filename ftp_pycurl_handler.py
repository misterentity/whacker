#!/usr/bin/env python3
"""
Professional FTP Handler using pycurl
Supports mixed SSL modes (SSL control + clear data) like FlashFXP
"""

import pycurl
import io
import json
import re
from pathlib import Path
from urllib.parse import quote

class ProfessionalFTPClient:
    """Professional FTP client using pycurl for better SSL support"""
    
    def __init__(self):
        self.connected = False
        self.host = ""
        self.port = 21
        self.username = ""
        self.password = ""
        self.ssl_mode = "Explicit"
        self.current_dir = "/"
        
    def connect(self, host, port, username, password, ssl_mode="Explicit"):
        """Connect using professional SSL methods like FlashFXP"""
        try:
            self.host = host
            self.port = port
            self.username = username
            self.password = password
            self.ssl_mode = ssl_mode
            
            print(f"Professional FTP Connection:")
            print(f"  Host: {host}:{port}")
            print(f"  Username: {username}")
            print(f"  SSL Mode: {ssl_mode}")
            
            # Test connection with a simple command
            success = self._test_connection()
            
            if success:
                self.connected = True
                print("  ✅ Professional FTP connection successful!")
                return True
            else:
                print("  ❌ Professional FTP connection failed")
                return False
                
        except Exception as e:
            print(f"  ❌ Connection error: {e}")
            return False
    
    def _test_connection(self):
        """Test connection with professional SSL settings"""
        try:
            # Test with a simple PWD command
            result = self._execute_ftp_command("PWD")
            if result and not result.startswith("Error"):
                self.current_dir = self._extract_pwd_from_response(result)
                return True
            return False
        except Exception as e:
            print(f"    Connection test failed: {e}")
            return False
    
    def _execute_ftp_command(self, command, expect_data=False):
        """Execute FTP command with professional SSL handling"""
        try:
            curl = pycurl.Curl()
            
            # Basic connection settings
            base_url = f"ftp://{self.host}:{self.port}/"
            curl.setopt(curl.URL, base_url)
            curl.setopt(curl.USERPWD, f"{self.username}:{self.password}")
            
            # Professional SSL settings (like FlashFXP)
            if self.ssl_mode == "Explicit":
                # SSL for control connection, clear for data (FlashFXP style)
                curl.setopt(curl.USE_SSL, pycurl.USESSL_CONTROL)
                print(f"    Using SSL control + clear data (FlashFXP style)")
            elif self.ssl_mode == "Implicit":
                # Full SSL
                curl.setopt(curl.USE_SSL, pycurl.USESSL_ALL)
                print(f"    Using full SSL (implicit)")
            else:
                # Plain FTP
                curl.setopt(curl.USE_SSL, pycurl.USESSL_NONE)
                print(f"    Using plain FTP")
            
            # SSL verification settings (like professional clients)
            curl.setopt(curl.SSL_VERIFYPEER, 0)
            curl.setopt(curl.SSL_VERIFYHOST, 0)
            
            # Professional timeout settings
            curl.setopt(curl.CONNECTTIMEOUT, 30)
            curl.setopt(curl.TIMEOUT, 60)
            
            # Use passive mode (required for most firewalls)
            curl.setopt(curl.FTP_USE_PASV, 1)
            
            # Custom FTP command
            if command:
                curl.setopt(curl.CUSTOMREQUEST, command)
            
            # Capture response
            response_buffer = io.BytesIO()
            curl.setopt(curl.WRITEDATA, response_buffer)
            
            # Execute
            curl.perform()
            
            # Get results
            response_code = curl.getinfo(curl.RESPONSE_CODE)
            response_text = response_buffer.getvalue().decode('utf-8', errors='ignore')
            
            curl.close()
            
            print(f"    Command: {command} -> Response Code: {response_code}")
            
            if response_code in [200, 213, 250, 257]:  # Success codes
                return response_text
            else:
                return f"Error {response_code}: {response_text}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def list_directory(self, path=""):
        """List directory contents using professional approach"""
        try:
            if not self.connected:
                return None, "Not connected"
            
            print(f"  Listing directory with professional SSL handling...")
            
            # Build URL for directory listing
            if path:
                list_url = f"ftp://{self.host}:{self.port}/{quote(path)}/"
            else:
                list_url = f"ftp://{self.host}:{self.port}/"
            
            curl = pycurl.Curl()
            
            # Connection settings
            curl.setopt(curl.URL, list_url)
            curl.setopt(curl.USERPWD, f"{self.username}:{self.password}")
            
            # Professional SSL settings (FlashFXP style)
            if self.ssl_mode == "Explicit":
                curl.setopt(curl.USE_SSL, pycurl.USESSL_CONTROL)
                print(f"    Directory listing with SSL control + clear data")
            elif self.ssl_mode == "Implicit":
                curl.setopt(curl.USE_SSL, pycurl.USESSL_ALL)
                print(f"    Directory listing with full SSL")
            else:
                curl.setopt(curl.USE_SSL, pycurl.USESSL_NONE)
                print(f"    Directory listing with plain FTP")
            
            # SSL verification settings
            curl.setopt(curl.SSL_VERIFYPEER, 0)
            curl.setopt(curl.SSL_VERIFYHOST, 0)
            
            # Professional settings
            curl.setopt(curl.CONNECTTIMEOUT, 30)
            curl.setopt(curl.TIMEOUT, 60)
            curl.setopt(curl.FTP_USE_PASV, 1)
            
            # Request directory listing
            curl.setopt(curl.FTPLISTONLY, 0)  # Detailed listing
            
            # Capture response
            response_buffer = io.BytesIO()
            curl.setopt(curl.WRITEDATA, response_buffer)
            
            # Execute
            curl.perform()
            
            # Get results
            response_code = curl.getinfo(curl.RESPONSE_CODE)
            listing_text = response_buffer.getvalue().decode('utf-8', errors='ignore')
            
            curl.close()
            
            print(f"    Directory listing response code: {response_code}")
            
            if response_code == 226:  # Transfer complete
                files = self._parse_directory_listing(listing_text)
                print(f"    ✅ Directory listing successful - {len(files)} entries")
                return files, None
            else:
                error_msg = f"Directory listing failed: {response_code}"
                print(f"    ❌ {error_msg}")
                return None, error_msg
                
        except Exception as e:
            error_msg = f"Directory listing error: {str(e)}"
            print(f"    ❌ {error_msg}")
            return None, error_msg
    
    def _parse_directory_listing(self, listing_text):
        """Parse FTP directory listing into structured format"""
        files = []
        
        for line in listing_text.strip().split('\n'):
            if not line.strip():
                continue
                
            try:
                # Parse standard FTP listing format
                parts = line.split()
                if len(parts) >= 8:
                    permissions = parts[0]
                    size = parts[4] if parts[4].isdigit() else "0"
                    date_str = " ".join(parts[5:8])
                    name = " ".join(parts[8:])
                    
                    # Skip . and .. entries
                    if name in ['.', '..']:
                        continue
                    
                    # Determine file type
                    if permissions.startswith('d'):
                        file_type = "directory"
                        icon = "📁"
                    else:
                        file_type = "file"
                        icon = "📄"
                    
                    files.append({
                        'name': name,
                        'type': file_type,
                        'icon': icon,
                        'size': int(size) if size.isdigit() else 0,
                        'size_str': self._format_file_size(int(size)) if size.isdigit() else size,
                        'date': date_str,
                        'permissions': permissions
                    })
                    
            except Exception as e:
                print(f"      Warning: Failed to parse line: {line} - {e}")
                continue
        
        return files
    
    def _format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def _extract_pwd_from_response(self, response):
        """Extract current directory from PWD response"""
        try:
            # PWD response format: 257 "/path/to/dir" is current directory
            match = re.search(r'\"([^\"]+)\"', response)
            if match:
                return match.group(1)
            return "/"
        except:
            return "/"
    
    def get_current_directory(self):
        """Get current directory"""
        if not self.connected:
            return None
        
        result = self._execute_ftp_command("PWD")
        if result and not result.startswith("Error"):
            self.current_dir = self._extract_pwd_from_response(result)
            return self.current_dir
        return None
    
    def change_directory(self, path):
        """Change to specified directory"""
        if not self.connected:
            return False
        
        result = self._execute_ftp_command(f"CWD {path}")
        if result and not result.startswith("Error"):
            self.current_dir = path
            return True
        return False
    
    def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        print("  Professional FTP client disconnected")

def test_professional_ftp():
    """Test the professional FTP client"""
    
    # Load connection settings
    config_file = Path("ftp_config.json")
    if not config_file.exists():
        print("❌ ftp_config.json not found")
        return
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Find connection to use
    conn = None
    last_used = config.get('last_used', '')
    for connection in config['connections']:
        if connection.get('name') == last_used:
            conn = connection
            break
    
    if not conn:
        print("❌ No valid connection found")
        return
    
    host = conn.get('host', '')
    port = conn.get('port', 21)
    username = conn.get('username', '')
    password = conn.get('password', '')
    ssl_mode = conn.get('ssl_mode', 'Explicit')
    
    print("=" * 80)
    print("PROFESSIONAL FTP CLIENT TEST (pycurl)")
    print("=" * 80)
    print(f"Testing FlashFXP-style connection to glftpd server")
    print("-" * 80)
    
    # Test the professional client
    client = ProfessionalFTPClient()
    
    if client.connect(host, port, username, password, ssl_mode):
        print(f"\n✅ Connection successful!")
        
        # Test directory listing
        print(f"\nTesting directory listing...")
        files, error = client.list_directory()
        
        if files:
            print(f"✅ Directory listing successful!")
            print(f"Found {len(files)} entries:")
            
            for i, file_info in enumerate(files[:5]):  # Show first 5
                print(f"  {file_info['icon']} {file_info['name']} ({file_info['size_str']})")
            
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more entries")
                
        else:
            print(f"❌ Directory listing failed: {error}")
        
        # Test current directory
        current_dir = client.get_current_directory()
        print(f"\nCurrent directory: {current_dir}")
        
        client.disconnect()
        
    else:
        print(f"❌ Connection failed")
    
    print("\n" + "=" * 80)
    print("PROFESSIONAL FTP TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_professional_ftp()
    input("\nPress Enter to exit...") 