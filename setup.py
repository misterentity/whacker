"""
setup.py - Setup script for Plex RAR Bridge

This script helps with initial setup:
1. Creates directory structure
2. Installs Python dependencies
3. Guides through configuration
4. Downloads and installs UnRAR if needed
5. Tests the installation
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
import tempfile
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import yaml
import requests
import time

def check_admin():
    """Check if script is running with administrator privileges"""
    try:
        return os.getuid() == 0
    except AttributeError:
        # Windows
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def discover_plex_server():
    """Attempt to discover Plex server host and port"""
    print("Searching for Plex server...")
    
    # List of server discovery methods
    server_sources = [
        ("Plex Registry", lambda: get_server_from_registry()),
        ("Plex Preferences", lambda: get_server_from_preferences()),
        ("Process Detection", lambda: get_server_from_process()),
        ("Network Scan", lambda: get_server_from_network()),
    ]
    
    for source_name, server_func in server_sources:
        try:
            server_info = server_func()
            if server_info:
                print(f"  [OK] Found server from {source_name}: {server_info}")
                return server_info
        except Exception as e:
            print(f"  [WARN] {source_name} failed: {e}")
    
    print("  [WARN] No server found automatically")
    return "http://127.0.0.1:32400"

def discover_plex_token():
    """Attempt to discover Plex token from various sources"""
    print("Searching for Plex token...")
    
    # List of common Plex token locations and methods
    token_sources = [
        ("Plex Registry", lambda: get_token_from_registry()),
        ("Plex Server Preferences", lambda: get_token_from_server_preferences()),
        ("Plex App Data", lambda: get_token_from_app_data()),
        ("Browser Cookies", lambda: get_token_from_cookies()),
        ("Plex Client Preferences", lambda: get_token_from_client_preferences()),
        ("Plex Database", lambda: get_token_from_database()),
    ]
    
    for source_name, token_func in token_sources:
        try:
            token = token_func()
            if token and len(token) > 10:  # Basic validation
                print(f"  [OK] Found token from {source_name}")
                return token
        except Exception as e:
            print(f"  [WARN] {source_name} failed: {e}")
    
    print("  [WARN] No token found automatically")
    return None

def get_server_from_registry():
    """Get Plex server info from Windows registry"""
    try:
        import winreg
        
        # Check for Plex Media Server installation
        server_keys = [
            r"SOFTWARE\Plex, Inc.\Plex Media Server",
            r"SOFTWARE\WOW6432Node\Plex, Inc.\Plex Media Server",
        ]
        
        for hive in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            for key_path in server_keys:
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        # Try to get port
                        try:
                            port, _ = winreg.QueryValueEx(key, "Port")
                            return f"http://127.0.0.1:{port}"
                        except FileNotFoundError:
                            pass
                        
                        # Try to get install path and check config
                        try:
                            install_path, _ = winreg.QueryValueEx(key, "InstallFolder")
                            if install_path:
                                return "http://127.0.0.1:32400"  # Default port
                        except FileNotFoundError:
                            pass
                except FileNotFoundError:
                    continue
    except ImportError:
        pass
    return None

def get_server_from_preferences():
    """Get Plex server info from preferences"""
    try:
        # Common Plex server preference locations
        plex_data_paths = [
            "C:/ProgramData/Plex Media Server/Preferences.xml",
            os.path.expanduser("~/Library/Application Support/Plex Media Server/Preferences.xml"),
            os.path.expanduser("~/.config/plex/Preferences.xml"),
        ]
        
        for prefs_path in plex_data_paths:
            if os.path.exists(prefs_path):
                try:
                    tree = ET.parse(prefs_path)
                    root = tree.getroot()
                    
                    # Check for port settings
                    port = root.get('Port') or root.get('ManualPortMappingPort') or "32400"
                    
                    # Check for network settings
                    host = "127.0.0.1"
                    if root.get('AcceptedEULA') == '1':  # Server is configured
                        return f"http://{host}:{port}"
                        
                except Exception:
                    continue
    except Exception:
        pass
    return None

def get_server_from_process():
    """Get Plex server info from running processes"""
    try:
        import psutil
        
        # Look for Plex Media Server process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'plex' in proc.info['name'].lower():
                    if 'media server' in ' '.join(proc.info['cmdline'] or []).lower():
                        # Found Plex Media Server, try to get port from command line
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if '--port' in cmdline:
                            parts = cmdline.split('--port')
                            if len(parts) > 1:
                                port = parts[1].strip().split()[0]
                                return f"http://127.0.0.1:{port}"
                        
                        # Default port if found but no port specified
                        return "http://127.0.0.1:32400"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        pass
    return None

def get_server_from_network():
    """Get Plex server info from network scan"""
    try:
        import socket
        
        # Try common Plex ports
        common_ports = [32400, 32401, 32402, 32403, 32404, 32405]
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result == 0:
                    # Port is open, try to verify it's Plex
                    try:
                        test_url = f"http://127.0.0.1:{port}/identity"
                        response = requests.get(test_url, timeout=2)
                        if response.status_code == 200 and 'plex' in response.text.lower():
                            return f"http://127.0.0.1:{port}"
                    except:
                        pass
            except Exception:
                continue
    except Exception:
        pass
    return None

def get_token_from_registry():
    """Get Plex token from Windows registry"""
    try:
        import winreg
        
        # Extended list of registry locations
        registry_locations = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Plex, Inc.\Plex Media Server"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Plex, Inc.\Plex Media Server"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Plex, Inc.\Plex"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Plex, Inc.\Plex"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Plex, Inc.\Plex Media Server"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Plex, Inc.\Plex Media Server"),
        ]
        
        token_keys = ['PlexToken', 'PlexOnlineToken', 'Token', 'AuthToken']
        
        for hive, key_path in registry_locations:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    for token_key in token_keys:
                        try:
                            token, _ = winreg.QueryValueEx(key, token_key)
                            if token and len(token) > 10:
                                return token
                        except FileNotFoundError:
                            continue
            except FileNotFoundError:
                continue
    except ImportError:
        pass
    return None

def get_token_from_server_preferences():
    """Get Plex token from server preferences"""
    try:
        # Server preference locations
        server_prefs_paths = [
            "C:/ProgramData/Plex Media Server/Preferences.xml",
            os.path.expanduser("~/Library/Application Support/Plex Media Server/Preferences.xml"),
            os.path.expanduser("~/.config/plex/Preferences.xml"),
            os.path.expanduser("~/AppData/Local/Plex Media Server/Preferences.xml"),
        ]
        
        for prefs_path in server_prefs_paths:
            if os.path.exists(prefs_path):
                try:
                    tree = ET.parse(prefs_path)
                    root = tree.getroot()
                    
                    # Look for various token attributes
                    token_attrs = ['PlexOnlineToken', 'PlexToken', 'Token', 'AuthToken']
                    for attr in token_attrs:
                        token = root.get(attr)
                        if token and len(token) > 10:
                            return token
                            
                except Exception:
                    continue
    except Exception:
        pass
    return None

def get_token_from_app_data():
    """Get Plex token from Plex app data directory"""
    try:
        # Windows Plex app data locations
        app_data_paths = [
            os.path.expanduser("~/AppData/Local/Plex Media Server/Plug-in Support/Preferences.xml"),
            os.path.expanduser("~/AppData/Roaming/Plex Media Server/Plug-in Support/Preferences.xml"),
            "C:/ProgramData/Plex Media Server/Plug-in Support/Preferences.xml",
            os.path.expanduser("~/AppData/Local/Plex/Plex Media Server/Preferences.xml"),
        ]
        
        for prefs_path in app_data_paths:
            if os.path.exists(prefs_path):
                try:
                    tree = ET.parse(prefs_path)
                    root = tree.getroot()
                    
                    # Look for PlexOnlineToken in settings
                    for setting in root.findall('.//Setting'):
                        if setting.get('id') in ['PlexOnlineToken', 'PlexToken', 'Token']:
                            token = setting.get('value')
                            if token and len(token) > 10:
                                return token
                    
                    # Also check root attributes
                    for attr in ['PlexOnlineToken', 'PlexToken', 'Token']:
                        token = root.get(attr)
                        if token and len(token) > 10:
                            return token
                            
                except Exception:
                    continue
    except Exception:
        pass
    return None

def get_token_from_cookies():
    """Get Plex token from browser cookies (Chrome/Edge/Firefox)"""
    try:
        import sqlite3
        
        # Extended browser cookie database locations
        cookie_paths = [
            os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default/Cookies"),
            os.path.expanduser("~/AppData/Local/Microsoft/Edge/User Data/Default/Cookies"),
            os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default/Network/Cookies"),
            os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles/*/cookies.sqlite"),
        ]
        
        # Add Chrome profiles
        chrome_base = os.path.expanduser("~/AppData/Local/Google/Chrome/User Data")
        if os.path.exists(chrome_base):
            for profile in os.listdir(chrome_base):
                if profile.startswith("Profile"):
                    cookie_paths.append(os.path.join(chrome_base, profile, "Cookies"))
        
        for cookie_path in cookie_paths:
            # Handle Firefox wildcard
            if '*' in cookie_path:
                firefox_base = os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles")
                if os.path.exists(firefox_base):
                    for profile in os.listdir(firefox_base):
                        actual_path = os.path.join(firefox_base, profile, "cookies.sqlite")
                        if os.path.exists(actual_path):
                            cookie_paths.append(actual_path)
                continue
            
            if os.path.exists(cookie_path):
                try:
                    # Make a copy since the database might be locked
                    temp_cookie_path = tempfile.mktemp(suffix='.db')
                    shutil.copy2(cookie_path, temp_cookie_path)
                    
                    conn = sqlite3.connect(temp_cookie_path)
                    
                    # Try different cookie queries
                    queries = [
                        "SELECT value FROM cookies WHERE host_key LIKE '%plex%' AND name = 'X-Plex-Token'",
                        "SELECT value FROM cookies WHERE host_key LIKE '%.plex.tv%' AND name = 'X-Plex-Token'",
                        "SELECT value FROM cookies WHERE name = 'X-Plex-Token'",
                        "SELECT value FROM cookies WHERE host_key LIKE '%plex%' AND name LIKE '%token%'",
                    ]
                    
                    for query in queries:
                        try:
                            cursor = conn.execute(query)
                            result = cursor.fetchone()
                            if result and result[0] and len(result[0]) > 10:
                                conn.close()
                                os.unlink(temp_cookie_path)
                                return result[0]
                        except sqlite3.OperationalError:
                            continue
                    
                    conn.close()
                    os.unlink(temp_cookie_path)
                    
                except Exception:
                    continue
    except Exception:
        pass
    return None

def get_token_from_client_preferences():
    """Get token from Plex client preferences"""
    try:
        # Client preference locations
        client_prefs_paths = [
            os.path.expanduser("~/AppData/Roaming/Plex/Plex Media Server/Preferences.xml"),
            os.path.expanduser("~/AppData/Local/Plex Inc/Plex Media Server/Preferences.xml"),
            os.path.expanduser("~/AppData/Local/PlexInc/Plex Media Server/Preferences.xml"),
            os.path.expanduser("~/Library/Preferences/com.plexapp.plexmediaserver.plist"),
        ]
        
        for prefs_path in client_prefs_paths:
            if os.path.exists(prefs_path):
                try:
                    if prefs_path.endswith('.xml'):
                        tree = ET.parse(prefs_path)
                        root = tree.getroot()
                        
                        # Look for token attributes
                        for attr in ['PlexOnlineToken', 'PlexToken', 'Token']:
                            token = root.get(attr)
                            if token and len(token) > 10:
                                return token
                    
                except Exception:
                    continue
    except Exception:
        pass
    return None

def get_token_from_database():
    """Get token from Plex database files"""
    try:
        import sqlite3
        
        # Database locations
        db_paths = [
            "C:/ProgramData/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db",
            os.path.expanduser("~/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"),
            os.path.expanduser("~/.config/plex/Plug-in Support/Databases/com.plexapp.plugins.library.db"),
        ]
        
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    # Make a copy since the database might be locked
                    temp_db_path = tempfile.mktemp(suffix='.db')
                    shutil.copy2(db_path, temp_db_path)
                    
                    conn = sqlite3.connect(temp_db_path)
                    
                    # Try to find token in various tables
                    queries = [
                        "SELECT value FROM preferences WHERE key LIKE '%token%'",
                        "SELECT value FROM preferences WHERE key = 'PlexOnlineToken'",
                        "SELECT data FROM accounts WHERE data LIKE '%token%'",
                    ]
                    
                    for query in queries:
                        try:
                            cursor = conn.execute(query)
                            results = cursor.fetchall()
                            for result in results:
                                if result and result[0] and len(str(result[0])) > 10:
                                    token = str(result[0])
                                    # Extract token from JSON if needed
                                    if '"' in token:
                                        import json
                                        try:
                                            data = json.loads(token)
                                            if isinstance(data, dict) and 'token' in data:
                                                token = data['token']
                                        except:
                                            pass
                                    
                                    if len(token) > 10:
                                        conn.close()
                                        os.unlink(temp_db_path)
                                        return token
                        except sqlite3.OperationalError:
                            continue
                    
                    conn.close()
                    os.unlink(temp_db_path)
                    
                except Exception:
                    continue
    except Exception:
        pass
    return None



def get_plex_libraries(host, token):
    """Get list of Plex libraries"""
    try:
        url = f"{host.rstrip('/')}/library/sections"
        params = {'X-Plex-Token': token}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        libraries = []
        
        for directory in root.findall('.//Directory'):
            library_info = {
                'key': directory.get('key'),
                'title': directory.get('title'),
                'type': directory.get('type'),
                'agent': directory.get('agent'),
                'language': directory.get('language'),
                'refreshing': directory.get('refreshing', 'false') == 'true'
            }
            libraries.append(library_info)
        
        return libraries
        
    except Exception as e:
        print(f"Error getting libraries: {e}")
        return []

def select_library(libraries):
    """Interactive library selection"""
    if not libraries:
        print("No libraries found!")
        return None
    
    print("\nAvailable Plex Libraries:")
    print("=" * 50)
    
    # Group libraries by type
    movie_libs = [lib for lib in libraries if lib['type'] == 'movie']
    show_libs = [lib for lib in libraries if lib['type'] == 'show']
    other_libs = [lib for lib in libraries if lib['type'] not in ['movie', 'show']]
    
    all_libs = []
    
    if movie_libs:
        print("\n📽️  MOVIE LIBRARIES:")
        for lib in movie_libs:
            print(f"  [{len(all_libs) + 1}] {lib['title']} (Key: {lib['key']})")
            all_libs.append(lib)
    
    if show_libs:
        print("\n📺 TV SHOW LIBRARIES:")
        for lib in show_libs:
            print(f"  [{len(all_libs) + 1}] {lib['title']} (Key: {lib['key']})")
            all_libs.append(lib)
    
    if other_libs:
        print(f"\n📚 OTHER LIBRARIES:")
        for lib in other_libs:
            print(f"  [{len(all_libs) + 1}] {lib['title']} - {lib['type']} (Key: {lib['key']})")
            all_libs.append(lib)
    
    print(f"\n  [0] Enter library key manually")
    print("=" * 50)
    
    while True:
        try:
            choice = input(f"\nSelect library (1-{len(all_libs)}, or 0 for manual): ").strip()
            
            if choice == '0':
                manual_key = input("Enter library key: ").strip()
                try:
                    return int(manual_key)
                except ValueError:
                    print("Please enter a valid number")
                    continue
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(all_libs):
                selected_lib = all_libs[choice_idx]
                print(f"\nSelected: {selected_lib['title']} (Key: {selected_lib['key']})")
                return int(selected_lib['key'])
            else:
                print(f"Please enter a number between 1 and {len(all_libs)}")
                
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nCancelled by user")
            return None

def test_plex_connection(host, token):
    """Test connection to Plex server"""
    try:
        url = f"{host.rstrip('/')}/library/sections"
        params = {'X-Plex-Token': token}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

def install_python_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("[SUCCESS] Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("Creating directory structure...")
    
    base_dir = Path.cwd()
    directories = [
        'logs',
        'data',
        'rar_watch',
        'work',
        'failed',
        'archive'
    ]
    
    created = []
    for dir_name in directories:
        dir_path = base_dir / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            created.append(dir_name)
            print(f"  [OK] Created: {dir_name}")
        else:
            print(f"  [OK] Exists: {dir_name}")
    
    if created:
        print(f"[SUCCESS] Created {len(created)} directories")
    else:
        print("[SUCCESS] All directories already exist")
    
    return True

def download_unrar():
    """Download and install UnRAR if needed"""
    print("Checking UnRAR installation...")
    
    # Check if UnRAR is already available
    try:
        result = subprocess.run(['unrar'], capture_output=True, text=True)
        if result.returncode == 0 or 'UNRAR' in result.stdout:
            print("  [OK] UnRAR is already installed")
            return True
    except FileNotFoundError:
        pass
    
    print("UnRAR not found. Attempting to download...")
    
    # Download UnRAR
    try:
        url = "https://www.rarlab.com/rar/unrarw32.exe"
        temp_dir = Path(tempfile.gettempdir())
        unrar_installer = temp_dir / "unrarw32.exe"
        
        print(f"  Downloading from {url}...")
        urllib.request.urlretrieve(url, unrar_installer)
        
        print("  [WARN] Please run the downloaded installer manually:")
        print(f"  {unrar_installer}")
        print("  After installation, add UnRAR to your PATH")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Failed to download UnRAR: {e}")
        print("  Please download manually from: https://www.rarlab.com/rar_add.htm")
        return False

def detect_and_install_handbrake():
    """Detect and optionally install HandBrake"""
    print("Checking HandBrake installation...")
    
    # Common HandBrake installation paths
    handbrake_paths = [
        "C:/Program Files/HandBrake/HandBrakeCLI.exe",
        "C:/Program Files (x86)/HandBrake/HandBrakeCLI.exe",
        "C:/Users/" + os.getenv('USERNAME', '') + "/AppData/Local/HandBrake/HandBrakeCLI.exe",
    ]
    
    # Check if HandBrake is already installed
    for path in handbrake_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"  [OK] HandBrake found: {path}")
                    return path
            except Exception:
                continue
    
    # Check if HandBrake is in PATH
    try:
        result = subprocess.run(['HandBrakeCLI', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  [OK] HandBrake found in PATH")
            return "HandBrakeCLI"
    except Exception:
        pass
    
    print("  [WARN] HandBrake not found")
    
    # Offer to download HandBrake
    response = input("  Download HandBrake installer? (y/n) [y]: ").strip()
    if response.lower() in ['', 'y', 'yes']:
        try:
            # Get latest release info from GitHub API
            print("  Getting latest HandBrake release info...")
            api_url = "https://api.github.com/repos/HandBrake/HandBrake/releases/latest"
            
            with urllib.request.urlopen(api_url) as response:
                import json
                release_data = json.loads(response.read().decode())
            
            tag_name = release_data['tag_name']
            
            # Find Windows GUI installer in assets
            installer_url = None
            installer_filename = None
            for asset in release_data['assets']:
                if 'Win_GUI.exe' in asset['name'] and ('x86_64' in asset['name'] or 'x64' in asset['name']):
                    installer_url = asset['browser_download_url']
                    installer_filename = asset['name']
                    break
            
            if not installer_url:
                print("  [ERROR] Could not find Windows installer in latest release")
                print("  Please download manually from: https://handbrake.fr/downloads.php")
                return None
            
            temp_dir = Path(tempfile.gettempdir())
            handbrake_installer = temp_dir / installer_filename
            
            print(f"  Downloading HandBrake {tag_name}...")
            print(f"  File: {installer_filename}")
            urllib.request.urlretrieve(installer_url, handbrake_installer)
            
            print(f"  [OK] Downloaded HandBrake installer: {handbrake_installer}")
            
            # Ask if user wants to run installer now
            run_response = input("  Run HandBrake installer now? (y/n) [y]: ").strip()
            if run_response.lower() in ['', 'y', 'yes']:
                try:
                    print("  [INFO] Running HandBrake installer with elevation...")
                    
                    # Try to run with elevation using PowerShell
                    powershell_cmd = f'Start-Process -FilePath "{handbrake_installer}" -Verb RunAs -Wait'
                    result = subprocess.run(['powershell', '-Command', powershell_cmd], 
                                          capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        print("  [OK] HandBrake installer completed")
                        
                        # Wait a moment and check again
                        print("  [INFO] Checking installation...")
                        time.sleep(5)
                        
                        # Re-check for HandBrake
                        for path in handbrake_paths:
                            if os.path.exists(path):
                                try:
                                    result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=10)
                                    if result.returncode == 0:
                                        print(f"  [OK] HandBrake installed successfully: {path}")
                                        return path
                                except Exception:
                                    continue
                        
                        print("  [WARN] Installation completed but HandBrake not found in expected locations")
                        print("  [INFO] You may need to restart this script after installation")
                    else:
                        print(f"  [WARN] Installer may have been cancelled or failed")
                        print(f"  [INFO] Please run manually as administrator: {handbrake_installer}")
                    
                except Exception as e:
                    print(f"  [WARN] Could not run installer with elevation: {e}")
                    print(f"  [INFO] Please run manually as administrator: {handbrake_installer}")
                    print("  [INFO] Right-click the installer and select 'Run as administrator'")
            else:
                print(f"  [INFO] Please install manually as administrator: {handbrake_installer}")
                print("  [INFO] Right-click the installer and select 'Run as administrator'")
            
            return None
            
        except Exception as e:
            print(f"  [ERROR] Failed to download HandBrake: {e}")
            print("  Please download manually from: https://handbrake.fr/downloads.php")
            return None
    
    return None

def create_initial_config():
    """Create initial configuration file"""
    print("Creating initial configuration...")
    
    config_path = Path('config.yaml')
    
    if config_path.exists():
        response = input("Config file already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("  [OK] Keeping existing configuration")
            return True
    
    # Get user input for configuration
    print("\nConfiguration setup:")
    print("Leave blank to use default values")
    
    # Enhanced Plex server discovery
    print("\n--- Plex Server Discovery ---")
    discovered_server = discover_plex_server()
    
    if discovered_server and discovered_server != "http://127.0.0.1:32400":
        print(f"Found server: {discovered_server}")
        use_discovered_server = input("Use discovered server? (y/n) [y]: ").strip()
        if use_discovered_server.lower() in ['', 'y', 'yes']:
            plex_host = discovered_server
            print("[OK] Using discovered server")
        else:
            plex_host = input("Plex server URL [http://127.0.0.1:32400]: ").strip()
            if not plex_host:
                plex_host = "http://127.0.0.1:32400"
    else:
        plex_host = input("Plex server URL [http://127.0.0.1:32400]: ").strip()
        if not plex_host:
            plex_host = "http://127.0.0.1:32400"
    
    # Enhanced Plex token detection
    print("\n--- Plex Token Detection ---")
    discovered_token = discover_plex_token()
    
    if discovered_token:
        print(f"Found token: {discovered_token[:20]}...")
        use_discovered = input("Use discovered token? (y/n) [y]: ").strip()
        if use_discovered.lower() in ['', 'y', 'yes']:
            plex_token = discovered_token
            print("[OK] Using discovered token")
        else:
            plex_token = input("Enter Plex token manually: ").strip()
            if not plex_token:
                plex_token = "PLEX-TOKEN-HERE"
    else:
        print("No token found automatically.")
        plex_token = input("Enter Plex token manually [PLEX-TOKEN-HERE]: ").strip()
        if not plex_token:
            plex_token = "PLEX-TOKEN-HERE"
    
    # Enhanced library selection
    library_key = 2  # Default fallback
    
    if plex_token and plex_token != "PLEX-TOKEN-HERE":
        print("\n--- Plex Library Selection ---")
        print("Testing Plex connection...")
        
        if test_plex_connection(plex_host, plex_token):
            print("[OK] Connected to Plex server")
            
            libraries = get_plex_libraries(plex_host, plex_token)
            if libraries:
                selected_key = select_library(libraries)
                if selected_key:
                    library_key = selected_key
                else:
                    print("No library selected, using default key: 2")
            else:
                print("No libraries found, using default key: 2")
        else:
            print("[ERROR] Could not connect to Plex server")
            library_key_input = input("Enter library section key manually [2]: ").strip()
            if library_key_input:
                try:
                    library_key = int(library_key_input)
                except ValueError:
                    library_key = 2
    else:
        print("Skipping library detection (no valid token)")
        library_key_input = input("Library section key [2]: ").strip()
        if library_key_input:
            try:
                library_key = int(library_key_input)
            except ValueError:
                library_key = 2
    
    # Get paths
    print("\n--- Directory Configuration ---")
    base_dir = Path.cwd()
    
    watch_dir = input(f"Watch directory [D:/x265]: ").strip()
    if not watch_dir:
        watch_dir = "D:/x265"
    
    work_dir = input(f"Work directory [{base_dir / 'work'}]: ").strip()
    if not work_dir:
        work_dir = str(base_dir / 'work')
    
    target_dir = input("Target directory (where movies go) [D:/Media/Movies]: ").strip()
    if not target_dir:
        target_dir = "D:/Media/Movies"
    
    # HandBrake configuration - detect if HandBrake was found
    handbrake_enabled = False
    handbrake_exe = "C:/Program Files/HandBrake/HandBrakeCLI.exe"
    
    # Check if HandBrake was detected in previous step
    handbrake_paths = [
        "C:/Program Files/HandBrake/HandBrakeCLI.exe",
        "C:/Program Files (x86)/HandBrake/HandBrakeCLI.exe",
        "HandBrakeCLI"
    ]
    
    for path in handbrake_paths:
        try:
            if path == "HandBrakeCLI":
                result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
            else:
                if os.path.exists(path):
                    result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
                else:
                    continue
            
            if result.returncode == 0:
                handbrake_exe = path
                handbrake_enabled = True
                print(f"\n[OK] HandBrake detected and will be enabled: {path}")
                break
        except Exception:
            continue
    
    if not handbrake_enabled:
        enable_response = input("\nEnable H.265 re-encoding with HandBrake? (y/n) [n]: ").strip()
        if enable_response.lower() in ['y', 'yes']:
            handbrake_enabled = True
    
    # Create configuration
    config = {
        'plex': {
            'host': plex_host,
            'token': plex_token,
            'library_key': library_key
        },
        'paths': {
            'watch': watch_dir,
            'work': work_dir,
            'target': target_dir,
            'failed': str(base_dir / 'failed'),
            'archive': str(base_dir / 'archive')
        },
        'options': {
            'delete_archives': True,
            'extensions': ['.rar', '.r00', '.r01', '.r02', '.r03', '.r04', '.r05', '.r06', '.r07', '.r08', '.r09'],
            'duplicate_check': True,
            'file_stabilization_time': 10,
            'max_file_age': 3600,
            'enable_gui': False,
            'enable_reencoding': handbrake_enabled
        },
        'handbrake': {
            'enabled': handbrake_enabled,
            'executable': handbrake_exe,
            'preset': "Fast 1080p30",
            'quality': 22
        },
        'logging': {
            'level': 'INFO',
            'max_log_size': 10485760,
            'backup_count': 5
        }
    }
    
    # Write configuration
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("[SUCCESS] Configuration file created")
    
    if handbrake_enabled:
        print("[INFO] HandBrake re-encoding is enabled")
    
    return True

def run_test():
    """Run installation test"""
    print("\nRunning installation test...")
    
    try:
        result = subprocess.run([sys.executable, 'test_installation.py'], 
                              capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("=== Plex RAR Bridge Setup ===")
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("[ERROR] Python 3.8 or higher is required")
        return 1
    
    print(f"[SUCCESS] Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Setup steps
    steps = [
        ("Create directories", create_directories),
        ("Install Python dependencies", install_python_dependencies),
        ("Check/Download UnRAR", download_unrar),
        ("Check/Download HandBrake", detect_and_install_handbrake),
    ]
    
    # Store HandBrake detection result
    handbrake_path = None
    
    for step_name, step_func in steps:
        print(f"\n--- {step_name} ---")
        
        if step_name == "Check/Download HandBrake":
            # Special handling for HandBrake detection
            handbrake_path = step_func()
            # This step doesn't fail even if HandBrake isn't found
            pass
        else:
            if not step_func():
                print(f"[ERROR] Setup failed at: {step_name}")
                return 1
    
    # Create configuration (this will use the HandBrake detection results)
    print(f"\n--- Create configuration ---")
    if not create_initial_config():
        print(f"[ERROR] Setup failed at: Create configuration")
        return 1
    
    print("\n--- Testing Installation ---")
    if run_test():
        print("\n[SUCCESS] Setup completed successfully!")
        print("\nNext steps:")
        print("1. Verify your target directory path in config.yaml")
        print("2. Check that target directory is monitored by Plex")
        print("3. Run: python plex_rar_bridge.py")
        print("4. Or install as service: install_service_easy.bat")
        
        if handbrake_path:
            print(f"\n[INFO] HandBrake is installed and enabled for H.265 re-encoding")
        else:
            print(f"\n[INFO] HandBrake not installed - files will be processed without re-encoding")
            
        print(f"\n[INFO] Drop RAR files into: {Path('config.yaml').parent / 'rar_watch' if Path('config.yaml').exists() else 'D:/x265'}")
    else:
        print("\n[WARN] Setup completed but some tests failed")
        print("Please review the test output above")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 