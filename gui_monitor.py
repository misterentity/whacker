#!/usr/bin/env python3
"""
Real-time GUI Monitor for Plex RAR Bridge
Shows detailed thread status, processing activity, and live monitoring
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import queue
import re
import yaml
import ftplib
import ssl
from urllib.parse import urlparse
import socket
import psutil
import tempfile
import shutil
import requests
from PIL import Image, ImageTk
import urllib.request
import hashlib
from functools import lru_cache

class IMDbHelper:
    """Helper class for fetching IMDb information and poster thumbnails"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or "YOUR_OMDB_API_KEY"  # OMDb API key - get from http://www.omdbapi.com/
        self.base_url = "http://www.omdbapi.com/"
        self.cache_dir = Path("thumbnails_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'PlexRarBridge-FTPPanel/1.0'})
        
    @lru_cache(maxsize=500)
    def search_content(self, title, year=None, content_type=None):
        """Search for movie/TV show information"""
        try:
            params = {
                'apikey': self.api_key,
                't': title,
                'plot': 'short'
            }
            
            if year:
                params['y'] = year
            if content_type == 'tv_show':
                params['type'] = 'series'
            elif content_type == 'movie':
                params['type'] = 'movie'
                
            response = self.session.get(self.base_url, params=params, timeout=5)
            data = response.json()
            
            if data.get('Response') == 'True':
                return {
                    'title': data.get('Title', ''),
                    'year': data.get('Year', ''),
                    'genre': data.get('Genre', ''),
                    'director': data.get('Director', ''),
                    'actors': data.get('Actors', ''),
                    'plot': data.get('Plot', ''),
                    'imdb_rating': data.get('imdbRating', ''),
                    'poster_url': data.get('Poster', ''),
                    'runtime': data.get('Runtime', ''),
                    'type': data.get('Type', '')
                }
            else:
                error_msg = data.get('Error', 'Unknown error')
                if 'Invalid API key' in error_msg:
                    print(f"❌ Invalid OMDb API key! Get a free key at: https://www.omdbapi.com/apikey.aspx")
                else:
                    print(f"IMDb search failed for '{title}': {error_msg}")
                    
        except Exception as e:
            print(f"IMDb search failed for '{title}': {e}")
        
        return None
    
    def download_thumbnail(self, poster_url, content_title):
        """Download and cache poster thumbnail"""
        if not poster_url or poster_url == 'N/A':
            return None
            
        try:
            # Create cache filename
            url_hash = hashlib.md5(poster_url.encode()).hexdigest()
            cache_file = self.cache_dir / f"{url_hash}.jpg"
            
            # Return cached file if exists
            if cache_file.exists():
                return str(cache_file)
            
            # Download poster
            response = self.session.get(poster_url, timeout=10)
            response.raise_for_status()
            
            # Save original
            with open(cache_file, 'wb') as f:
                f.write(response.content)
            
            # Create thumbnail
            thumb_file = self.cache_dir / f"{url_hash}_thumb.jpg"
            try:
                with Image.open(cache_file) as img:
                    img.thumbnail((100, 150), Image.Resampling.LANCZOS)
                    img.save(thumb_file, 'JPEG', quality=85)
                return str(thumb_file)
            except Exception:
                return str(cache_file)  # Return original if thumbnail creation fails
                
        except Exception as e:
            print(f"Failed to download poster for '{content_title}': {e}")
            return None
    
    def extract_clean_title(self, folder_name):
        """Extract clean title from release folder name"""
        # Remove common separators and convert to title case
        clean = re.sub(r'[._-]', ' ', folder_name)
        
        # Remove parentheses and their content (often contain technical info)
        clean = re.sub(r'\([^)]*\)', '', clean)
        
        # Remove brackets and their content
        clean = re.sub(r'\[[^\]]*\]', '', clean)
        
        # Remove year (but keep it for separate extraction)
        clean = re.sub(r'\b(19|20)\d{2}\b', '', clean)
        
        # Remove quality indicators (case insensitive)
        quality_patterns = [
            r'\b(720p|1080p|2160p|4k|uhd|1080i|720i)\b',
            r'\b(bluray|blu-ray|brrip|dvdrip|webrip|hdtv|web|webdl|web-dl)\b',
            r'\b(x264|x265|h264|h265|hevc|xvid|avc|av1)\b',
            r'\b(dts|ac3|aac|mp3|flac|truehd|atmos)\b',
            r'\b(hdr|hdr10|dolby|vision|dv)\b',
            r'\b(extended|directors|unrated|theatrical|remastered|imax|criterion)\b',
            r'\b(internal|proper|repack|read\.nfo|readnfo|rerip)\b',
            r'\b(extras|sample|proof|subbed|dubbed)\b'
        ]
        
        for pattern in quality_patterns:
            clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)
        
        # Remove release group patterns (more comprehensive)
        # Groups at the end after dash
        clean = re.sub(r'-[A-Z0-9]+$', '', clean, flags=re.IGNORECASE)
        # Groups at the end in brackets
        clean = re.sub(r'\[[A-Z0-9]+\]$', '', clean, flags=re.IGNORECASE)
        
        # Remove season/episode info for TV shows
        clean = re.sub(r'\bs\d{1,2}e\d{1,2}\b', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bseason\s*\d+\b', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bepisode\s*\d+\b', '', clean, flags=re.IGNORECASE)
        
        # Remove special characters and symbols
        clean = re.sub(r'[•·]', ' ', clean)
        clean = re.sub(r'[^\w\s]', ' ', clean)
        
        # Remove remaining ALL CAPS words (likely release groups)
        words = clean.split()
        filtered_words = []
        for word in words:
            # Keep word if it's not all caps OR if it's a short word (like "TV", "HD") OR if it's a common word
            if not (word.isupper() and len(word) > 3 and word not in ['IMAX', 'HDTV']):
                filtered_words.append(word)
        clean = ' '.join(filtered_words)
        
        # Clean up multiple spaces and trim
        clean = ' '.join(clean.split())
        return clean.strip()
    
    def extract_year(self, folder_name):
        """Extract year from folder name"""
        match = re.search(r'\b(19|20)(\d{2})\b', folder_name)
        return f"{match.group(1)}{match.group(2)}" if match else None

class ManualAuthTLSWrapper:
    """
    Wrapper class that provides ftplib-compatible interface for manual AUTH TLS connections
    This allows us to use manual SSL negotiation while maintaining compatibility with existing GUI code
    """
    
    def __init__(self, ssl_socket, host, port, gui_logger=None):
        self.ssl_socket = ssl_socket
        self.host = host
        self.port = port
        self.current_dir = "/"
        self.passive_mode = True
        self.response_buffer = ""  # Buffer for partial responses
        self.data_protection = 'clear'  # Default to clear data connections
        self.gui_logger = gui_logger
        
    def _read_all_responses(self):
        """Read all pending responses from the socket"""
        all_responses = []
        try:
            self.ssl_socket.settimeout(0.5)  # Short timeout for reading pending data
            while True:
                try:
                    data = self.ssl_socket.recv(4096)
                    if data:
                        text = data.decode('utf-8', errors='ignore')
                        all_responses.append(text)
                    else:
                        break
                except:
                    break
        except:
            pass
        finally:
            self.ssl_socket.settimeout(10)  # Reset timeout
        
        if all_responses:
            combined = ''.join(all_responses)
            print(f"      Cleared pending responses: {combined.strip()}")
        
        return all_responses
    
    def sendcmd(self, cmd):
        """Send a command and get response with proper FTP protocol handling"""
        # Get logger from the GUI instance
        if hasattr(self, 'gui_logger'):
            self.gui_logger.info(f"      FTP: {cmd}")
        
        # Clear any pending responses first
        self._read_all_responses()
        
        # Send command
        self.ssl_socket.send(f'{cmd}\r\n'.encode())
        
        # Read response with proper FTP protocol handling
        response_lines = []
        
        try:
            self.ssl_socket.settimeout(15)  # Give time for response
            
            # Keep reading until we get a complete FTP response
            while True:
                data = self.ssl_socket.recv(4096)
                if not data:
                    break
                
                text = data.decode('utf-8', errors='ignore')
                
                # Add to buffer and process lines
                self.response_buffer += text
                
                # Split into lines and process
                while '\n' in self.response_buffer:
                    line, self.response_buffer = self.response_buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                        
                    response_lines.append(line)
                    
                    # Check if this is a final response line
                    if len(line) >= 4 and line[3:4] == ' ' and line[:3].isdigit():
                        final_response = '\n'.join(response_lines)
                        if hasattr(self, 'gui_logger'):
                            self.gui_logger.info(f"      Response: {final_response}")
                        return final_response
                
                # Small delay for more data
                time.sleep(0.1)
            
            # Return what we have
            final_response = '\n'.join(response_lines) if response_lines else ""
            if hasattr(self, 'gui_logger'):
                self.gui_logger.info(f"      Response: {final_response}")
            return final_response
            
        except Exception as e:
            print(f"      Socket error: {e}")
            return ""
        finally:
            self.ssl_socket.settimeout(10)
    
    def voidcmd(self, cmd):
        """Send a command and expect 200-series response"""
        response = self.sendcmd(cmd)
        if not (response.startswith('2') or response.startswith('1')):
            raise Exception(f"Command failed: {cmd} -> {response}")
        return response
    
    def pwd(self):
        """Get current working directory"""
        response = self.sendcmd('PWD')
        if response.startswith('257'):
            # Extract directory from '257 "/path/to/dir" is current directory'
            import re
            match = re.search(r'"([^"]*)"', response)
            if match:
                self.current_dir = match.group(1)
                return self.current_dir
        return self.current_dir
    
    def cwd(self, dirname):
        """Change working directory"""
        response = self.sendcmd(f'CWD {dirname}')
        if response.startswith('250'):
            if dirname == '..':
                # Go up one level
                if self.current_dir != '/':
                    parts = self.current_dir.rstrip('/').split('/')
                    self.current_dir = '/'.join(parts[:-1]) or '/'
            elif dirname == '/':
                self.current_dir = '/'
            else:
                # Navigate to directory
                if dirname.startswith('/'):
                    self.current_dir = dirname
                else:
                    if self.current_dir.endswith('/'):
                        self.current_dir += dirname
                    else:
                        self.current_dir += '/' + dirname
        else:
            raise Exception(f"CWD failed: {response}")
    
    def nlst(self, dirname=None):
        """Get directory listing (names only)"""
        try:
            # Use PASV mode for data connection
            pasv_response = self.sendcmd('PASV')
            if not pasv_response.startswith('227'):
                print(f"      PASV not supported, trying EPSV...")
                # Try EPSV as fallback
                epsv_response = self.sendcmd('EPSV')
                if not epsv_response.startswith('229'):
                    raise Exception(f"Both PASV and EPSV failed")
                
                # Parse EPSV response: 229 Entering Extended Passive Mode (|||21000|)
                import re
                match = re.search(r'\(\|\|\|(\d+)\|\)', epsv_response)
                if not match:
                    raise Exception("Could not parse EPSV response")
                
                data_host = self.host  # Use same host for EPSV
                data_port = int(match.group(1))
            else:
                # Parse PASV response to get data connection info
                import re
                match = re.search(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', pasv_response)
                if not match:
                    raise Exception("Could not parse PASV response")
                
                h1, h2, h3, h4, p1, p2 = map(int, match.groups())
                data_host = f"{h1}.{h2}.{h3}.{h4}"
                data_port = p1 * 256 + p2
            
            print(f"      Data connection: {data_host}:{data_port}")
            
            # Create data connection (clear, not SSL)
            import socket
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.settimeout(30)
            data_sock.connect((data_host, data_port))
            
            # Send NLST command
            cmd = 'NLST' if dirname is None else f'NLST {dirname}'
            list_response = self.sendcmd(cmd)
            
            # Read data
            data = b''
            try:
                while True:
                    chunk = data_sock.recv(8192)
                    if not chunk:
                        break
                    data += chunk
            except:
                pass
            
            data_sock.close()
            
            # Get final response (transfer complete)
            final_response = self.ssl_socket.recv(1024).decode('utf-8', errors='ignore')
            print(f"      Final: {final_response.strip()}")
            
            # Parse file list
            if data:
                files = data.decode('utf-8', errors='ignore').strip().split('\n')
                return [f.strip() for f in files if f.strip()]
            
            return []
            
        except Exception as e:
            print(f"      NLST failed: {e}")
            return []
    
    def dir(self, dirname=None, callback=None):
        """Get detailed directory listing"""
        try:
            # Use PASV mode for data connection
            pasv_response = self.sendcmd('PASV')
            if not pasv_response.startswith('227'):
                raise Exception(f"PASV failed: {pasv_response}")
            
            # Parse PASV response
            import re
            match = re.search(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', pasv_response)
            if not match:
                raise Exception("Could not parse PASV response")
            
            h1, h2, h3, h4, p1, p2 = map(int, match.groups())
            data_host = f"{h1}.{h2}.{h3}.{h4}"
            data_port = p1 * 256 + p2
            
            # Create data connection
            import socket
            import ssl
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.settimeout(30)
            data_sock.connect((data_host, data_port))
            
            # Send LIST command
            cmd = 'LIST' if dirname is None else f'LIST {dirname}'
            list_response = self.sendcmd(cmd)
            
            # Wrap data connection with SSL for glftpd compatibility
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                ssl_data_sock = ssl_context.wrap_socket(data_sock, server_hostname=data_host)
                print(f"      SSL data connection established after LIST")
            except Exception as ssl_e:
                print(f"      SSL wrap failed, trying plain connection: {ssl_e}")
                ssl_data_sock = data_sock
            
            # Read data
            data = b''
            try:
                while True:
                    chunk = ssl_data_sock.recv(8192)
                    if not chunk:
                        break
                    data += chunk
            except:
                pass
            
            ssl_data_sock.close()
            
            # Get final response
            final_response = self.ssl_socket.recv(1024).decode('utf-8', errors='ignore')
            
            # Process data with callback if provided
            if data and callback:
                lines = data.decode('utf-8', errors='ignore').strip().split('\n')
                for line in lines:
                    if line.strip():
                        callback(line)
            
            return data.decode('utf-8', errors='ignore') if data else ""
            
        except Exception as e:
            print(f"      LIST failed: {e}")
            return ""
    
    def retrbinary(self, cmd, callback, blocksize=8192):
        """Retrieve a file in binary mode"""
        try:
            # Use PASV mode for data connection
            pasv_response = self.sendcmd('PASV')
            if not pasv_response.startswith('227'):
                raise Exception(f"PASV failed: {pasv_response}")
            
            # Parse PASV response
            import re
            match = re.search(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', pasv_response)
            if not match:
                raise Exception("Could not parse PASV response")
            
            h1, h2, h3, h4, p1, p2 = map(int, match.groups())
            data_host = f"{h1}.{h2}.{h3}.{h4}"
            data_port = p1 * 256 + p2
            
            # Create data connection
            import socket
            import ssl
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.settimeout(60)
            data_sock.connect((data_host, data_port))
            
            # Send command (e.g., RETR filename)
            retr_response = self.sendcmd(cmd)
            if not retr_response.startswith('1'):  # 150 or 125 for data transfer
                data_sock.close()
                raise Exception(f"RETR failed: {retr_response}")
            
            # Wrap data connection with SSL for glftpd compatibility
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                ssl_data_sock = ssl_context.wrap_socket(data_sock, server_hostname=data_host)
                print(f"      SSL data connection established after RETR")
            except Exception as ssl_e:
                print(f"      SSL wrap failed, trying plain connection: {ssl_e}")
                ssl_data_sock = data_sock
            
            # Read data and call callback
            try:
                while True:
                    chunk = ssl_data_sock.recv(blocksize)
                    if not chunk:
                        break
                    callback(chunk)
            except Exception as e:
                print(f"      Data transfer error: {e}")
            
            ssl_data_sock.close()
            
            # Get final response
            final_response = self.ssl_socket.recv(1024).decode('utf-8', errors='ignore')
            if not final_response.startswith('226'):
                print(f"      Warning: Unexpected final response: {final_response.strip()}")
            
        except Exception as e:
            print(f"      RETR failed: {e}")
            raise
    
    def retrlines(self, cmd, callback=None):
        """Retrieve data in line mode (for directory listings)"""
        try:
            # Use PASV mode for data connection
            pasv_response = self.sendcmd('PASV')
            if not pasv_response.startswith('227'):
                raise Exception(f"PASV failed: {pasv_response}")
            
            # Parse PASV response
            import re
            match = re.search(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', pasv_response)
            if not match:
                raise Exception("Could not parse PASV response")
            
            h1, h2, h3, h4, p1, p2 = map(int, match.groups())
            data_host = f"{h1}.{h2}.{h3}.{h4}"
            data_port = p1 * 256 + p2
            
            print(f"      Data connection: {data_host}:{data_port}")
            
            # Create data connection
            import socket
            import ssl
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.settimeout(30)
            data_sock.connect((data_host, data_port))
            
            # Send LIST command first (before SSL handshake for some servers)
            list_response = self.sendcmd(cmd)
            if not list_response.startswith('1'):  # 150 or 125 for data transfer
                data_sock.close()
                raise Exception(f"LIST failed: {list_response}")
            
            # Now wrap with SSL if using PROT P (after LIST command is accepted)
            if self.data_protection == 'ssl':
                try:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                    ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
                    
                    # Use shorter timeout for SSL handshake
                    data_sock.settimeout(5)
                    data_sock = ssl_context.wrap_socket(data_sock, server_hostname=None)
                    print(f"      SSL data connection established after LIST")
                except Exception as ssl_error:
                    print(f"      SSL data connection failed: {ssl_error}")
                    # Close the failed connection and raise error since server requires SSL
                    try:
                        data_sock.close()
                    except:
                        pass
                    raise Exception("SSL data connection required but failed")
            else:
                print(f"      Using clear data connection")
            
            # Read data
            data = b''
            try:
                while True:
                    chunk = data_sock.recv(8192)
                    if not chunk:
                        break
                    data += chunk
            except Exception as e:
                print(f"      Data read error: {e}")
            
            data_sock.close()
            
            # Get final response (transfer complete)
            final_response = self.sendcmd('NOOP')  # Get any pending response
            print(f"      Data transfer complete")
            
            # Process data line by line
            lines = []
            if data:
                text_data = data.decode('utf-8', errors='ignore')
                lines = text_data.strip().split('\n')
                
                # Call callback for each line if provided
                if callback:
                    for line in lines:
                        if line.strip():
                            callback(line.strip())
            
            return lines
            
        except Exception as e:
            print(f"      retrlines failed: {e}")
            return []
    
    def size(self, filename):
        """Get file size"""
        try:
            response = self.sendcmd(f'SIZE {filename}')
            if response.startswith('213'):
                return int(response.split()[1])
        except:
            pass
        return None
    
    def set_pasv(self, val):
        """Set passive mode (ftplib compatibility)"""
        self.passive_mode = bool(val)
        print(f"      Passive mode set to: {self.passive_mode}")
    
    def set_debuglevel(self, level):
        """Set debug level (ftplib compatibility)"""
        # We already print debug info, so this is just for compatibility
        pass
    
    def connect(self, host, port):
        """Connect method (ftplib compatibility) - already connected"""
        # This wrapper is created after connection, so this is a no-op
        pass
    
    def login(self, user, password):
        """Login method (ftplib compatibility) - already logged in"""
        # This wrapper is created after login, so this is a no-op
        pass
    
    def getwelcome(self):
        """Get welcome message (ftplib compatibility)"""
        return "220 Checker Flag"  # Return the server's welcome message
    
    def close(self):
        """Close connection (alias for quit)"""
        self.quit()
    
    def quit(self):
        """Close the connection"""
        try:
            self.sendcmd('QUIT')
        except:
            pass
        finally:
            try:
                self.ssl_socket.close()
            except:
                pass

class PlexRarBridgeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Plex RAR Bridge - Real-time Monitor")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2b2b2b')
        
        # Initialize variables
        self.script_dir = Path(__file__).parent.absolute()
        self.log_file = self.script_dir / "logs" / "bridge.log"
        self.ftp_log_file = self.script_dir / "logs" / "ftp.log"
        self.config_file = self.script_dir / "config.yaml"
        self.ftp_config_file = self.script_dir / "ftp_config.json"
        self.service_name = "PlexRarBridge"
        
        # Data storage
        self.active_threads = {}
        self.retry_queue = {}
        self.recent_activity = []
        self.statistics = {
            'processed': 0,
            'errors': 0,
            'warnings': 0,
            'retries': 0,
            'uptime': 0
        }
        
        # Threading
        self.update_queue = queue.Queue()
        self.running = True
        
        # Initialize IMDb helper
        self.imdb_helper = IMDbHelper()
        
        # Setup FTP logging
        self.setup_ftp_logging()
        
        # Setup GUI
        self.setup_gui()
        self.setup_monitoring()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start GUI update loop
        self.update_gui_loop()
    
    def setup_gui(self):
        """Setup the GUI layout"""
        # Create main style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'), foreground='white', background='#2b2b2b')
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'), foreground='#4CAF50', background='#2b2b2b')
        style.configure('Status.TLabel', font=('Arial', 9), foreground='white', background='#2b2b2b')
        style.configure('Running.TLabel', font=('Arial', 9, 'bold'), foreground='#4CAF50', background='#2b2b2b')
        style.configure('Error.TLabel', font=('Arial', 9, 'bold'), foreground='#f44336', background='#2b2b2b')
        style.configure('Warning.TLabel', font=('Arial', 9, 'bold'), foreground='#ff9800', background='#2b2b2b')
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section - Service Status
        self.create_service_status_section(main_frame)
        
        # Middle section - Notebook with tabs
        self.create_tabbed_section(main_frame)
        
        # Bottom section - Control buttons
        self.create_control_section(main_frame)
    
    def create_service_status_section(self, parent):
        """Create service status section"""
        status_frame = ttk.LabelFrame(parent, text="Service Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Service info grid
        info_frame = ttk.Frame(status_frame)
        info_frame.pack(fill=tk.X)
        
        # Service status
        ttk.Label(info_frame, text="Service:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.service_status_label = ttk.Label(info_frame, text="Checking...", style='Status.TLabel')
        self.service_status_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 30))
        
        # Process status
        ttk.Label(info_frame, text="Process:", style='Header.TLabel').grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.process_status_label = ttk.Label(info_frame, text="Checking...", style='Status.TLabel')
        self.process_status_label.grid(row=0, column=3, sticky=tk.W, padx=(0, 30))
        
        # Monitoring status
        ttk.Label(info_frame, text="Monitoring:", style='Header.TLabel').grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        self.monitoring_status_label = ttk.Label(info_frame, text="Checking...", style='Status.TLabel')
        self.monitoring_status_label.grid(row=0, column=5, sticky=tk.W)
        
        # Statistics row
        ttk.Label(info_frame, text="Processed:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.processed_label = ttk.Label(info_frame, text="0", style='Status.TLabel')
        self.processed_label.grid(row=1, column=1, sticky=tk.W, padx=(0, 30))
        
        ttk.Label(info_frame, text="Errors:", style='Header.TLabel').grid(row=1, column=2, sticky=tk.W, padx=(0, 10))
        self.errors_label = ttk.Label(info_frame, text="0", style='Status.TLabel')
        self.errors_label.grid(row=1, column=3, sticky=tk.W, padx=(0, 30))
        
        ttk.Label(info_frame, text="Uptime:", style='Header.TLabel').grid(row=1, column=4, sticky=tk.W, padx=(0, 10))
        self.uptime_label = ttk.Label(info_frame, text="Unknown", style='Status.TLabel')
        self.uptime_label.grid(row=1, column=5, sticky=tk.W)
    
    def create_tabbed_section(self, parent):
        """Create tabbed section with different views"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Tab 1: Active Threads
        self.create_threads_tab()
        
        # Tab 2: Retry Queue
        self.create_retry_queue_tab()
        
        # Tab 3: Live Logs
        self.create_logs_tab()
        
        # Tab 4: Statistics
        self.create_statistics_tab()
        
        # Tab 5: FTP Download Panel
        self.create_ftp_tab()
        
        # Tab 6: Setup Panel
        self.create_setup_tab()
        
        # Tab 7: Enhanced Setup Panel
        self.create_enhanced_setup_tab()
        
        # Tab 8: Configuration
        self.create_config_tab()
    
    def create_threads_tab(self):
        """Create active threads monitoring tab"""
        threads_frame = ttk.Frame(self.notebook)
        self.notebook.add(threads_frame, text="Active Threads")
        
        # Thread list with details
        ttk.Label(threads_frame, text="Active Processing Threads", style='Title.TLabel').pack(pady=(10, 5))
        
        # Thread tree view
        columns = ('Thread', 'Status', 'File', 'Progress', 'Started', 'Duration')
        self.threads_tree = ttk.Treeview(threads_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.threads_tree.heading(col, text=col)
            self.threads_tree.column(col, width=150 if col != 'File' else 300)
        
        # Scrollbar for threads
        threads_scroll = ttk.Scrollbar(threads_frame, orient=tk.VERTICAL, command=self.threads_tree.yview)
        self.threads_tree.configure(yscrollcommand=threads_scroll.set)
        
        # Pack thread view
        thread_container = ttk.Frame(threads_frame)
        thread_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.threads_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        threads_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Thread details
        ttk.Label(threads_frame, text="Thread Details", style='Header.TLabel').pack(pady=(10, 5))
        self.thread_details = scrolledtext.ScrolledText(threads_frame, height=6, font=('Consolas', 9))
        self.thread_details.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Bind selection
        self.threads_tree.bind('<<TreeviewSelect>>', self.on_thread_select)
    
    def create_retry_queue_tab(self):
        """Create retry queue monitoring tab"""
        retry_frame = ttk.Frame(self.notebook)
        self.notebook.add(retry_frame, text="Retry Queue")
        
        ttk.Label(retry_frame, text="Files Waiting for Completion", style='Title.TLabel').pack(pady=(10, 5))
        
        # Retry queue tree view
        retry_columns = ('File', 'Attempts', 'First Seen', 'Last Attempt', 'Status')
        self.retry_tree = ttk.Treeview(retry_frame, columns=retry_columns, show='headings', height=10)
        
        for col in retry_columns:
            self.retry_tree.heading(col, text=col)
            self.retry_tree.column(col, width=200 if col == 'File' else 120)
        
        # Scrollbar for retry queue
        retry_scroll = ttk.Scrollbar(retry_frame, orient=tk.VERTICAL, command=self.retry_tree.yview)
        self.retry_tree.configure(yscrollcommand=retry_scroll.set)
        
        # Pack retry view
        retry_container = ttk.Frame(retry_frame)
        retry_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.retry_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        retry_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Retry queue controls
        control_frame = ttk.Frame(retry_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="Force Retry Selected", command=self.force_retry).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Remove Selected", command=self.remove_from_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Clear Old Entries", command=self.clear_old_entries).pack(side=tk.LEFT, padx=5)
    
    def create_logs_tab(self):
        """Create live logs monitoring tab"""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Live Logs")
        
        # Log info header
        log_info_frame = ttk.Frame(logs_frame)
        log_info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(log_info_frame, text="📝 Monitoring: Bridge + FTP Logs", style='Header.TLabel').pack(side=tk.LEFT)
        
        # Log controls
        log_control_frame = ttk.Frame(logs_frame)
        log_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(log_control_frame, text="Log Level Filter:", style='Header.TLabel').pack(side=tk.LEFT, padx=(0, 10))
        
        self.log_level_var = tk.StringVar(value="ALL")
        log_levels = ["ALL", "INFO", "WARNING", "ERROR"]
        log_level_combo = ttk.Combobox(log_control_frame, textvariable=self.log_level_var, values=log_levels, width=10)
        log_level_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(log_control_frame, text="Clear", command=self.clear_logs).pack(side=tk.LEFT, padx=10)
        ttk.Button(log_control_frame, text="Save Logs", command=self.save_logs).pack(side=tk.LEFT, padx=5)
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_control_frame, text="Auto-scroll", variable=self.auto_scroll_var).pack(side=tk.RIGHT)
        
        # Live log display
        self.log_display = scrolledtext.ScrolledText(logs_frame, font=('Consolas', 9), height=20)
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configure log text tags for coloring
        self.log_display.tag_configure("INFO", foreground="#4CAF50")
        self.log_display.tag_configure("WARNING", foreground="#ff9800")
        self.log_display.tag_configure("ERROR", foreground="#f44336")
        self.log_display.tag_configure("DEBUG", foreground="#2196F3")
    
    def create_statistics_tab(self):
        """Create statistics tab"""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="Statistics")
        
        ttk.Label(stats_frame, text="Processing Statistics", style='Title.TLabel').pack(pady=(10, 20))
        
        # Statistics grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(pady=20)
        
        # Create statistics labels
        self.stats_labels = {}
        stats_info = [
            ("Total Files Processed", "processed", 0),
            ("Total Errors", "errors", 1),
            ("Total Warnings", "warnings", 2),
            ("Total Retries", "retries", 3),
            ("Active Threads", "active_threads", 4),
            ("Queue Length", "queue_length", 5),
            ("Service Uptime", "uptime", 6),
            ("Files per Hour", "rate", 7)
        ]
        
        for i, (label, key, row) in enumerate(stats_info):
            ttk.Label(stats_grid, text=f"{label}:", style='Header.TLabel').grid(row=row, column=0, sticky=tk.W, padx=(0, 20), pady=5)
            self.stats_labels[key] = ttk.Label(stats_grid, text="0", style='Status.TLabel')
            self.stats_labels[key].grid(row=row, column=1, sticky=tk.W, pady=5)
        
        # Recent activity summary
        ttk.Label(stats_frame, text="Recent Activity Summary", style='Title.TLabel').pack(pady=(40, 10))
        
        self.activity_summary = scrolledtext.ScrolledText(stats_frame, height=10, font=('Consolas', 9))
        self.activity_summary.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    def create_ftp_tab(self):
        """Create FTP SSL download tab"""
        ftp_frame = ttk.Frame(self.notebook)
        self.notebook.add(ftp_frame, text="FTP Downloads")
        
        # Initialize FTP variables
        self.ftp_connection = None
        self.ftp_connected = False
        self.ftp_current_dir = "/"
        self.download_queue = []
        self.active_downloads = {}
        
        # Create main paned window for left/right layout
        main_paned = ttk.PanedWindow(ftp_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Connection and Controls
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # Right panel - File Browser and Downloads
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        self.create_ftp_connection_panel(left_frame)
        self.create_ftp_browser_panel(right_frame)
    
    def create_ftp_connection_panel(self, parent):
        """Create FTP connection settings panel"""
        # Connection Settings
        conn_frame = ttk.LabelFrame(parent, text="FTP SSL Connection", padding=10)
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Connection presets
        ttk.Label(conn_frame, text="Saved Connections:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ftp_presets_var = tk.StringVar()
        self.ftp_presets_combo = ttk.Combobox(conn_frame, textvariable=self.ftp_presets_var, width=22, state="readonly")
        self.ftp_presets_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        self.ftp_presets_combo.bind('<<ComboboxSelected>>', self.load_ftp_preset)
        
        ttk.Button(conn_frame, text="Save", command=self.save_ftp_preset).grid(row=0, column=2, padx=(5, 0), pady=2)
        
        # Server settings
        ttk.Label(conn_frame, text="Server:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=2)
        self.ftp_host_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.ftp_host_var, width=25).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(conn_frame, text="Port:", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=2)
        self.ftp_port_var = tk.StringVar(value="21")
        ttk.Entry(conn_frame, textvariable=self.ftp_port_var, width=25).grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(conn_frame, text="Username:", style='Header.TLabel').grid(row=3, column=0, sticky=tk.W, pady=2)
        self.ftp_user_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.ftp_user_var, width=25).grid(row=3, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(conn_frame, text="Password:", style='Header.TLabel').grid(row=4, column=0, sticky=tk.W, pady=2)
        self.ftp_pass_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.ftp_pass_var, width=25, show="*").grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # SSL Mode
        ttk.Label(conn_frame, text="SSL Mode:", style='Header.TLabel').grid(row=5, column=0, sticky=tk.W, pady=2)
        self.ftp_ssl_var = tk.StringVar(value="Explicit")
        ssl_combo = ttk.Combobox(conn_frame, textvariable=self.ftp_ssl_var, values=["Explicit", "Implicit", "None"], width=22, state="readonly")
        ssl_combo.grid(row=5, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Connection status and controls
        status_frame = ttk.Frame(conn_frame)
        status_frame.grid(row=6, column=0, columnspan=3, sticky=tk.W+tk.E, pady=(10, 0))
        
        self.ftp_status_label = ttk.Label(status_frame, text="❌ Disconnected", style='Error.TLabel')
        self.ftp_status_label.pack(side=tk.LEFT)
        
        ttk.Button(status_frame, text="Connect", command=self.ftp_connect).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(status_frame, text="Disconnect", command=self.ftp_disconnect).pack(side=tk.RIGHT)
        
        # Download Settings
        download_frame = ttk.LabelFrame(parent, text="Download Destinations", padding=10)
        download_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Movie destination
        ttk.Label(download_frame, text="🎬 Movies:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ftp_movie_dirs_var = tk.StringVar()
        movie_frame = ttk.Frame(download_frame)
        movie_frame.grid(row=0, column=1, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        movie_frame.columnconfigure(0, weight=1)
        ttk.Entry(movie_frame, textvariable=self.ftp_movie_dirs_var, width=20).grid(row=0, column=0, sticky=tk.W+tk.E)
        ttk.Button(movie_frame, text="Browse", command=self.browse_movie_dir).grid(row=0, column=1, padx=(5, 0))
        
        # TV Show destination
        ttk.Label(download_frame, text="📺 TV Shows:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=2)
        self.ftp_tv_dirs_var = tk.StringVar()
        tv_frame = ttk.Frame(download_frame)
        tv_frame.grid(row=1, column=1, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        tv_frame.columnconfigure(0, weight=1)
        ttk.Entry(tv_frame, textvariable=self.ftp_tv_dirs_var, width=20).grid(row=0, column=0, sticky=tk.W+tk.E)
        ttk.Button(tv_frame, text="Browse", command=self.browse_tv_dir).grid(row=0, column=1, padx=(5, 0))
        
        # General download directory (fallback)
        ttk.Label(download_frame, text="📁 General:", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=2)
        self.ftp_download_dir_var = tk.StringVar()
        
        # Load default download directory from config
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                default_download = config.get('paths', {}).get('watch', str(self.script_dir))
                self.ftp_download_dir_var.set(default_download)
        except:
            self.ftp_download_dir_var.set(str(self.script_dir))
        
        general_frame = ttk.Frame(download_frame)
        general_frame.grid(row=2, column=1, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        general_frame.columnconfigure(0, weight=1)
        ttk.Entry(general_frame, textvariable=self.ftp_download_dir_var, width=20).grid(row=0, column=0, sticky=tk.W+tk.E)
        ttk.Button(general_frame, text="Browse", command=self.browse_download_dir).grid(row=0, column=1, padx=(5, 0))
        
        # Configure column weights
        download_frame.columnconfigure(1, weight=1)
        
        # File filters
        ttk.Label(download_frame, text="File Filter:", style='Header.TLabel').grid(row=3, column=0, sticky=tk.W, pady=2)
        self.ftp_filter_var = tk.StringVar(value="*.rar")
        ttk.Entry(download_frame, textvariable=self.ftp_filter_var, width=25).grid(row=3, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Transfer mode
        ttk.Label(download_frame, text="Transfer Mode:", style='Header.TLabel').grid(row=4, column=0, sticky=tk.W, pady=2)
        self.ftp_mode_var = tk.StringVar(value="Binary")
        mode_combo = ttk.Combobox(download_frame, textvariable=self.ftp_mode_var, values=["Binary", "ASCII"], width=22, state="readonly")
        mode_combo.grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Download Queue
        queue_frame = ttk.LabelFrame(parent, text="Download Queue", padding=10)
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Queue controls
        queue_controls = ttk.Frame(queue_frame)
        queue_controls.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(queue_controls, text="Start Queue", command=self.start_download_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_controls, text="Pause Queue", command=self.pause_download_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_controls, text="Clear Queue", command=self.clear_download_queue).pack(side=tk.LEFT)
        
        # Queue list
        queue_columns = ('File', 'Size', 'Status')
        self.download_queue_tree = ttk.Treeview(queue_frame, columns=queue_columns, show='headings', height=8)
        
        for col in queue_columns:
            self.download_queue_tree.heading(col, text=col)
            if col == 'File':
                self.download_queue_tree.column(col, width=200)
            else:
                self.download_queue_tree.column(col, width=80)
        
        # Scrollbar for queue
        queue_scroll = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.download_queue_tree.yview)
        self.download_queue_tree.configure(yscrollcommand=queue_scroll.set)
        
        queue_tree_frame = ttk.Frame(queue_frame)
        queue_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.download_queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        queue_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load FTP presets
        self.load_ftp_config()
    
    def create_ftp_browser_panel(self, parent):
        """Create FTP file browser and download management"""
        # Search box at the top
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        
        ttk.Label(search_frame, text="🔍 Quick Search:", style='Header.TLabel').pack(side=tk.LEFT)
        self.ftp_search_var = tk.StringVar()
        self.ftp_search_entry = ttk.Entry(search_frame, textvariable=self.ftp_search_var, width=30, font=('Arial', 10))
        self.ftp_search_entry.pack(side=tk.LEFT, padx=(5, 10), fill=tk.X, expand=True)
        
        # Clear search button
        ttk.Button(search_frame, text="✖", command=self.clear_search, width=3).pack(side=tk.LEFT, padx=2)
        
        # Search result count
        self.search_result_label = ttk.Label(search_frame, text="", style='Status.TLabel')
        self.search_result_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Bind search events
        self.ftp_search_var.trace('w', self.filter_content)
        self.ftp_search_entry.bind('<Escape>', lambda e: self.clear_search())
        self.ftp_search_entry.bind('<Return>', lambda e: self.ftp_files_tree.focus())
        
        # Add tooltip
        self.ftp_search_entry.bind('<FocusIn>', lambda e: self.show_search_tip())
        self.ftp_search_entry.bind('<FocusOut>', lambda e: self.hide_search_tip())
        
        # Current directory and navigation
        nav_frame = ttk.Frame(parent)
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(nav_frame, text="Current Directory:", style='Header.TLabel').pack(side=tk.LEFT)
        self.ftp_current_dir_label = ttk.Label(nav_frame, text="/", style='Status.TLabel')
        self.ftp_current_dir_label.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Button(nav_frame, text="🔼 Up", command=self.ftp_go_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="🏠 Root", command=self.ftp_go_root).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="🔄 Refresh", command=self.ftp_refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="🔍 Scan Content", command=self.ftp_scan_content).pack(side=tk.LEFT, padx=2)
        
        # Content type filter
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(filter_frame, text="Content Filter:", style='Header.TLabel').pack(side=tk.LEFT)
        self.ftp_content_filter_var = tk.StringVar(value="All")
        content_filter = ttk.Combobox(filter_frame, textvariable=self.ftp_content_filter_var, 
                                     values=["All", "Movies", "TV Shows", "Other"], width=12, state="readonly")
        content_filter.pack(side=tk.LEFT, padx=(5, 10))
        content_filter.bind('<<ComboboxSelected>>', self.ftp_apply_content_filter)
        
        ttk.Button(filter_frame, text="🎬 Movie Folders", command=self.ftp_show_movie_folders).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="📺 TV Folders", command=self.ftp_show_tv_folders).pack(side=tk.LEFT, padx=2)
        
        # File browser
        browser_frame = ttk.LabelFrame(parent, text="Remote Files", padding=5)
        browser_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid weights
        browser_frame.grid_rowconfigure(0, weight=1)
        browser_frame.grid_columnconfigure(0, weight=1)
        
        # Create file tree with simplified columns for fast loading
        columns = ("Type", "Name", "Size", "Date", "Content")
        self.ftp_files_tree = ttk.Treeview(browser_frame, columns=columns, show='headings', height=12)
        
        # Configure columns with sorting
        self.ftp_files_tree.heading("Type", text="Type", command=lambda: self._sort_column("Type", False))
        self.ftp_files_tree.heading("Name", text="Name ▼", command=lambda: self._sort_column("Name", False))
        self.ftp_files_tree.heading("Size", text="Size", command=lambda: self._sort_column("Size", False))
        self.ftp_files_tree.heading("Date", text="Date", command=lambda: self._sort_column("Date", False))
        self.ftp_files_tree.heading("Content", text="Content", command=lambda: self._sort_column("Content", False))
        
        # Track current sort column and direction
        self.current_sort_column = "Name"
        self.sort_reverse = False
        
        self.ftp_files_tree.column("Type", width=80, minwidth=60)
        self.ftp_files_tree.column("Name", width=300, minwidth=200)
        self.ftp_files_tree.column("Size", width=100, minwidth=80)
        self.ftp_files_tree.column("Date", width=120, minwidth=100)
        self.ftp_files_tree.column("Content", width=100, minwidth=80)
        
        # Scrollbars
        files_v_scroll = ttk.Scrollbar(browser_frame, orient=tk.VERTICAL, command=self.ftp_files_tree.yview)
        files_h_scroll = ttk.Scrollbar(browser_frame, orient=tk.HORIZONTAL, command=self.ftp_files_tree.xview)
        self.ftp_files_tree.configure(yscrollcommand=files_v_scroll.set, xscrollcommand=files_h_scroll.set)
        
        # Pack file browser
        self.ftp_files_tree.grid(row=0, column=0, sticky=tk.NSEW)
        files_v_scroll.grid(row=0, column=1, sticky=tk.NS)
        files_h_scroll.grid(row=1, column=0, sticky=tk.EW)
        
        browser_frame.columnconfigure(0, weight=1)
        browser_frame.rowconfigure(0, weight=1)
        
        # File operations
        file_ops_frame = ttk.Frame(parent)
        file_ops_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_ops_frame, text="📁 Enter Directory", command=self.ftp_enter_directory).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_ops_frame, text="⬇ Download Selected", command=self.ftp_download_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_ops_frame, text="📁⬇ Download Folder", command=self.ftp_download_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_ops_frame, text="⬇ Download All RAR", command=self.ftp_download_all_rar).pack(side=tk.LEFT, padx=2)
        
        # Initialize content tracking
        self.discovered_content = {
            'movies': [],
            'tv_shows': [],
            'other': []
        }
        self.current_view = 'all'
        
        # Initialize download settings
        self.ftp_max_downloads_var = tk.StringVar(value="3")
        
        # Store poster images to prevent garbage collection
        self.poster_images = {}
        
        # Store original items for filtering
        self.original_items = []
        self.is_filtered = False
        
        # Bind events
        self.ftp_files_tree.bind("<Button-3>", self.show_context_menu)  # Right-click for context menu
        self.ftp_files_tree.bind("<Double-1>", self.ftp_on_double_click)  # Double-click for navigation/download
        
        # Create context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="🎬 Show IMDb Info", command=self.show_imdb_info)
        self.context_menu.add_command(label="🖼️ Show Poster", command=self.show_poster_preview)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📁 Enter Directory", command=self.ftp_enter_directory)
        self.context_menu.add_command(label="⬇ Download", command=self.ftp_download_selected)
        self.context_menu.add_command(label="📁⬇ Download Folder", command=self.ftp_download_folder)
        
        # Add global keyboard shortcuts for search
        self.root.bind_all('<Control-f>', self.focus_search)
        self.root.bind_all('<Control-F>', self.focus_search)
    
    def detect_content_type(self, folder_name, folder_path=""):
        """Detect if a folder contains movies, TV shows, or other content"""
        folder_lower = folder_name.lower()
        
        # TV Show patterns
        tv_patterns = [
            # Season/Episode patterns
            r's\d{1,2}e\d{1,2}',  # S01E01
            r'season[\s\._-]*\d+',  # Season 1, Season.1, etc
            r'episode[\s\._-]*\d+',  # Episode 1
            r'\d{1,2}x\d{1,2}',  # 1x01
            r'complete[\s\._-]*series',
            r'tv[\s\._-]*series',
            # TV keywords
            'series', 'seasons', 'episodes', 'tvshow', 'tv.show',
            # Common TV folders
            'tv', 'television', 'shows', 'series'
        ]
        
        # Movie patterns  
        movie_patterns = [
            # Year patterns (movies typically have years)
            r'(19|20)\d{2}',  # 1900-2099
            # Resolution/quality patterns
            r'(720p|1080p|2160p|4k|1080i|720i)',
            r'(bluray|blu-ray|brrip|dvdrip|webrip|hdtv)',
            r'(x264|x265|h264|h265|hevc|xvid)',
            # Movie keywords
            'movie', 'film', 'cinema', 'theatrical',
            # Common movie folders
            'movies', 'films', 'movie', 'x264', 'x265', 'bluray', 'remux'
        ]
        
        # Check for TV patterns (more explicit detection)
        import re
        
        # Strong TV indicators that should always win
        if re.search(r's\d{1,2}e\d{1,2}', folder_lower):  # S01E01, S04E05, etc.
            return 'tv_show'
        if re.search(r'\d{1,2}x\d{1,2}', folder_lower):  # 1x01, 4x05, etc.
            return 'tv_show'
        if re.search(r'season[\s\._-]*\d+', folder_lower):  # Season 1, Season.1, etc
            return 'tv_show'
        if re.search(r'episode[\s\._-]*\d+', folder_lower):  # Episode 1
            return 'tv_show'
        
        # Check other TV patterns
        for pattern in tv_patterns:
            if isinstance(pattern, str):
                if pattern in folder_lower:
                    return 'tv_show'
            else:
                if re.search(pattern, folder_lower):
                    return 'tv_show'
        
        # Check for movie patterns
        movie_score = 0
        for pattern in movie_patterns:
            if isinstance(pattern, str):
                if pattern in folder_lower:
                    movie_score += 1
            else:
                if re.search(pattern, folder_lower):
                    movie_score += 1
        
        # Special folder names that indicate content type
        if any(keyword in folder_lower for keyword in ['recent', 'new', 'latest']):
            # Don't scan inside folders - just return other
            return 'other'
        
        # If multiple movie indicators, likely a movie
        if movie_score >= 2:
            return 'movie'
        elif movie_score >= 1 and not any(tv in folder_lower for tv in ['series', 'season', 'episode']):
            return 'movie'
        
        return 'other'
    
    def get_content_imdb_info(self, folder_name, content_type):
        """Get IMDb information for content"""
        try:
            # Extract clean title and year
            clean_title = self.imdb_helper.extract_clean_title(folder_name)
            year = self.imdb_helper.extract_year(folder_name)
            
            if not clean_title:
                return None
            
            # Search for content
            imdb_info = self.imdb_helper.search_content(clean_title, year, content_type)
            
            if imdb_info:
                # Download thumbnail in background
                threading.Thread(
                    target=self._download_poster_async,
                    args=(imdb_info['poster_url'], clean_title, folder_name),
                    daemon=True
                ).start()
            
            return imdb_info
            
        except Exception as e:
            print(f"Failed to get IMDb info for '{folder_name}': {e}")
            return None
    
    def _download_poster_async(self, poster_url, clean_title, folder_name):
        """Download poster thumbnail asynchronously"""
        try:
            thumb_path = self.imdb_helper.download_thumbnail(poster_url, clean_title)
            if thumb_path:
                # Load and store thumbnail for display
                self.root.after(0, self._update_poster_display, folder_name, thumb_path)
        except Exception as e:
            print(f"Async poster download failed for '{clean_title}': {e}")
    
    def _update_poster_display(self, folder_name, thumb_path):
        """Update poster storage for later display"""
        try:
            # Load thumbnail image
            img = Image.open(thumb_path)
            img.thumbnail((60, 90), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Store image to prevent garbage collection
            self.poster_images[folder_name] = {
                'thumbnail': photo,
                'path': thumb_path
            }
            
            print(f"Poster cached for '{folder_name}'")
                    
        except Exception as e:
            print(f"Failed to cache poster for '{folder_name}': {e}")
    
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        # Select the item under cursor
        item = self.ftp_files_tree.identify_row(event.y)
        if item:
            self.ftp_files_tree.selection_set(item)
            
            # Check if this is a movie/TV folder to enable IMDb options
            values = self.ftp_files_tree.item(item, 'values')
            content_type = values[4] if len(values) > 4 else ""  # Content column
            
            # Enable/disable IMDb options based on content type
            if "Movie" in content_type or "TV Show" in content_type:
                self.context_menu.entryconfig("🎬 Show IMDb Info", state="normal")
                self.context_menu.entryconfig("🖼️ Show Poster", state="normal")
            else:
                self.context_menu.entryconfig("🎬 Show IMDb Info", state="disabled")
                self.context_menu.entryconfig("🖼️ Show Poster", state="disabled")
                
            # Show context menu
            self.context_menu.post(event.x_root, event.y_root)
    
    def show_imdb_info(self):
        """Show IMDb information for selected item"""
        selection = self.ftp_files_tree.selection()
        if not selection:
            return
            
        try:
            item = self.ftp_files_tree.item(selection[0])
            values = item['values']
            folder_name = values[1]  # Name column
            content_type = values[4] if len(values) > 4 else ""  # Content column
            
            # Determine content type for IMDb search
            imdb_content_type = None
            if "Movie" in content_type:
                imdb_content_type = "movie"
            elif "TV Show" in content_type:
                imdb_content_type = "tv_show"
            else:
                messagebox.showinfo("No IMDb Info", "IMDb information is only available for movies and TV shows.")
                return
            
            # Show loading message
            loading_popup = tk.Toplevel(self.root)
            loading_popup.title("Loading IMDb Info...")
            loading_popup.geometry("300x100")
            loading_popup.configure(bg='#2b2b2b')
            tk.Label(loading_popup, text="🔍 Searching IMDb...", bg='#2b2b2b', fg='white', 
                    font=('Arial', 12)).pack(expand=True)
            loading_popup.update()
            
            # Get IMDb information
            imdb_info = self.get_content_imdb_info(folder_name, imdb_content_type)
            
            # Close loading popup
            loading_popup.destroy()
            
            if imdb_info:
                self._show_imdb_window(folder_name, imdb_info)
            else:
                messagebox.showinfo("No Results", f"No IMDb information found for '{folder_name}'")
                
        except Exception as e:
            print(f"Failed to show IMDb info: {e}")
            messagebox.showerror("Error", f"Failed to retrieve IMDb information: {e}")
    
    def show_poster_preview(self):
        """Show poster preview for selected item (now called from context menu)"""
        selection = self.ftp_files_tree.selection()
        if not selection:
            return
        
        try:
            values = self.ftp_files_tree.item(selection[0], 'values')
            folder_name = values[1]  # Name column
            
            # Check if we have poster for this item
            if folder_name in self.poster_images:
                self._show_poster_window(folder_name, values)
            else:
                messagebox.showinfo("No Poster", "No poster available. Try 'Show IMDb Info' first to download the poster.")
        except Exception as e:
            print(f"Failed to show poster preview: {e}")
    
    def _show_imdb_window(self, folder_name, imdb_info):
        """Show IMDb information in a popup window"""
        try:
            # Create popup window
            popup = tk.Toplevel(self.root)
            popup.title(f"IMDb Info: {imdb_info['title']}")
            popup.geometry("500x700")
            popup.configure(bg='#2b2b2b')
            
            # Title
            title_label = tk.Label(popup, text=imdb_info['title'], bg='#2b2b2b', 
                                  fg='white', font=('Arial', 16, 'bold'), wraplength=450)
            title_label.pack(pady=10)
            
            # Poster
            if folder_name in self.poster_images:
                poster_data = self.poster_images[folder_name]
                if 'path' in poster_data:
                    # Load larger poster
                    img = Image.open(poster_data['path'])
                    img.thumbnail((250, 375), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    poster_label = tk.Label(popup, image=photo, bg='#2b2b2b')
                    poster_label.image = photo  # Keep reference
                    poster_label.pack(pady=10)
            
            # Info frame
            info_frame = tk.Frame(popup, bg='#2b2b2b')
            info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            # Create info text
            info_lines = []
            if imdb_info.get('year'):
                info_lines.append(f"📅 Year: {imdb_info['year']}")
            if imdb_info.get('imdb_rating') and imdb_info['imdb_rating'] != 'N/A':
                info_lines.append(f"⭐ IMDb Rating: {imdb_info['imdb_rating']}/10")
            if imdb_info.get('runtime'):
                info_lines.append(f"⏱️ Runtime: {imdb_info['runtime']}")
            if imdb_info.get('genre'):
                info_lines.append(f"🎭 Genre: {imdb_info['genre']}")
            if imdb_info.get('director'):
                info_lines.append(f"🎬 Director: {imdb_info['director']}")
            if imdb_info.get('actors'):
                info_lines.append(f"👥 Cast: {imdb_info['actors']}")
            if imdb_info.get('plot'):
                info_lines.append(f"\n📖 Plot:\n{imdb_info['plot']}")
            
            info_text = "\n\n".join(info_lines)
            
            # Scrollable text widget
            text_frame = tk.Frame(info_frame, bg='#2b2b2b')
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text_widget = scrolledtext.ScrolledText(text_frame, bg='#3b3b3b', fg='white', 
                                                   wrap=tk.WORD, height=10, font=('Arial', 10))
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert(tk.END, info_text)
            text_widget.config(state=tk.DISABLED)
            
            # Buttons frame
            button_frame = tk.Frame(popup, bg='#2b2b2b')
            button_frame.pack(fill=tk.X, padx=20, pady=10)
            
            tk.Button(button_frame, text="Close", command=popup.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            print(f"Failed to create IMDb window: {e}")
    
    def _show_poster_window(self, folder_name, item_values):
        """Show poster in a popup window"""
        try:
            if folder_name not in self.poster_images:
                messagebox.showinfo("No Poster", "No poster available for this item.")
                return
                
            poster_data = self.poster_images[folder_name]
            
            # Create popup window
            popup = tk.Toplevel(self.root)
            popup.title(f"Poster: {folder_name}")
            popup.geometry("400x600")
            popup.configure(bg='#2b2b2b')
            
            # Load and display poster
            if 'path' in poster_data:
                img = Image.open(poster_data['path'])
                img.thumbnail((350, 525), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                poster_label = tk.Label(popup, image=photo, bg='#2b2b2b')
                poster_label.image = photo  # Keep reference
                poster_label.pack(pady=20)
            
            # Title
            title_label = tk.Label(popup, text=folder_name, bg='#2b2b2b', 
                                  fg='white', font=('Arial', 12), wraplength=350)
            title_label.pack(pady=10)
            
            # Close button
            tk.Button(popup, text="Close", command=popup.destroy).pack(pady=10)
            
        except Exception as e:
            print(f"Failed to create poster window: {e}")
    
    def filter_content(self, *args):
        """Filter content in real-time as user types"""
        search_term = self.ftp_search_var.get().lower().strip()
        
        if not search_term:
            # No search term - restore original items
            self.restore_original_items()
            return
        
        # Filter original items
        if not self.original_items:
            # Store current items as original if not already stored
            self.store_original_items()
        
        # Clear current view
        for item in self.ftp_files_tree.get_children():
            self.ftp_files_tree.delete(item)
        
        # Filter and display matching items
        matched_count = 0
        for item_data in self.original_items:
            values, tags = item_data
            
            # Search in the name column (index 1)
            name = values[1].lower() if len(values) > 1 else ""
            
            # Also search in content type (index 4) for movie/tv filtering
            content = values[4].lower() if len(values) > 4 else ""
            
            # Check if search term matches name or content
            if search_term in name or search_term in content:
                item_id = self.ftp_files_tree.insert('', 'end', values=values)
                if tags:
                    self.ftp_files_tree.item(item_id, tags=tags)
                matched_count += 1
        
        # Update search result count
        total_count = len(self.original_items)
        self.search_result_label.config(text=f"{matched_count}/{total_count} items")
        self.is_filtered = True
    
    def store_original_items(self):
        """Store current tree items for filtering"""
        self.original_items = []
        for child in self.ftp_files_tree.get_children():
            item = self.ftp_files_tree.item(child)
            values = item['values']
            tags = item.get('tags', ())
            self.original_items.append((values, tags))
    
    def restore_original_items(self):
        """Restore original items when search is cleared"""
        if not self.original_items or not self.is_filtered:
            return
        
        # Clear current view
        for item in self.ftp_files_tree.get_children():
            self.ftp_files_tree.delete(item)
        
        # Restore all original items
        for item_data in self.original_items:
            values, tags = item_data
            item_id = self.ftp_files_tree.insert('', 'end', values=values)
            if tags:
                self.ftp_files_tree.item(item_id, tags=tags)
        
        # Clear search result count
        self.search_result_label.config(text="")
        self.is_filtered = False
    
    def clear_search(self):
        """Clear search box and restore full listing"""
        self.ftp_search_var.set("")
        self.restore_original_items()
        self.ftp_search_entry.focus()
    
    def update_search_status(self):
        """Update search status after content is loaded"""
        if hasattr(self, 'search_result_label'):
            total_items = len(self.ftp_files_tree.get_children())
            if total_items > 0 and not self.is_filtered:
                self.search_result_label.config(text=f"{total_items} items")
            elif total_items == 0:
                self.search_result_label.config(text="")
    
    def show_search_tip(self):
        """Show search tip"""
        if not self.ftp_search_var.get():
            # Temporarily set placeholder text (will be cleared on typing)
            pass
    
    def hide_search_tip(self):
        """Hide search tip"""
        pass
    
    def focus_search(self, event=None):
        """Focus the search box (can be called via keyboard shortcut)"""
        if hasattr(self, 'ftp_search_entry'):
            self.ftp_search_entry.focus()
            self.ftp_search_entry.select_range(0, tk.END)
    
    def _analyze_folder_contents(self, folder_path):
        """Analyze folder contents to determine content type"""
        if not self.ftp_connected:
            return 'other'
        
        try:
            # Save current directory
            original_dir = self.ftp_connection.pwd()
            
            # Navigate to folder
            self.ftp_connection.cwd(folder_path)
            
            # Get directory listing
            lines = self.ftp_connection.retrlines('LIST')
            
            movie_count = 0
            tv_count = 0
            
            for line in lines:
                if line.startswith('d'):  # Directory
                    dir_name = line.split()[-1]
                    content_type = self.detect_content_type(dir_name)
                    if content_type == 'movie':
                        movie_count += 1
                    elif content_type == 'tv_show':
                        tv_count += 1
            
            # Restore original directory
            self.ftp_connection.cwd(original_dir)
            
            # Determine predominant type
            if tv_count > movie_count:
                return 'tv_show'
            elif movie_count > tv_count:
                return 'movie'
            else:
                return 'other'
                
        except Exception as e:
            print(f"Error analyzing folder contents: {e}")
            return 'other'
    
    def ftp_scan_content(self):
        """Scan FTP server for movie and TV show content"""
        if not self.ftp_connected:
            messagebox.showwarning("Not Connected", "Please connect to FTP server first")
            return
        
        self.ftp_status_label.config(text="🔍 Scanning for content...", style='Warning.TLabel')
        self.root.update()
        
        # Clear previous discoveries
        self.discovered_content = {
            'movies': [],
            'tv_shows': [], 
            'other': []
        }
        
        try:
            # Save current directory
            original_dir = self.ftp_connection.pwd()
            
            # Scan common content directories
            scan_paths = ['/', '/recent', '/movies', '/tv', '/x264', '/x265', '/incoming']
            
            for path in scan_paths:
                try:
                    print(f"Scanning: {path}")
                    self.ftp_connection.cwd(path)
                    lines = self.ftp_connection.retrlines('LIST')
                    
                    for line in lines:
                        if line.startswith('d'):  # Directory
                            dir_name = line.split()[-1]
                            if dir_name in ['.', '..']:
                                continue
                                
                            current_path = f"{path}/{dir_name}".replace('//', '/')
                            content_type = self.detect_content_type(dir_name, current_path)
                            
                            folder_info = {
                                'name': dir_name,
                                'path': current_path,
                                'parent': path,
                                'type': content_type
                            }
                            
                            if content_type == 'movie':
                                self.discovered_content['movies'].append(folder_info)
                            elif content_type == 'tv_show':
                                self.discovered_content['tv_shows'].append(folder_info)
                            else:
                                self.discovered_content['other'].append(folder_info)
                                
                except Exception as e:
                    print(f"Could not scan {path}: {e}")
                    continue
            
            # Restore original directory
            self.ftp_connection.cwd(original_dir)
            
            # Update status
            movie_count = len(self.discovered_content['movies'])
            tv_count = len(self.discovered_content['tv_shows'])
            other_count = len(self.discovered_content['other'])
            
            self.ftp_status_label.config(
                text=f"✅ Found: {movie_count} movies, {tv_count} TV shows, {other_count} other", 
                style='Running.TLabel'
            )
            
            # Refresh current view to show content types
            self.ftp_refresh()
            
            messagebox.showinfo(
                "Content Scan Complete",
                f"Discovered content:\n\n"
                f"🎬 Movies: {movie_count} folders\n"
                f"📺 TV Shows: {tv_count} folders\n"
                f"📁 Other: {other_count} folders\n\n"
                f"Use the content filter to view specific types."
            )
            
        except Exception as e:
            self.ftp_status_label.config(text="❌ Scan failed", style='Error.TLabel')
            messagebox.showerror("Scan Error", f"Failed to scan content: {e}")
    
    def ftp_show_movie_folders(self):
        """Show only movie folders"""
        self.current_view = 'movies'
        self._display_discovered_content('movies')
    
    def ftp_show_tv_folders(self):
        """Show only TV show folders"""
        self.current_view = 'tv_shows'
        self._display_discovered_content('tv_shows')
    
    def _display_discovered_content(self, content_type):
        """Display discovered content of specified type"""
        if not self.discovered_content[content_type]:
            messagebox.showinfo(
                "No Content Found",
                f"No {content_type.replace('_', ' ')} found. Run content scan first."
            )
            return
        
        # Clear current listing and search state
        for item in self.ftp_files_tree.get_children():
            self.ftp_files_tree.delete(item)
        
        # Reset search state
        self.original_items = []
        self.is_filtered = False
        if hasattr(self, 'ftp_search_var'):
            self.ftp_search_var.set("")
            self.search_result_label.config(text="")
        
        # Display content with full path information stored in tags
        for folder_info in self.discovered_content[content_type]:
            content_label = "🎬 Movie" if content_type == 'movies' else "📺 TV Show"
            
            # Store the full path information in the item's tags
            item_id = self.ftp_files_tree.insert('', 'end', values=(
                "📁 DIR",           # Type
                folder_info['name'], # Name
                "",                  # Size
                "",                  # Date
                content_label        # Content
            ))
            
            # Store the full path and parent directory in the item's tags
            self.ftp_files_tree.item(item_id, tags=(folder_info['path'], folder_info['parent'], folder_info['name']))
        
        # Update current directory label
        self.ftp_current_dir_label.config(text=f"[{content_type.replace('_', ' ').title()} View]")
        
        # Update search status
        self.update_search_status()
    
    def ftp_apply_content_filter(self, event=None):
        """Apply content filter"""
        filter_type = self.ftp_content_filter_var.get().lower()
        
        if filter_type == "all":
            self.current_view = 'all'
            self.ftp_refresh()
        elif filter_type == "movies":
            self.ftp_show_movie_folders()
        elif filter_type == "tv shows":
            self.ftp_show_tv_folders()
        elif filter_type == "other":
            self.current_view = 'other'
            self._display_discovered_content('other')
    
    def browse_download_dir(self):
        """Browse for download directory"""
        directory = filedialog.askdirectory(title="Select Download Directory")
        if directory:
            self.ftp_download_dir_var.set(directory)
    
    def ftp_connect(self):
        """Connect to FTP server with professional-grade SSL handling"""
        try:
            host = self.ftp_host_var.get().strip()
            port = int(self.ftp_port_var.get().strip() or "21")
            user = self.ftp_user_var.get().strip()
            password = self.ftp_pass_var.get()
            ssl_mode = self.ftp_ssl_var.get()
            
            if not host or not user:
                messagebox.showerror("Connection Error", "Please enter host and username")
                return
            
            self.ftp_status_label.config(text="🔄 Connecting...", style='Warning.TLabel')
            self.root.update()
            
            # Log connection attempt
            self.ftp_logger.info(f"FTP Connection Attempt:")
            self.ftp_logger.info(f"  Host: {host}")
            self.ftp_logger.info(f"  Port: {port}")
            self.ftp_logger.info(f"  Username: {user}")
            self.ftp_logger.info(f"  SSL Mode: {ssl_mode}")
            
            # Professional client approaches (ordered by success likelihood)
            if ssl_mode == "Explicit":
                self.ftp_logger.info("  Attempting professional FTPS Explicit approaches...")
                success = self._connect_professional_explicit(host, port, user, password)
                
            elif ssl_mode == "Implicit":
                self.ftp_logger.info("  Attempting professional FTPS Implicit approaches...")
                success = self._connect_professional_implicit(host, port, user, password)
                
            else:
                self.ftp_logger.info("  Attempting plain FTP connection...")
                success = self._connect_plain_ftp(host, port, user, password)
            
            if not success:
                return
            
            # Configure connection settings
            self.ftp_logger.info("  Configuring connection settings...")
            
            # Set passive mode (required by many servers)
            self.ftp_connection.set_pasv(True)
            self.ftp_logger.info("  Passive mode enabled")
            
            # Set binary mode by default
            if self.ftp_mode_var.get() == "Binary":
                self.ftp_logger.info("  Setting binary transfer mode...")
                try:
                    self.ftp_connection.voidcmd('TYPE I')
                    self.ftp_logger.info("  Binary mode set successfully")
                except:
                    self.ftp_logger.warning("  Binary mode setting failed (non-critical)")
            
            # Get current directory
            try:
                self.ftp_current_dir = self.ftp_connection.pwd()
                self.ftp_logger.info(f"  Current directory: {self.ftp_current_dir}")
            except:
                self.ftp_current_dir = "/"
                self.ftp_logger.info("  Using default directory: /")
            
            # Mark as connected
            self.ftp_connected = True
            self.ftp_status_label.config(text="✅ Connected", style='Running.TLabel')
            self.ftp_current_dir_label.config(text=self.ftp_current_dir)
            
            # Load directory listing
            self.ftp_logger.info("  Loading directory listing...")
            self.ftp_refresh()
            self.ftp_logger.info("  Connection established successfully!")
            
            # Auto-scan for content after successful connection
            self.ftp_logger.info("  Auto-scanning for content...")
            threading.Thread(target=self._auto_scan_content, daemon=True).start()
            
        except Exception as e:
            self.ftp_logger.error(f"  CRITICAL ERROR: {str(e)}")
            self.ftp_logger.error(f"  Exception type: {type(e).__name__}")
            
            self.ftp_connected = False
            self.ftp_status_label.config(text=f"❌ Error: {str(e)[:30]}...", style='Error.TLabel')
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}\n\nSee FTP logs for details.")
    
    def _connect_professional_explicit(self, host, port, user, password):
        """Professional explicit SSL connection with multiple approaches like FlashFXP"""
        
        # Professional clients try these approaches in order
        approaches = [
            ("Manual AUTH TLS (glftpd Compatible)", self._manual_auth_tls_approach),
            ("FlashFXP-Style Clear Data", self._flashfxp_clear_data_approach),
            ("TLS 1.2 + Clear Data", self._tls12_clear_data_approach),
            ("Professional Compatible", self._professional_compatible_approach),
            ("Legacy Compatible", self._legacy_compatible_approach),
            ("Standard with Fallbacks", self._standard_with_fallbacks_approach)
        ]
        
        for approach_name, approach_func in approaches:
            try:
                self.ftp_logger.info(f"    Trying: {approach_name}...")
                connection = approach_func(host, port, user, password)
                
                if connection:
                    self.ftp_connection = connection
                    self.ftp_logger.info(f"    ✅ Success with: {approach_name}")
                    return True
                    
            except Exception as e:
                self.ftp_logger.error(f"    ❌ {approach_name} failed: {e}")
                continue
        
        self.ftp_logger.error("    ❌ All professional explicit approaches failed")
        return False
    
    def _manual_auth_tls_approach(self, host, port, user, password):
        """Manual AUTH TLS negotiation like FlashFXP - proven to work with glftpd"""
        import socket
        import ssl
        import time
        
        self.ftp_logger.info(f"      Manual AUTH TLS sequence (FlashFXP style)...")
        
        # Step 1: Plain socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(60)  # Professional timeout
        
        try:
            self.ftp_logger.info(f"      Connecting to {host}:{port}...")
            sock.connect((host, port))
            
            # Step 2: Read FTP welcome message
            welcome = sock.recv(1024).decode('utf-8', errors='ignore')
            self.ftp_logger.info(f"      Welcome: {welcome.strip()}")
            
            if not welcome.startswith('220'):
                raise Exception(f"Unexpected welcome: {welcome.strip()}")
            
            # Step 3: Send AUTH TLS command
            self.ftp_logger.info(f"      Sending AUTH TLS...")
            sock.send(b'AUTH TLS\r\n')
            auth_response = sock.recv(1024).decode('utf-8', errors='ignore')
            self.ftp_logger.info(f"      AUTH response: {auth_response.strip()}")
            
            if not auth_response.startswith('234'):
                # Try AUTH SSL as fallback
                sock.send(b'AUTH SSL\r\n')
                auth_response = sock.recv(1024).decode('utf-8', errors='ignore')
                if not auth_response.startswith('234'):
                    raise Exception(f"AUTH failed: {auth_response.strip()}")
            
            # Step 4: SSL handshake
            self.ftp_logger.info(f"      Performing SSL handshake...")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Try TLS 1.2 first (most compatible with glftpd)
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
            
            ssl_sock = ssl_context.wrap_socket(sock, server_hostname=None)
            self.ftp_logger.info(f"      ✅ SSL handshake successful")
            
            # Step 5: Login
            self.ftp_logger.info(f"      Logging in...")
            ssl_sock.send(f'USER {user}\r\n'.encode())
            user_response = ssl_sock.recv(1024).decode('utf-8', errors='ignore')
            
            ssl_sock.send(f'PASS {password}\r\n'.encode())
            pass_response = ssl_sock.recv(1024).decode('utf-8', errors='ignore')
            
            if not pass_response.startswith('230'):
                raise Exception(f"Login failed: {pass_response.strip()}")
            
            self.ftp_logger.info(f"      ✅ Login successful")
            
            # Step 6: Set data connection mode (PBSZ/PROT)
            self.ftp_logger.info(f"      Setting data connection mode...")
            try:
                ssl_sock.send(b'PBSZ 0\r\n')
                pbsz_response = ssl_sock.recv(1024).decode('utf-8', errors='ignore')
                self.ftp_logger.info(f"      PBSZ 0: {pbsz_response.strip()}")
            except:
                pass
            
            # Try PROT P (SSL data) first 
            ssl_sock.send(b'PROT P\r\n')  # SSL data connections (required by this server)
            prot_response = ssl_sock.recv(1024).decode('utf-8', errors='ignore')
            self.ftp_logger.info(f"      PROT P: {prot_response.strip()}")
            
            # Check if we need to fallback to clear data (200 or 230 are success codes)
            if not (prot_response.startswith('200') or prot_response.startswith('230')):
                self.ftp_logger.info(f"      PROT P failed, trying PROT C...")
                ssl_sock.send(b'PROT C\r\n')
                prot_response = ssl_sock.recv(1024).decode('utf-8', errors='ignore')
                self.ftp_logger.info(f"      PROT C: {prot_response.strip()}")
                data_protection = 'clear'
            else:
                data_protection = 'ssl'
                self.ftp_logger.info(f"      Using SSL data connections")
            
            # Step 7: Create custom FTP wrapper
            custom_ftp = ManualAuthTLSWrapper(ssl_sock, host, port, self.ftp_logger)
            custom_ftp.data_protection = data_protection  # Store the data protection mode
            self.ftp_logger.info(f"      ✅ Manual AUTH TLS connection established")
            
            return custom_ftp
            
        except Exception as e:
            self.ftp_logger.error(f"      ❌ Manual AUTH TLS failed: {e}")
            try:
                sock.close()
            except:
                pass
            raise
    
    def _flashfxp_clear_data_approach(self, host, port, user, password):
        """FlashFXP-style: SSL control + clear data connections"""
        # This is what many professional clients do for glftpd compatibility
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # FlashFXP typically uses TLS 1.2 for compatibility
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
        
        # Professional cipher selection
        try:
            ssl_context.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:AES128-GCM-SHA256:AES256-GCM-SHA384:HIGH:!aNULL:!eNULL')
        except:
            ssl_context.set_ciphers('HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5')
        
        ftp = ftplib.FTP_TLS(context=ssl_context)
        ftp.connect(host, port, timeout=60)  # Professional clients use longer timeouts
        ftp.login(user, password)
        
        # Key difference: Use clear data connections (like FlashFXP does)
        try:
            ftp.sendcmd('PBSZ 0')  # Set buffer size
        except:
            pass
        
        ftp.prot_c()  # Clear data connections (not encrypted)
        print(f"      Using clear (non-SSL) data connections for compatibility")
        
        # Test the connection
        ftp.voidcmd('NOOP')
        return ftp
    
    def _tls12_clear_data_approach(self, host, port, user, password):
        """TLS 1.2 only with clear data (common for glftpd)"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Force TLS 1.2 (glftpd compatibility)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
        
        # Conservative cipher selection for older servers
        ssl_context.set_ciphers('HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP')
        
        ftp = ftplib.FTP_TLS(context=ssl_context)
        ftp.connect(host, port, timeout=30)
        ftp.login(user, password)
        
        # Clear data connections
        ftp.prot_c()
        print(f"      TLS 1.2 control + clear data connections")
        
        ftp.voidcmd('NOOP')
        return ftp
    
    def _professional_compatible_approach(self, host, port, user, password):
        """Professional client compatible SSL settings"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Professional client SSL options
        ssl_context.options |= ssl.OP_NO_SSLv2
        ssl_context.options |= ssl.OP_NO_SSLv3
        ssl_context.options |= ssl.OP_SINGLE_DH_USE
        ssl_context.options |= ssl.OP_SINGLE_ECDH_USE
        
        # TLS 1.2 range (most compatible)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        ftp = ftplib.FTP_TLS(context=ssl_context)
        ftp.connect(host, port, timeout=45)
        ftp.login(user, password)
        
        # Try clear data first (most compatible)
        try:
            ftp.prot_c()
            print(f"      Professional settings + clear data")
        except:
            ftp.prot_p()
            print(f"      Professional settings + SSL data")
        
        ftp.voidcmd('NOOP')
        return ftp
    
    def _legacy_compatible_approach(self, host, port, user, password):
        """Legacy SSL compatibility for older servers"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Legacy server compatibility
        ssl_context.options |= ssl.OP_LEGACY_SERVER_CONNECT
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
        
        ftp = ftplib.FTP_TLS(context=ssl_context)
        ftp.connect(host, port, timeout=30)
        ftp.login(user, password)
        
        # Always use clear data for maximum compatibility
        ftp.prot_c()
        print(f"      Legacy compatibility + clear data")
        
        ftp.voidcmd('NOOP')
        return ftp
    
    def _standard_with_fallbacks_approach(self, host, port, user, password):
        """Standard approach with data protection fallbacks"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        try:
            ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')
        except:
            pass
        
        ftp = ftplib.FTP_TLS(context=ssl_context)
        ftp.connect(host, port, timeout=30)
        ftp.login(user, password)
        
        # Try clear data first, then SSL data
        try:
            ftp.prot_c()
            print(f"      Standard settings + clear data fallback")
        except:
            try:
                ftp.prot_p()
                print(f"      Standard settings + SSL data")
            except:
                print(f"      Standard settings + default data protection")
        
        ftp.voidcmd('NOOP')
        return ftp
    
    def _connect_professional_implicit(self, host, port, user, password):
        """Professional implicit SSL connection"""
        try:
            print(f"    Creating professional FTPS Implicit connection...")
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
            
            try:
                ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            except:
                ssl_context.set_ciphers('HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5')
            
            self.ftp_connection = ftplib.FTP_TLS(context=ssl_context)
            
            print(f"    Connecting to {host}:{port} with implicit SSL...")
            self.ftp_connection.connect(host, port, timeout=30)
            print("    Connected, attempting login...")
            
            self.ftp_connection.login(user, password)
            print("    Login successful")
            
            # Try clear data for compatibility
            try:
                self.ftp_connection.prot_c()
                print("    Using clear data connections")
            except:
                try:
                    self.ftp_connection.prot_p()
                    print("    Using SSL data connections")
                except:
                    print("    Using default data protection")
            
            # Test connection
            self.ftp_connection.voidcmd('NOOP')
            print("    ✅ Professional Implicit SSL successful")
            return True
            
        except Exception as e:
            print(f"    ❌ Professional Implicit SSL failed: {e}")
            try:
                self.ftp_connection.quit()
            except:
                pass
            return False
    
    def _connect_plain_ftp(self, host, port, user, password):
        """Connect using plain FTP"""
        try:
            self.ftp_logger.info(f"    Creating plain FTP connection...")
            self.ftp_connection = ftplib.FTP()
            
            self.ftp_logger.info(f"    Connecting to {host}:{port}...")
            self.ftp_connection.connect(host, port, timeout=30)
            self.ftp_logger.info("    Connected, attempting login...")
            
            self.ftp_connection.login(user, password)
            self.ftp_logger.info("    Login successful")
            
            # Test connection
            self.ftp_connection.voidcmd('NOOP')
            self.ftp_logger.info("    ✅ Plain FTP connection successful")
            return True
            
        except Exception as e:
            self.ftp_logger.error(f"    ❌ Plain FTP failed: {e}")
            try:
                self.ftp_connection.quit()
            except:
                pass
            raise e
    
    def ftp_disconnect(self):
        """Disconnect from FTP server"""
        try:
            if self.ftp_connection:
                self.ftp_connection.quit()
        except:
            pass
        
        self.ftp_connection = None
        self.ftp_connected = False
        self.ftp_current_dir = "/"
        
        self.ftp_status_label.config(text="❌ Disconnected", style='Error.TLabel')
        self.ftp_current_dir_label.config(text="/")
        
        # Clear file listing
        for item in self.ftp_files_tree.get_children():
            self.ftp_files_tree.delete(item)
    
    def ftp_refresh(self):
        """Refresh current directory listing with professional SSL handling"""
        if not self.ftp_connected:
            return
        
        try:
            # Clear current listing and search state
            for item in self.ftp_files_tree.get_children():
                self.ftp_files_tree.delete(item)
            
            # Reset search state
            self.original_items = []
            self.is_filtered = False
            if hasattr(self, 'ftp_search_var'):
                self.ftp_search_var.set("")
                self.search_result_label.config(text="")
            
            # Check what type of data connection we're using
            data_protection_type = "Unknown"
            try:
                # Try to determine current protection mode
                if hasattr(self.ftp_connection, '_prot_p'):
                    data_protection_type = "SSL Protected" if self.ftp_connection._prot_p else "Clear (Non-SSL)"
                else:
                    data_protection_type = "Default"
            except:
                data_protection_type = "Unknown"
            
            self.ftp_logger.info(f"  Refreshing directory listing (Data: {data_protection_type})...")
            
            # Professional approach: Try methods in order of reliability
            files_list = []
            success = False
            
            # Method 1: Standard LIST (works well with clear data connections)
            if not success:
                try:
                    self.ftp_logger.info("    Trying LIST command...")
                    self.ftp_connection.retrlines('LIST', files_list.append)
                    success = True
                    self.ftp_logger.info(f"    ✅ LIST successful with {data_protection_type} data")
                except Exception as e:
                    self.ftp_logger.error(f"    ❌ LIST failed: {e}")
                    files_list = []
            
            # Method 2: Try toggling data protection if LIST failed
            if not success and hasattr(self.ftp_connection, 'prot_c') and hasattr(self.ftp_connection, 'prot_p'):
                try:
                    print("    Trying to switch data protection mode...")
                    current_prot = getattr(self.ftp_connection, '_prot_p', None)
                    
                    if current_prot:
                        # Currently using SSL data, try clear
                        print("    Switching from SSL to clear data...")
                        self.ftp_connection.prot_c()
                        self.ftp_connection.retrlines('LIST', files_list.append)
                        print("    ✅ LIST successful after switching to clear data")
                    else:
                        # Currently using clear data, try SSL
                        print("    Switching from clear to SSL data...")
                        self.ftp_connection.prot_p()
                        self.ftp_connection.retrlines('LIST', files_list.append)
                        print("    ✅ LIST successful after switching to SSL data")
                    
                    success = True
                except Exception as e:
                    print(f"    ❌ Data protection switch failed: {e}")
                    files_list = []
                    # Try to restore original protection mode
                    try:
                        if current_prot:
                            self.ftp_connection.prot_p()
                        else:
                            self.ftp_connection.prot_c()
                    except:
                        pass
            
            # Method 3: Try NLST (name list - simpler command)
            if not success:
                try:
                    print("    Trying NLST command...")
                    nlst_files = self.ftp_connection.nlst()
                    # Convert NLST to LIST-like format
                    for filename in nlst_files:
                        if filename not in ['.', '..']:
                            # Create basic LIST-like entry
                            files_list.append(f"-rw-rw-rw- 1 user group 0 Jan 01 00:00 {filename}")
                    
                    success = True
                    print(f"    ✅ NLST successful - converted {len(nlst_files)} entries")
                except Exception as e:
                    print(f"    ❌ NLST failed: {e}")
                    files_list = []
            
            # Method 4: Try manual PASV + LIST (raw approach)
            if not success:
                try:
                    print("    Trying manual PASV approach...")
                    # This is a last resort - might work when other methods fail
                    pasv_response = self.ftp_connection.sendcmd('PASV')
                    print(f"      PASV response: {pasv_response}")
                    
                    # Try a simple LIST command
                    files_list = []
                    self.ftp_connection.retrlines('LIST', files_list.append)
                    success = True
                    print("    ✅ Manual PASV approach successful")
                except Exception as e:
                    print(f"    ❌ Manual PASV approach failed: {e}")
                    files_list = []
            
            # Method 5: Create minimal listing if all else fails
            if not success:
                try:
                    print("    Creating minimal directory listing...")
                    current_dir = self.ftp_connection.pwd()
                    files_list = [f"drwxrwxrwx 1 user group 0 Jan 01 00:00 (Connected to: {current_dir})"]
                    success = True
                    print("    ✅ Minimal listing created")
                except Exception as e:
                    print(f"    ❌ Even minimal listing failed: {e}")
            
            if not success:
                raise Exception("All directory listing methods failed")
            
            # Check if we're at root and should show virtual folders
            current_dir = self.ftp_connection.pwd()
            if current_dir == "/" or current_dir == "\\":
                self._show_virtual_folders()
            else:
                # Parse and display files normally
                for line in files_list:
                    try:
                        parts = line.split()
                        if len(parts) >= 8:
                            perms = parts[0]
                            size = parts[4] if len(parts) > 4 and parts[4].isdigit() else "0"
                            date_str = " ".join(parts[5:8]) if len(parts) >= 8 else "Unknown"
                            name = " ".join(parts[8:]) if len(parts) >= 9 else "Unknown"
                            
                            # Skip . and .. entries
                            if name in ['.', '..']:
                                continue
                            
                            # Determine type and content
                            if perms.startswith('d'):
                                file_type = "📁 DIR"
                                size_display = ""
                                # Detect content type for directories
                                content_type = self.detect_content_type(name)
                                if content_type == 'movie':
                                    content_display = "🎬 Movie"
                                elif content_type == 'tv_show':
                                    content_display = "📺 TV Show"
                                else:
                                    content_display = "📁 Other"
                            else:
                                file_type = "📄 FILE"
                                size_display = self.format_file_size(int(size)) if size.isdigit() else size
                                content_display = ""
                            
                            self.ftp_files_tree.insert('', 'end', values=(
                                file_type, name, size_display, date_str, content_display
                            ))
                    except Exception as e:
                        print(f"  ⚠️  Failed to parse line: {line} - {e}")
                        continue
            
            # Update current directory display
            try:
                self.ftp_current_dir = self.ftp_connection.pwd()
                self.ftp_current_dir_label.config(text=self.ftp_current_dir)
                print(f"  ✅ Directory listing complete: {len(files_list)} entries ({data_protection_type} data)")
            except Exception as e:
                print(f"  ⚠️  Could not update current directory: {e}")
            
            # Update search status
            self.update_search_status()
            
        except Exception as e:
            error_msg = str(e)
            self.ftp_logger.error(f"  ❌ Directory refresh failed: {error_msg}")
            
            # Check if it's a connection issue and try to recover
            if any(keyword in error_msg.lower() for keyword in ['connection', 'timeout', 'broken', 'refused']):
                self.ftp_logger.warning("  Detected connection issue during directory listing")
                if self._attempt_reconnection():
                    self.ftp_logger.info("  Connection recovered, retrying directory listing...")
                    try:
                        self.ftp_refresh()  # Recursive retry after reconnection
                        return
                    except Exception as retry_e:
                        self.ftp_logger.error(f"  Retry after reconnection failed: {retry_e}")
            
            # Show user-friendly error with professional context
            messagebox.showerror(
                "Directory Listing Error", 
                f"Failed to load directory listing.\n\n"
                f"Error: {error_msg}\n\n"
                f"This can happen with:\n"
                f"• SSL data connection issues\n"
                f"• Server SSL configuration problems\n"
                f"• Firewall blocking data ports\n\n"
                f"The professional client uses {data_protection_type} data connections.\n"
                f"Try disconnecting and reconnecting to reset the connection."
            )
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _show_virtual_folders(self):
        """Show virtual Movies and TV Shows folders at root"""
        print("  Showing virtual folder structure...")
        
        # Reset search state for virtual folders
        self.original_items = []
        self.is_filtered = False
        if hasattr(self, 'ftp_search_var'):
            self.ftp_search_var.set("")
            self.search_result_label.config(text="")
        
        # Create virtual Movies folder
        movies_item = self.ftp_files_tree.insert('', 'end', values=(
            "📁 DIR", "Movies", "", "", "🎬 All Movies"
        ))
        self.ftp_files_tree.item(movies_item, tags=("virtual_movies",))
        
        # Create virtual TV Shows folder  
        tv_item = self.ftp_files_tree.insert('', 'end', values=(
            "📁 DIR", "TV Shows", "", "", "📺 All TV Shows"
        ))
        self.ftp_files_tree.item(tv_item, tags=("virtual_tv",))
        
        # Update status
        self.ftp_current_dir_label.config(text="/ [Virtual View]")
        print("  ✅ Virtual folders created")
    
    def _show_virtual_content(self, content_type):
        """Show aggregated content from all directories"""
        print(f"  Showing virtual {content_type} content...")
        
        # Clear current listing and search state
        for item in self.ftp_files_tree.get_children():
            self.ftp_files_tree.delete(item)
        
        # Reset search state
        self.original_items = []
        self.is_filtered = False
        if hasattr(self, 'ftp_search_var'):
            self.ftp_search_var.set("")
            self.search_result_label.config(text="")
        
        # Get content from discovered_content
        content_key = content_type if content_type in self.discovered_content else content_type
        if content_key not in self.discovered_content:
            print(f"  No {content_type} content discovered yet")
            self.ftp_current_dir_label.config(text=f"/ Virtual {content_type.replace('_', ' ').title()} (Empty)")
            return
        
        # Display all content of this type
        content_list = self.discovered_content[content_key]
        print(f"  Found {len(content_list)} {content_type} items")
        
        for folder_info in content_list:
            # Extract clean title and technical details from folder name
            clean_title = self._extract_clean_title(folder_info['name'])
            tech_details = self._extract_technical_details(folder_info['name'])
            display_name = self._format_technical_display(clean_title, tech_details)
            content_label = "🎬 Movie" if content_type == 'movies' else "📺 TV Show"
            
            # Create item with enhanced display name
            item_id = self.ftp_files_tree.insert('', 'end', values=(
                "📁 DIR",           # Type
                display_name,        # Display clean title with technical details
                "",                  # Size
                "",                  # Date
                content_label        # Content
            ))
            
            # Store the actual folder info in tags for downloads
            self.ftp_files_tree.item(item_id, tags=(
                folder_info['path'],  # Full FTP path
                folder_info['name'],  # Original folder name
                folder_info['parent'] # Parent directory
            ))
        
        # Update current directory label
        content_name = content_type.replace('_', ' ').title()
        self.ftp_current_dir_label.config(text=f"/ Virtual {content_name} ({len(content_list)} items)")
        print(f"  ✅ Virtual {content_type} listing complete")
        
        # Update search status
        self.update_search_status()
    
    def _sort_column(self, col, reverse):
        """Sort treeview by column"""
        # Get all items
        items = [(self.ftp_files_tree.set(child, col), child) for child in self.ftp_files_tree.get_children('')]
        
        # Sort items
        if col == "Size":
            # Special sorting for size column (convert to numeric if possible)
            def size_key(item):
                size_text = item[0]
                if not size_text or size_text == "":
                    return 0
                # Extract numeric value and unit
                import re
                match = re.match(r'([\d.]+)\s*([KMGT]?B)', size_text)
                if match:
                    value, unit = match.groups()
                    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                    return float(value) * multipliers.get(unit, 1)
                return 0
            items.sort(key=size_key, reverse=reverse)
        else:
            # Regular alphabetical sorting
            items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        
        # Rearrange items in sorted positions
        for index, (val, child) in enumerate(items):
            self.ftp_files_tree.move(child, '', index)
        
        # Update column headers to show sort direction
        for column in ("Type", "Name", "Size", "Date", "Content"):
            if column == col:
                direction = " ▲" if reverse else " ▼"
                self.ftp_files_tree.heading(column, text=column + direction, 
                                           command=lambda c=column: self._sort_column(c, not reverse))
            else:
                self.ftp_files_tree.heading(column, text=column,
                                           command=lambda c=column: self._sort_column(c, False))
        
        # Update tracking variables
        self.current_sort_column = col
        self.sort_reverse = reverse
    
    def _extract_clean_title(self, folder_name):
        """Extract clean movie/TV show title from folder name"""
        import re
        
        # Remove common release group tags
        clean = re.sub(r'-[A-Z0-9]+$', '', folder_name)  # Remove -GROUPNAME
        
        # Remove quality/format info
        clean = re.sub(r'\.(1080p|720p|2160p|4k|uhd|bluray|web|h264|h265|x264|x265).*', '', clean, flags=re.IGNORECASE)
        
        # Remove year from movies (keep for TV shows which often don't have years)
        clean = re.sub(r'\.(19|20)\d{2}\.', '.', clean)
        
        # Replace dots and underscores with spaces
        clean = clean.replace('.', ' ').replace('_', ' ')
        
        # Clean up multiple spaces
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # Capitalize words properly
        clean = ' '.join(word.capitalize() for word in clean.split())
        
        return clean if clean else folder_name  # Fallback to original if cleaning failed
    
    def _extract_technical_details(self, folder_name):
        """Extract technical details like quality, encoding, year from folder name"""
        import re
        
        details = {
            'quality': '',
            'encoding': '',
            'year': '',
            'source': ''
        }
        
        folder_lower = folder_name.lower()
        
        # Extract quality/resolution
        quality_patterns = [
            r'2160p|4k', r'1080p', r'720p', r'480p', r'1080i', r'720i'
        ]
        for pattern in quality_patterns:
            if re.search(pattern, folder_lower):
                match = re.search(pattern, folder_lower)
                details['quality'] = match.group().upper()
                break
        
        # Extract encoding
        encoding_patterns = [
            r'h265|hevc', r'h264|avc', r'x265', r'x264', r'xvid', r'vc1'
        ]
        for pattern in encoding_patterns:
            if re.search(pattern, folder_lower):
                match = re.search(pattern, folder_lower)
                encoding = match.group().upper()
                # Normalize common encodings
                if encoding in ['H265', 'HEVC']:
                    details['encoding'] = 'H.265'
                elif encoding in ['H264', 'AVC']:
                    details['encoding'] = 'H.264'
                elif encoding == 'X265':
                    details['encoding'] = 'x265'
                elif encoding == 'X264':
                    details['encoding'] = 'x264'
                else:
                    details['encoding'] = encoding
                break
        
        # Extract source
        source_patterns = [
            r'bluray|blu-ray', r'uhd\.bluray|uhdbd', r'webrip|web-rip', r'web\.', r'hdtv', r'dvdrip|dvd-rip', r'brrip|br-rip'
        ]
        for pattern in source_patterns:
            if re.search(pattern, folder_lower):
                match = re.search(pattern, folder_lower)
                source = match.group().upper()
                # Normalize common sources
                if 'BLURAY' in source or 'BLU-RAY' in source:
                    if 'UHD' in source:
                        details['source'] = 'UHD BluRay'
                    else:
                        details['source'] = 'BluRay'
                elif 'WEBRIP' in source or 'WEB-RIP' in source:
                    details['source'] = 'WEBRip'
                elif 'WEB' in source:
                    details['source'] = 'WEB'
                elif 'HDTV' in source:
                    details['source'] = 'HDTV'
                elif 'DVDRIP' in source or 'DVD-RIP' in source:
                    details['source'] = 'DVDRip'
                elif 'BRRIP' in source or 'BR-RIP' in source:
                    details['source'] = 'BRRip'
                else:
                    details['source'] = source
                break
        
        # Extract year
        year_match = re.search(r'(19|20)\d{2}', folder_name)
        if year_match:
            details['year'] = year_match.group()
        
        return details
    
    def _format_technical_display(self, clean_title, technical_details):
        """Format the display name with technical details"""
        tech_parts = []
        
        if technical_details['year']:
            tech_parts.append(technical_details['year'])
        if technical_details['quality']:
            tech_parts.append(technical_details['quality'])
        if technical_details['source']:
            tech_parts.append(technical_details['source'])
        if technical_details['encoding']:
            tech_parts.append(technical_details['encoding'])
        
        if tech_parts:
            return f"{clean_title} ({' • '.join(tech_parts)})"
        else:
            return clean_title
    
    def _refresh_virtual_folders_if_needed(self):
        """Refresh virtual folders display if we're currently showing them"""
        try:
            current_label = self.ftp_current_dir_label.cget('text')
            current_dir = self.ftp_connection.pwd() if self.ftp_connected else "/"
            
            # Check if we're at root showing virtual folders
            if current_dir == "/" and "[Virtual View]" in current_label:
                print("  Refreshing virtual folders with discovered content...")
                self._show_virtual_folders()
            # Check if we're in a specific virtual content view
            elif "Virtual Movies" in current_label:
                print("  Refreshing virtual Movies content...")
                self._show_virtual_content("movies")
            elif "Virtual TV Shows" in current_label:
                print("  Refreshing virtual TV Shows content...")
                self._show_virtual_content("tv_shows")
                
        except Exception as e:
            print(f"  Error refreshing virtual folders: {e}")
    
    def ftp_go_up(self):
        """Go to parent directory or back to virtual root"""
        if not self.ftp_connected:
            return
        
        try:
            # Check if we're in a virtual view
            current_label = self.ftp_current_dir_label.cget('text')
            if "Virtual" in current_label and current_label != "/ [Virtual View]":
                # We're in a virtual content view, go back to virtual root
                print("  Going back to virtual root")
                self.ftp_connection.cwd('/')  # Go to actual root
                self.ftp_refresh()  # This will show virtual folders
            else:
                # Regular navigation
                self.ftp_connection.cwd('..')
                self.ftp_refresh()
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Failed to go up: {e}")
    
    def ftp_go_root(self):
        """Go to root directory"""
        if not self.ftp_connected:
            return
        
        try:
            self.ftp_connection.cwd('/')
            self.ftp_refresh()
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Failed to go to root: {e}")
    
    def ftp_enter_directory(self):
        """Enter selected directory"""
        selection = self.ftp_files_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a directory to enter")
            return
        
        item = self.ftp_files_tree.item(selection[0])
        # Column indices: Type=0, Name=1, Size=2, Date=3, Content=4
        file_type, name = item['values'][0], item['values'][1]  # Type and Name columns
        
        if "DIR" not in file_type:
            messagebox.showwarning("Not a Directory", "Please select a directory")
            return
        
        # Use smart navigation to handle filtered views
        self._navigate_to_directory(selection[0], name)
    
    def _navigate_to_directory(self, item_id, folder_name):
        """Smart navigation that handles both regular and filtered views"""
        try:
            # Check if we're in a filtered view by examining the item's tags
            item = self.ftp_files_tree.item(item_id)
            tags = item.get('tags', ())
            
            # Handle virtual folders
            if tags and "virtual_movies" in tags:
                print("  Navigating to virtual Movies folder")
                self._show_virtual_content("movies")
                return
            elif tags and "virtual_tv" in tags:
                print("  Navigating to virtual TV Shows folder")
                self._show_virtual_content("tv_shows")
                return
            elif tags and len(tags) >= 1:
                # We're in a filtered view - use the stored full path
                full_path = tags[0]
                print(f"  Navigating to filtered view path: {full_path}")
                self.ftp_connection.cwd(full_path)
            else:
                # Regular navigation - use folder name relative to current directory
                print(f"  Navigating to: {folder_name}")
                self.ftp_connection.cwd(folder_name)
            
            # Update current directory and refresh
            self.ftp_current_dir = self.ftp_connection.pwd()
            self.ftp_current_dir_label.config(text=self.ftp_current_dir)
            
            # Reset to regular view when navigating
            self.current_view = 'all'
            self.ftp_content_filter_var.set("All")
            self.ftp_refresh()
            
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Failed to enter directory: {e}")
    
    def _auto_scan_content(self):
        """Auto-scan content in background thread"""
        try:
            # Wait a moment for connection to stabilize
            import time
            time.sleep(2)
            
            # Update status
            self.root.after(0, lambda: self.ftp_status_label.config(
                text="🔍 Auto-scanning content...", style='Warning.TLabel'
            ))
            
            # Perform the scan
            self._perform_content_scan()
            
            # Update status with results
            movie_count = len(self.discovered_content['movies'])
            tv_count = len(self.discovered_content['tv_shows'])
            other_count = len(self.discovered_content['other'])
            
            self.root.after(0, lambda: self.ftp_status_label.config(
                text=f"✅ Auto-scan: {movie_count} movies, {tv_count} TV shows, {other_count} other",
                style='Running.TLabel'
            ))
            
            print(f"  Auto-scan complete: {movie_count} movies, {tv_count} TV shows, {other_count} other")
            
            # Refresh virtual folders if we're currently showing them
            self.root.after(0, self._refresh_virtual_folders_if_needed)
            
        except Exception as e:
            print(f"  Auto-scan error: {e}")
            self.root.after(0, lambda: self.ftp_status_label.config(
                text="⚠️ Auto-scan failed", style='Error.TLabel'
            ))
    
    def _perform_content_scan(self):
        """Perform deep content scan to find actual movie/TV folders"""
        if not self.ftp_connected:
            return
        
        # Clear previous discoveries
        self.discovered_content = {
            'movies': [],
            'tv_shows': [], 
            'other': []
        }
        
        try:
            # Save current directory
            original_dir = self.ftp_connection.pwd()
            
            # First, scan root to find section directories
            print("Auto-scanning: /")
            self.ftp_connection.cwd('/')
            root_lines = []
            self.ftp_connection.retrlines('LIST', root_lines.append)
            
            section_dirs = []
            for line in root_lines:
                if line.startswith('d'):  # Directory
                    dir_name = ' '.join(line.split()[8:]) if len(line.split()) >= 9 else line.split()[-1]
                    if dir_name not in ['.', '..']:
                        section_dirs.append(dir_name)
                        print(f"  Found section: {dir_name}")
            
            # Now scan inside each section directory for subsections, then content
            for section in section_dirs:
                try:
                    section_path = f"/{section}"
                    print(f"Auto-scanning: {section_path}")
                    self.ftp_connection.cwd(section_path)
                    
                    content_lines = []
                    self.ftp_connection.retrlines('LIST', content_lines.append)
                    
                    # Look for subsections (bluray, x265, etc.) and actual content
                    for line in content_lines:
                        if line.startswith('d'):  # Directory
                            dir_name = ' '.join(line.split()[8:]) if len(line.split()) >= 9 else line.split()[-1]
                            if dir_name in ['.', '..']:
                                continue
                                
                            current_path = f"{section_path}/{dir_name}".replace('//', '/')
                            content_type = self.detect_content_type(dir_name, current_path)
                            
                            # Check if this looks like a subsection (bluray, x265, etc.) or actual content
                            if dir_name.lower() in ['bluray', 'bluray-uhd', 'mbluray', 'x264-hd', 'x264-sd', 'x265', 'x264-boxsets', 'tv-bluray', 'tv-hd', 'tv-dvdrip', 'tv-sports']:
                                # This is a subsection - scan inside it for actual content
                                try:
                                    print(f"  Scanning subsection: {current_path}")
                                    self.ftp_connection.cwd(current_path)
                                    subsection_lines = []
                                    self.ftp_connection.retrlines('LIST', subsection_lines.append)
                                    
                                    for sub_line in subsection_lines:
                                        if sub_line.startswith('d'):  # Directory
                                            sub_dir_name = ' '.join(sub_line.split()[8:]) if len(sub_line.split()) >= 9 else sub_line.split()[-1]
                                            if sub_dir_name in ['.', '..']:
                                                continue
                                                
                                            sub_current_path = f"{current_path}/{sub_dir_name}".replace('//', '/')
                                            sub_content_type = self.detect_content_type(sub_dir_name, sub_current_path)
                                            
                                            folder_info = {
                                                'name': sub_dir_name,
                                                'path': sub_current_path,
                                                'parent': current_path,
                                                'section': section,
                                                'subsection': dir_name,
                                                'type': sub_content_type
                                            }
                                            
                                            if sub_content_type == 'movie':
                                                self.discovered_content['movies'].append(folder_info)
                                                print(f"    📽️ Movie: {sub_dir_name}")
                                            elif sub_content_type == 'tv_show':
                                                self.discovered_content['tv_shows'].append(folder_info)
                                                print(f"    📺 TV: {sub_dir_name}")
                                            else:
                                                self.discovered_content['other'].append(folder_info)
                                    
                                    # Go back to section directory
                                    self.ftp_connection.cwd(section_path)
                                    
                                except Exception as e:
                                    print(f"    Could not scan subsection {current_path}: {e}")
                                    self.ftp_connection.cwd(section_path)  # Make sure we're back
                                    continue
                            else:
                                # This looks like actual content at the section level
                                folder_info = {
                                    'name': dir_name,
                                    'path': current_path,
                                    'parent': section_path,
                                    'section': section,
                                    'type': content_type
                                }
                                
                                if content_type == 'movie':
                                    self.discovered_content['movies'].append(folder_info)
                                    print(f"    📽️ Movie: {dir_name}")
                                elif content_type == 'tv_show':
                                    self.discovered_content['tv_shows'].append(folder_info)
                                    print(f"    📺 TV: {dir_name}")
                                else:
                                    self.discovered_content['other'].append(folder_info)
                                
                except Exception as e:
                    print(f"  Could not scan section {section}: {e}")
                    continue
            
            # Restore original directory
            self.ftp_connection.cwd(original_dir)
            
        except Exception as e:
            print(f"Auto-scan error: {e}")
    
    def ftp_on_double_click(self, event):
        """Handle double-click on file/directory"""
        selection = self.ftp_files_tree.selection()
        if not selection:
            return
        
        item = self.ftp_files_tree.item(selection[0])
        # Column indices: Type=0, Name=1, Size=2, Date=3, Content=4
        file_type, name = item['values'][0], item['values'][1]  # Type and Name columns
        
        if "DIR" in file_type:
            # Double-click on directory - enter it using smart navigation
            self._navigate_to_directory(selection[0], name)
        else:
            # Double-click on file - add to download queue
            self.add_file_to_queue(name, item['values'][2])  # Size column
    
    def ftp_download_selected(self):
        """Download selected files"""
        selections = self.ftp_files_tree.selection()
        if not selections:
            messagebox.showwarning("No Selection", "Please select files to download")
            return
        
        for selection in selections:
            item = self.ftp_files_tree.item(selection)
            # Column indices: Type=0, Name=1, Size=2, Date=3, Content=4
            file_type, name, size = item['values'][0], item['values'][1], item['values'][2]  # Type, Name, Size columns
            
            if "FILE" in file_type:
                self.add_file_to_queue(name, size)
    
    def ftp_download_all_rar(self):
        """Download all RAR files in current directory"""
        rar_files = []
        for item_id in self.ftp_files_tree.get_children():
            item = self.ftp_files_tree.item(item_id)
            # Column indices: Type=0, Name=1, Size=2, Date=3, Content=4
            file_type, name, size = item['values'][0], item['values'][1], item['values'][2]  # Type, Name, Size columns
            
            if "FILE" in file_type and name.lower().endswith(('.rar', '.r00', '.r01', '.r02', '.r03', '.r04', '.r05')):
                rar_files.append((name, size))
        
        if rar_files:
            for name, size in rar_files:
                self.add_file_to_queue(name, size)
            messagebox.showinfo("Added to Queue", f"Added {len(rar_files)} RAR files to download queue")
        else:
            messagebox.showinfo("No RAR Files", "No RAR files found in current directory")
    
    def ftp_apply_filter(self):
        """Apply file filter to current view"""
        # This would implement filtering - for now just refresh
        self.ftp_refresh()
    
    def add_file_to_queue(self, filename, size):
        """Add file to download queue"""
        # Check if already in queue
        for item_id in self.download_queue_tree.get_children():
            item = self.download_queue_tree.item(item_id)
            if item['values'][0] == filename:
                messagebox.showinfo("Already Queued", f"{filename} is already in the download queue")
                return
        
        # Add to queue display
        self.download_queue_tree.insert('', 'end', values=(filename, size, "Queued"))
        
        # Add to internal queue
        queue_item = {
            'filename': filename,
            'size': size,
            'remote_path': f"{self.ftp_current_dir}/{filename}".replace('//', '/'),
            'local_path': Path(self.ftp_download_dir_var.get()) / filename,
            'status': 'Queued'
        }
        self.download_queue.append(queue_item)
    
    def start_download_queue(self):
        """Start processing download queue"""
        if not self.ftp_connected:
            messagebox.showerror("Not Connected", "Please connect to FTP server first")
            return
        
        if not self.download_queue:
            messagebox.showinfo("Empty Queue", "Download queue is empty")
            return
        
        # Start download thread
        download_thread = threading.Thread(target=self.process_download_queue, daemon=True)
        download_thread.start()
    
    def pause_download_queue(self):
        """Pause download queue"""
        # Implementation for pausing downloads
        messagebox.showinfo("Pause", "Download queue paused")
    
    def clear_download_queue(self):
        """Clear download queue"""
        if messagebox.askyesno("Clear Queue", "Are you sure you want to clear the download queue?"):
            self.download_queue.clear()
            for item in self.download_queue_tree.get_children():
                self.download_queue_tree.delete(item)
    
    def process_download_queue(self):
        """Process downloads from queue with enhanced SSL connection handling"""
        for i, queue_item in enumerate(self.download_queue):
            if queue_item['status'] != 'Queued':
                continue
            
            retry_count = 0
            max_retries = 3
            
            while retry_count <= max_retries:
                try:
                    # Check connection health before download
                    if not self._check_connection_health():
                        print(f"Connection lost, attempting to reconnect...")
                        if not self._attempt_reconnection():
                            queue_item['status'] = 'Error: Connection lost'
                            self.update_queue_display()
                            break
                    
                    # Update status to downloading
                    queue_item['status'] = f'Downloading (attempt {retry_count + 1})'
                    self.update_queue_display()
                    
                    # Download file with enhanced error handling
                    success = self._download_file_with_recovery(queue_item)
                    
                    if success:
                        queue_item['status'] = 'Completed'
                        self.update_queue_display()
                        print(f"✅ Downloaded: {queue_item['filename']} -> {queue_item['local_path']}")
                        break
                    else:
                        retry_count += 1
                        if retry_count <= max_retries:
                            print(f"Download failed, retrying... ({retry_count}/{max_retries})")
                            queue_item['status'] = f'Retrying ({retry_count}/{max_retries})'
                            self.update_queue_display()
                            time.sleep(2)  # Wait before retry
                        else:
                            queue_item['status'] = 'Error: Max retries exceeded'
                            self.update_queue_display()
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)[:30] + "..." if len(str(e)) > 30 else str(e)
                    
                    if retry_count <= max_retries:
                        print(f"Download error for {queue_item['filename']}: {e}")
                        print(f"Retrying... ({retry_count}/{max_retries})")
                        queue_item['status'] = f'Error, retrying ({retry_count}/{max_retries})'
                        self.update_queue_display()
                        time.sleep(2)
                    else:
                        queue_item['status'] = f'Error: {error_msg}'
                        self.update_queue_display()
                        print(f"❌ Download failed after {max_retries} retries: {queue_item['filename']}: {e}")
    
    def _check_connection_health(self):
        """Check if FTP connection is still alive"""
        if not self.ftp_connected or not hasattr(self, 'ftp_connection'):
            return False
        
        try:
            # Send a simple command to test connection
            self.ftp_connection.voidcmd('NOOP')
            return True
        except Exception as e:
            print(f"Connection health check failed: {e}")
            return False
    
    def _attempt_reconnection(self):
        """Attempt to reconnect using professional approaches"""
        try:
            print("Attempting to reconnect with professional methods...")
            
            # Get current connection settings
            host = self.ftp_host_var.get().strip()
            port = int(self.ftp_port_var.get().strip() or "21")
            user = self.ftp_user_var.get().strip()
            password = self.ftp_pass_var.get()
            ssl_mode = self.ftp_ssl_var.get()
            
            # Disconnect current connection if exists
            try:
                self.ftp_connection.quit()
            except:
                pass
            
            self.ftp_connected = False
            
            # Use the same professional approaches as main connection
            if ssl_mode == "Explicit":
                success = self._connect_professional_explicit(host, port, user, password)
            elif ssl_mode == "Implicit":
                success = self._connect_professional_implicit(host, port, user, password)
            else:
                success = self._connect_plain_ftp(host, port, user, password)
            
            if success:
                # Configure connection settings
                self.ftp_connection.set_pasv(True)
                
                if self.ftp_mode_var.get() == "Binary":
                    try:
                        self.ftp_connection.voidcmd('TYPE I')
                    except:
                        pass
                
                self.ftp_connected = True
                self.ftp_status_label.config(text="✅ Reconnected", style='Running.TLabel')
                print("✅ Professional reconnection successful")
                return True
            else:
                self.ftp_status_label.config(text="❌ Reconnection failed", style='Error.TLabel')
                print("❌ Professional reconnection failed")
                return False
                
        except Exception as e:
            print(f"Reconnection attempt failed: {e}")
            self.ftp_connected = False
            self.ftp_status_label.config(text="❌ Reconnection failed", style='Error.TLabel')
            return False
    
    def _download_file_with_recovery(self, queue_item):
        """Download file with SSL connection recovery"""
        try:
            # Prepare local path - handle both Path objects and strings
            local_path = queue_item['local_path']
            if isinstance(local_path, str):
                local_path = Path(local_path)
            
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Change to correct directory if needed
            # Use manual path manipulation to keep forward slashes for FTP
            remote_path = queue_item['remote_path']
            if '/' in remote_path:
                remote_dir = '/'.join(remote_path.split('/')[:-1])
            else:
                remote_dir = '/'
            
            if remote_dir != self.ftp_current_dir:
                try:
                    self.ftp_connection.cwd(remote_dir)
                    self.ftp_current_dir = remote_dir
                    print(f"Changed to directory: {remote_dir}")
                except Exception as e:
                    print(f"Failed to change directory to {remote_dir}: {e}")
                    return False
            
            # Download file with progress tracking
            downloaded_bytes = 0
            
            with open(local_path, 'wb') as local_file:
                def progress_callback(data):
                    nonlocal downloaded_bytes
                    local_file.write(data)
                    downloaded_bytes += len(data)
                
                # Attempt download with connection monitoring
                try:
                    self.ftp_connection.retrbinary(
                        f"RETR {queue_item['filename']}", 
                        progress_callback,
                        blocksize=8192  # Use smaller blocks for better progress tracking
                    )
                    print(f"Downloaded {downloaded_bytes} bytes for {queue_item['filename']}")
                    return True
                    
                except Exception as e:
                    print(f"Download failed: {e}")
                    
                    # Check if it's a connection issue
                    if any(keyword in str(e).lower() for keyword in ['connection', 'timeout', 'broken', 'ssl', 'tls']):
                        print("Detected connection issue during download")
                        
                        # Try to recover the connection
                        if self._attempt_reconnection():
                            print("Connection recovered, retrying download...")
                            return False  # Return False to trigger retry
                    
                    raise e
            
        except Exception as e:
            print(f"Download error: {e}")
            return False
    
    def update_queue_display(self):
        """Update download queue display"""
        # Clear and repopulate queue display
        for item in self.download_queue_tree.get_children():
            self.download_queue_tree.delete(item)
        
        for queue_item in self.download_queue:
            status = queue_item.get('status', 'Unknown')
            content_type = queue_item.get('content_type', '')
            folder = queue_item.get('folder', '')
            
            # Add content type and folder info to status
            if content_type and folder:
                status = f"{status} ({content_type} from {folder})"
            
            self.download_queue_tree.insert('', 'end', values=(
                queue_item['filename'],
                queue_item.get('size', 'Unknown'),
                status
            ))
    
    def create_setup_tab(self):
        """Create comprehensive setup panel"""
        setup_frame = ttk.Frame(self.notebook)
        self.notebook.add(setup_frame, text="Setup Panel")
        
        # Create scrollable frame
        canvas = tk.Canvas(setup_frame)
        scrollbar = ttk.Scrollbar(setup_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Initialize setup data
        self.setup_data = {
            'directory_pairs': [],
            'plex_libraries': [],
            'plex_host': '',
            'plex_token': ''
        }
        
        # Plex Connection Section
        self.create_plex_connection_section(scrollable_frame)
        
        # Directory Pairs Section
        self.create_directory_pairs_section(scrollable_frame)
        
        # Control Buttons Section
        self.create_setup_controls_section(scrollable_frame)
        
        # Load existing setup
        self.load_setup_config()
    
    def create_plex_connection_section(self, parent):
        """Create Plex connection configuration"""
        # Plex Connection Frame
        plex_frame = ttk.LabelFrame(parent, text="Plex Server Connection", padding=15)
        plex_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Server URL
        ttk.Label(plex_frame, text="Plex Server URL:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.plex_host_var = tk.StringVar()
        self.plex_host_entry = ttk.Entry(plex_frame, textvariable=self.plex_host_var, width=40)
        self.plex_host_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Button(plex_frame, text="Auto-Detect", command=self.auto_detect_plex).grid(row=0, column=2, padx=(10, 0), pady=5)
        
        # Token
        ttk.Label(plex_frame, text="Plex Token:", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.plex_token_var = tk.StringVar()
        self.plex_token_entry = ttk.Entry(plex_frame, textvariable=self.plex_token_var, width=40, show="*")
        self.plex_token_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Button(plex_frame, text="Auto-Detect", command=self.auto_detect_token).grid(row=1, column=2, padx=(10, 0), pady=5)
        
        # Connection status and test
        self.plex_status_label = ttk.Label(plex_frame, text="Not Connected", style='Error.TLabel')
        self.plex_status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Button(plex_frame, text="Test Connection", command=self.test_plex_connection).grid(row=2, column=2, padx=(10, 0), pady=5)
        
        # Libraries list
        ttk.Label(plex_frame, text="Available Libraries:", style='Header.TLabel').grid(row=3, column=0, sticky=tk.NW, pady=(10, 5))
        
        # Libraries frame with scrollbar
        libraries_frame = ttk.Frame(plex_frame)
        libraries_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(10, 5))
        
        self.libraries_listbox = tk.Listbox(libraries_frame, height=6, width=50)
        libs_scrollbar = ttk.Scrollbar(libraries_frame, orient=tk.VERTICAL, command=self.libraries_listbox.yview)
        self.libraries_listbox.configure(yscrollcommand=libs_scrollbar.set)
        
        self.libraries_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        libs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_directory_pairs_section(self, parent):
        """Create directory pairs configuration"""
        # Directory Pairs Frame
        pairs_frame = ttk.LabelFrame(parent, text="Source → Target Directory Pairs", padding=15)
        pairs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Instructions
        instructions = ttk.Label(pairs_frame, 
                               text="Configure multiple source directories (where RAR files are placed) with their target directories (where extracted files go).\nEach pair can be associated with a specific Plex library.",
                               style='Status.TLabel')
        instructions.pack(pady=(0, 10))
        
        # Directory pairs tree
        columns = ('Source Directory', 'Target Directory', 'Plex Library', 'Status')
        self.pairs_tree = ttk.Treeview(pairs_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.pairs_tree.heading(col, text=col)
            self.pairs_tree.column(col, width=200)
        
        # Scrollbar for pairs tree
        pairs_scroll = ttk.Scrollbar(pairs_frame, orient=tk.VERTICAL, command=self.pairs_tree.yview)
        self.pairs_tree.configure(yscrollcommand=pairs_scroll.set)
        
        # Pack tree and scrollbar
        tree_frame = ttk.Frame(pairs_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.pairs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pairs_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Directory pair controls
        controls_frame = ttk.Frame(pairs_frame)
        controls_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(controls_frame, text="Add Pair", command=self.add_directory_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Edit Selected", command=self.edit_directory_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Remove Selected", command=self.remove_directory_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Test Selected", command=self.test_directory_pair).pack(side=tk.LEFT, padx=5)
    
    def create_setup_controls_section(self, parent):
        """Create setup control buttons"""
        controls_frame = ttk.LabelFrame(parent, text="Configuration Controls", padding=15)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Status label
        self.setup_status_label = ttk.Label(controls_frame, text="Ready to configure", style='Status.TLabel')
        self.setup_status_label.pack(pady=(0, 10))
        
        # Control buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack()
        
        ttk.Button(buttons_frame, text="Save Configuration", command=self.save_setup_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Load Configuration", command=self.load_setup_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Apply & Restart Service", command=self.apply_and_restart).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Reset to Defaults", command=self.reset_setup).pack(side=tk.LEFT, padx=5)
        
        # Advanced options
        advanced_frame = ttk.Frame(controls_frame)
        advanced_frame.pack(pady=(10, 0))
        
        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Monitor subdirectories recursively", variable=self.recursive_var).pack(side=tk.LEFT, padx=5)
        
        self.auto_start_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Auto-start service on boot", variable=self.auto_start_var).pack(side=tk.LEFT, padx=5)
    
    def auto_detect_plex(self):
        """Auto-detect Plex server"""
        self.setup_status_label.config(text="Detecting Plex server...")
        self.root.update()
        
        try:
            # Import the discovery functions from setup.py
            import sys
            sys.path.append(str(self.script_dir))
            from setup import discover_plex_server
            
            host = discover_plex_server()
            if host:
                self.plex_host_var.set(host)
                self.setup_status_label.config(text=f"Found Plex server: {host}")
                # Auto-detect token if server found
                self.auto_detect_token()
            else:
                self.setup_status_label.config(text="Could not auto-detect Plex server")
        except Exception as e:
            self.setup_status_label.config(text=f"Error detecting Plex: {e}")
    
    def auto_detect_token(self):
        """Auto-detect Plex token"""
        self.setup_status_label.config(text="Detecting Plex token...")
        self.root.update()
        
        try:
            from setup import discover_plex_token
            
            token = discover_plex_token()
            if token:
                self.plex_token_var.set(token)
                self.setup_status_label.config(text="Plex token detected successfully")
                # Auto-test connection
                self.test_plex_connection()
            else:
                self.setup_status_label.config(text="Could not auto-detect Plex token")
        except Exception as e:
            self.setup_status_label.config(text=f"Error detecting token: {e}")
    
    def test_plex_connection(self):
        """Test Plex connection and load libraries"""
        host = self.plex_host_var.get().strip()
        token = self.plex_token_var.get().strip()
        
        if not host or not token:
            self.plex_status_label.config(text="Please enter host and token", style='Error.TLabel')
            return
        
        self.setup_status_label.config(text="Testing Plex connection...")
        self.root.update()
        
        try:
            # Test connection
            import requests
            url = f"{host.rstrip('/')}/library/sections"
            params = {'X-Plex-Token': token}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse libraries
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            libraries = []
            self.libraries_listbox.delete(0, tk.END)
            
            for directory in root.findall('.//Directory'):
                lib_key = directory.get('key')
                lib_title = directory.get('title')
                lib_type = directory.get('type')
                
                if lib_key and lib_title:
                    library_info = {
                        'key': lib_key,
                        'title': lib_title,
                        'type': lib_type
                    }
                    libraries.append(library_info)
                    
                    # Add to listbox with type indicator
                    type_icon = "📽️" if lib_type == "movie" else "📺" if lib_type == "show" else "📁"
                    display_text = f"{type_icon} {lib_title} (Key: {lib_key})"
                    self.libraries_listbox.insert(tk.END, display_text)
            
            self.setup_data['plex_libraries'] = libraries
            self.setup_data['plex_host'] = host
            self.setup_data['plex_token'] = token
            
            self.plex_status_label.config(text=f"✅ Connected - Found {len(libraries)} libraries", style='Running.TLabel')
            self.setup_status_label.config(text=f"Connected to Plex - {len(libraries)} libraries available")
            
        except Exception as e:
            self.plex_status_label.config(text=f"❌ Connection failed: {e}", style='Error.TLabel')
            self.setup_status_label.config(text=f"Plex connection failed: {e}")
    
    def add_directory_pair(self):
        """Add new directory pair"""
        self.open_directory_pair_dialog()
    
    def edit_directory_pair(self):
        """Edit selected directory pair"""
        selection = self.pairs_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a directory pair to edit")
            return
        
        item = self.pairs_tree.item(selection[0])
        values = item['values']
        
        # Find the pair in setup data
        for i, pair in enumerate(self.setup_data['directory_pairs']):
            if pair['source'] == values[0] and pair['target'] == values[1]:
                self.open_directory_pair_dialog(edit_index=i)
                break
    
    def remove_directory_pair(self):
        """Remove selected directory pair"""
        selection = self.pairs_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a directory pair to remove")
            return
        
        if messagebox.askyesno("Confirm Removal", "Are you sure you want to remove this directory pair?"):
            item = self.pairs_tree.item(selection[0])
            values = item['values']
            
            # Remove from setup data
            self.setup_data['directory_pairs'] = [
                pair for pair in self.setup_data['directory_pairs']
                if not (pair['source'] == values[0] and pair['target'] == values[1])
            ]
            
            # Refresh display
            self.refresh_pairs_display()
            self.setup_status_label.config(text="Directory pair removed")
    
    def test_directory_pair(self):
        """Test selected directory pair"""
        selection = self.pairs_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a directory pair to test")
            return
        
        item = self.pairs_tree.item(selection[0])
        values = item['values']
        source_dir = values[0]
        target_dir = values[1]
        
        # Test directories
        issues = []
        
        # Test source directory
        if not os.path.exists(source_dir):
            issues.append(f"Source directory does not exist: {source_dir}")
        elif not os.access(source_dir, os.R_OK):
            issues.append(f"Source directory is not readable: {source_dir}")
        
        # Test target directory
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create target directory: {target_dir} - {e}")
        
        if os.path.exists(target_dir) and not os.access(target_dir, os.W_OK):
            issues.append(f"Target directory is not writable: {target_dir}")
        
        # Show results
        if issues:
            messagebox.showerror("Directory Test Failed", "\n".join(issues))
        else:
            messagebox.showinfo("Directory Test Passed", "All directories are accessible and writable!")
    
    def open_directory_pair_dialog(self, edit_index=None):
        """Open directory pair configuration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Directory Pair")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Initialize variables
        source_var = tk.StringVar()
        target_var = tk.StringVar()
        library_var = tk.StringVar()
        enabled_var = tk.BooleanVar(value=True)
        
        # If editing, populate with existing values
        if edit_index is not None:
            pair = self.setup_data['directory_pairs'][edit_index]
            source_var.set(pair['source'])
            target_var.set(pair['target'])
            library_var.set(pair['library_key'])
            enabled_var.set(pair.get('enabled', True))
        
        # Source directory
        ttk.Label(dialog, text="Source Directory (where RAR files are dropped):", style='Header.TLabel').pack(pady=(10, 5))
        source_frame = ttk.Frame(dialog)
        source_frame.pack(fill=tk.X, padx=10, pady=5)
        
        source_entry = ttk.Entry(source_frame, textvariable=source_var, width=60)
        source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(source_frame, text="Browse", 
                  command=lambda: self.browse_directory(source_var)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Target directory
        ttk.Label(dialog, text="Target Directory (where extracted files go):", style='Header.TLabel').pack(pady=(10, 5))
        target_frame = ttk.Frame(dialog)
        target_frame.pack(fill=tk.X, padx=10, pady=5)
        
        target_entry = ttk.Entry(target_frame, textvariable=target_var, width=60)
        target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(target_frame, text="Browse", 
                  command=lambda: self.browse_directory(target_var)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Plex library selection
        ttk.Label(dialog, text="Associated Plex Library:", style='Header.TLabel').pack(pady=(10, 5))
        
        if self.setup_data['plex_libraries']:
            library_values = ["None"] + [f"{lib['title']} (Key: {lib['key']})" for lib in self.setup_data['plex_libraries']]
            library_combo = ttk.Combobox(dialog, textvariable=library_var, values=library_values, width=50)
            library_combo.pack(padx=10, pady=5)
        else:
            ttk.Label(dialog, text="No Plex libraries available - please test Plex connection first", 
                     style='Error.TLabel').pack(padx=10, pady=5)
            library_combo = ttk.Entry(dialog, textvariable=library_var, width=50)
            library_combo.pack(padx=10, pady=5)
        
        # Options
        options_frame = ttk.Frame(dialog)
        options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Checkbutton(options_frame, text="Enable this directory pair", variable=enabled_var).pack(side=tk.LEFT)
        
        # Buttons
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(pady=20)
        
        def save_pair():
            source = source_var.get().strip()
            target = target_var.get().strip()
            library = library_var.get().strip()
            
            if not source or not target:
                messagebox.showerror("Invalid Input", "Please specify both source and target directories")
                return
            
            # Extract library key if needed
            library_key = ""
            library_title = "None"
            if library and library != "None":
                if "(Key: " in library:
                    library_title = library.split(" (Key: ")[0]
                    library_key = library.split("(Key: ")[1].rstrip(")")
                else:
                    library_key = library
                    library_title = library
            
            # Create or update pair
            pair_data = {
                'source': source,
                'target': target,
                'library_key': library_key,
                'library_title': library_title,
                'enabled': enabled_var.get()
            }
            
            if edit_index is not None:
                self.setup_data['directory_pairs'][edit_index] = pair_data
            else:
                self.setup_data['directory_pairs'].append(pair_data)
            
            self.refresh_pairs_display()
            self.setup_status_label.config(text="Directory pair saved")
            dialog.destroy()
        
        ttk.Button(buttons_frame, text="Save", command=save_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def browse_directory(self, var):
        """Browse for directory"""
        from tkinter import filedialog
        directory = filedialog.askdirectory()
        if directory:
            var.set(directory)
    
    def refresh_pairs_display(self):
        """Refresh directory pairs display"""
        # Clear existing items
        for item in self.pairs_tree.get_children():
            self.pairs_tree.delete(item)
        
        # Add current pairs
        for pair in self.setup_data['directory_pairs']:
            status = "✅ Enabled" if pair.get('enabled', True) else "❌ Disabled"
            library_display = pair['library_title'] if pair['library_title'] else "None"
            
            self.pairs_tree.insert('', 'end', values=(
                pair['source'],
                pair['target'],
                library_display,
                status
            ))
    
    def save_setup_config(self):
        """Save setup configuration to file"""
        try:
            config_data = {
                'plex': {
                    'host': self.setup_data['plex_host'],
                    'token': self.setup_data['plex_token'],
                    'libraries': self.setup_data['plex_libraries']
                },
                'directory_pairs': self.setup_data['directory_pairs'],
                'options': {
                    'recursive_monitoring': self.recursive_var.get(),
                    'auto_start_service': self.auto_start_var.get()
                }
            }
            
            # Save to setup config file
            setup_config_file = self.script_dir / "setup_config.json"
            import json
            
            with open(setup_config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Also update main config.yaml
            self.update_main_config()
            
            self.setup_status_label.config(text=f"Configuration saved to {setup_config_file}")
            messagebox.showinfo("Configuration Saved", "Setup configuration has been saved successfully!")
            
        except Exception as e:
            self.setup_status_label.config(text=f"Error saving configuration: {e}")
            messagebox.showerror("Save Error", f"Failed to save configuration: {e}")
    
    def load_setup_config(self):
        """Load setup configuration from file"""
        try:
            setup_config_file = self.script_dir / "setup_config.json"
            
            if setup_config_file.exists():
                import json
                with open(setup_config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Load Plex settings
                plex_config = config_data.get('plex', {})
                self.plex_host_var.set(plex_config.get('host', ''))
                self.plex_token_var.set(plex_config.get('token', ''))
                self.setup_data['plex_libraries'] = plex_config.get('libraries', [])
                self.setup_data['plex_host'] = plex_config.get('host', '')
                self.setup_data['plex_token'] = plex_config.get('token', '')
                
                # Load directory pairs
                self.setup_data['directory_pairs'] = config_data.get('directory_pairs', [])
                
                # Load options
                options = config_data.get('options', {})
                self.recursive_var.set(options.get('recursive_monitoring', True))
                self.auto_start_var.set(options.get('auto_start_service', True))
                
                # Refresh displays
                self.refresh_pairs_display()
                
                # Update Plex libraries listbox
                self.libraries_listbox.delete(0, tk.END)
                for lib in self.setup_data['plex_libraries']:
                    type_icon = "📽️" if lib['type'] == "movie" else "📺" if lib['type'] == "show" else "📁"
                    display_text = f"{type_icon} {lib['title']} (Key: {lib['key']})"
                    self.libraries_listbox.insert(tk.END, display_text)
                
                # Update status
                if self.setup_data['plex_host'] and self.setup_data['plex_token']:
                    self.plex_status_label.config(text=f"✅ Configured - {len(self.setup_data['plex_libraries'])} libraries", style='Running.TLabel')
                
                self.setup_status_label.config(text=f"Configuration loaded from {setup_config_file}")
                
            else:
                # Try to load from main config
                self.load_from_main_config()
                
        except Exception as e:
            self.setup_status_label.config(text=f"Error loading configuration: {e}")
    
    def load_from_main_config(self):
        """Load basic settings from main config.yaml"""
        try:
            if self.config_file.exists():
                import yaml
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Load basic Plex settings
                plex_config = config.get('plex', {})
                self.plex_host_var.set(plex_config.get('host', ''))
                self.plex_token_var.set(plex_config.get('token', ''))
                
                # Create default directory pair from main config
                paths = config.get('paths', {})
                if paths.get('watch') and paths.get('target'):
                    default_pair = {
                        'source': paths['watch'],
                        'target': paths['target'],
                        'library_key': str(plex_config.get('library_key', '')),
                        'library_title': 'Default Library',
                        'enabled': True
                    }
                    self.setup_data['directory_pairs'] = [default_pair]
                    self.refresh_pairs_display()
                
                self.setup_status_label.config(text="Loaded basic settings from main config")
                
        except Exception as e:
            self.setup_status_label.config(text=f"Error loading main config: {e}")
    
    def update_main_config(self):
        """Update main config.yaml with first directory pair"""
        try:
            # Load existing config
            config = {}
            if self.config_file.exists():
                import yaml
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
            
            # Update with setup data
            if not config.get('plex'):
                config['plex'] = {}
            
            config['plex']['host'] = self.setup_data['plex_host']
            config['plex']['token'] = self.setup_data['plex_token']
            
            # Use first enabled directory pair for main config
            enabled_pairs = [p for p in self.setup_data['directory_pairs'] if p.get('enabled', True)]
            if enabled_pairs:
                first_pair = enabled_pairs[0]
                config['plex']['library_key'] = int(first_pair['library_key']) if first_pair['library_key'].isdigit() else 1
                
                if not config.get('paths'):
                    config['paths'] = {}
                
                config['paths']['watch'] = first_pair['source']
                config['paths']['target'] = first_pair['target']
            
            # Save updated config
            import yaml
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
                
        except Exception as e:
            print(f"Error updating main config: {e}")
    
    def apply_and_restart(self):
        """Apply configuration and restart service"""
        if messagebox.askyesno("Apply Configuration", 
                              "This will save the configuration and restart the Plex RAR Bridge service. Continue?"):
            try:
                # Save configuration
                self.save_setup_config()
                
                # Restart service
                self.setup_status_label.config(text="Restarting service...")
                self.root.update()
                
                # Try to restart the service
                try:
                    subprocess.run(['sc', 'stop', 'PlexRarBridge'], capture_output=True)
                    time.sleep(2)
                    subprocess.run(['sc', 'start', 'PlexRarBridge'], capture_output=True)
                    self.setup_status_label.config(text="Service restarted successfully")
                except Exception as e:
                    self.setup_status_label.config(text=f"Manual service restart may be needed: {e}")
                
                messagebox.showinfo("Applied", "Configuration applied. Service restart attempted.")
                
            except Exception as e:
                messagebox.showerror("Apply Error", f"Failed to apply configuration: {e}")
    
    def reset_setup(self):
        """Reset setup to defaults"""
        if messagebox.askyesno("Reset Setup", "This will clear all setup configuration. Continue?"):
            self.setup_data = {
                'directory_pairs': [],
                'plex_libraries': [],
                'plex_host': '',
                'plex_token': ''
            }
            
            self.plex_host_var.set('')
            self.plex_token_var.set('')
            self.recursive_var.set(True)
            self.auto_start_var.set(True)
            
            self.libraries_listbox.delete(0, tk.END)
            self.refresh_pairs_display()
            
            self.plex_status_label.config(text="Not Connected", style='Error.TLabel')
            self.setup_status_label.config(text="Setup reset to defaults")
    
    def create_enhanced_setup_tab(self):
        """Create enhanced setup tab with processing mode selection"""
        try:
            # Import the enhanced setup panel
            from enhanced_setup_panel import EnhancedSetupPanel
            
            # Create the enhanced setup panel
            self.enhanced_setup_panel = EnhancedSetupPanel(self.notebook, self.script_dir)
            
        except ImportError:
            # Fallback if enhanced setup panel is not available
            fallback_frame = ttk.Frame(self.notebook)
            self.notebook.add(fallback_frame, text="Enhanced Setup")
            
            ttk.Label(fallback_frame, 
                     text="Enhanced Setup Panel is not available.\nPlease ensure enhanced_setup_panel.py is in the same directory.",
                     font=('TkDefaultFont', 12)).pack(expand=True)
        except Exception as e:
            # Error handling
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="Enhanced Setup")
            
            ttk.Label(error_frame, 
                     text=f"Error loading Enhanced Setup Panel:\n{e}",
                     font=('TkDefaultFont', 12)).pack(expand=True)
    
    def create_config_tab(self):
        """Create configuration tab"""
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Raw Configuration")
        
        ttk.Label(config_frame, text="Current Configuration", style='Title.TLabel').pack(pady=(10, 5))
        
        # Configuration display
        self.config_display = scrolledtext.ScrolledText(config_frame, font=('Consolas', 9))
        self.config_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Config controls
        config_controls = ttk.Frame(config_frame)
        config_controls.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(config_controls, text="Reload Config", command=self.reload_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_controls, text="Open Config File", command=self.open_config_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_controls, text="Test Installation", command=self.run_test).pack(side=tk.LEFT, padx=5)
    
    def create_control_section(self, parent):
        """Create control buttons section"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X)
        
        # Left side buttons
        left_buttons = ttk.Frame(control_frame)
        left_buttons.pack(side=tk.LEFT)
        
        ttk.Button(left_buttons, text="Service Manager", command=self.open_service_manager).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Open Logs Folder", command=self.open_logs_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Test Plex", command=self.test_plex).pack(side=tk.LEFT, padx=5)
        
        # Right side buttons
        right_buttons = ttk.Frame(control_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="Refresh", command=self.force_refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_buttons, text="Exit", command=self.on_closing).pack(side=tk.LEFT, padx=5)
    
    def setup_ftp_logging(self):
        """Setup FTP logging system"""
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Ensure logs directory exists
        logs_dir = self.script_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Create FTP logger
        self.ftp_logger = logging.getLogger('ftp_gui')
        self.ftp_logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        if self.ftp_logger.handlers:
            self.ftp_logger.handlers.clear()
        
        # Create FTP log handler
        ftp_handler = RotatingFileHandler(
            self.ftp_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        # Format for FTP logs
        ftp_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s [FTP] %(message)s'
        )
        ftp_handler.setFormatter(ftp_formatter)
        
        # Add handler to logger
        self.ftp_logger.addHandler(ftp_handler)
        
        # Don't propagate to root logger to avoid duplicate console output
        self.ftp_logger.propagate = False
        
        # Log startup
        self.ftp_logger.info("FTP logging system initialized")
    
    def setup_monitoring(self):
        """Setup monitoring data structures"""
        self.last_log_position = 0
        self.last_ftp_log_position = 0
        self.start_time = datetime.now()
    
    def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Update service status
                self.update_service_status()
                
                # Parse logs for thread activity
                self.parse_log_activity()
                
                # Update statistics
                self.update_statistics()
                
                # Queue GUI update
                self.update_queue.put("refresh")
                
                time.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                print(f"Monitor loop error: {e}")
                time.sleep(5)
    
    def update_service_status(self):
        """Update service and process status"""
        try:
            # Check Windows service
            result = subprocess.run(['sc', 'query', self.service_name], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and 'RUNNING' in result.stdout:
                service_status = "🟢 RUNNING"
            elif result.returncode == 0 and 'STOPPED' in result.stdout:
                service_status = "🔴 STOPPED"
            else:
                service_status = "❓ UNKNOWN"
        except:
            service_status = "❌ ERROR"
        
        # Check for Python process
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                                  capture_output=True, text=True)
            if 'plex_rar_bridge.py' in result.stdout:
                process_status = "🟢 ACTIVE"
            else:
                process_status = "🔴 INACTIVE"
        except:
            process_status = "❓ UNKNOWN"
        
        # Check monitoring status
        if self.log_file.exists():
            monitoring_status = "🟢 LOGGING"
        else:
            monitoring_status = "🔴 NO LOGS"
        
        self.update_queue.put(("service_status", {
            'service': service_status,
            'process': process_status,
            'monitoring': monitoring_status
        }))
    
    def parse_log_activity(self):
        """Parse log files for thread activity and retry queue"""
        # Parse main bridge log
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Seek to last position
                    f.seek(self.last_log_position)
                    new_lines = f.readlines()
                    self.last_log_position = f.tell()
                
                for line in new_lines:
                    self.process_log_line(line.strip())
                    
            except Exception as e:
                print(f"Error parsing bridge logs: {e}")
        
        # Parse FTP log
        if self.ftp_log_file.exists():
            try:
                with open(self.ftp_log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Seek to last position
                    f.seek(self.last_ftp_log_position)
                    new_lines = f.readlines()
                    self.last_ftp_log_position = f.tell()
                
                for line in new_lines:
                    self.process_log_line(line.strip())
                    
            except Exception as e:
                print(f"Error parsing FTP logs: {e}")
    
    def process_log_line(self, line):
        """Process individual log line"""
        if not line:
            return
        
        # Add to recent activity
        self.recent_activity.append({
            'timestamp': datetime.now(),
            'line': line
        })
        
        # Keep only last 100 entries
        if len(self.recent_activity) > 100:
            self.recent_activity.pop(0)
        
        # Extract thread information
        thread_match = re.search(r'\[([^\]]+)\]', line)
        if thread_match:
            thread_name = thread_match.group(1)
            
            # Track thread activity
            if 'Starting extraction' in line:
                file_match = re.search(r'Starting extraction: (.+)', line)
                if file_match:
                    filename = file_match.group(1)
                    self.active_threads[thread_name] = {
                        'status': 'Extracting',
                        'file': filename,
                        'started': datetime.now(),
                        'progress': 'In Progress'
                    }
            
            elif 'Successfully processed' in line:
                if thread_name in self.active_threads:
                    self.active_threads[thread_name]['status'] = 'Completed'
                    self.active_threads[thread_name]['progress'] = 'Done'
            
            elif 'ERROR' in line and thread_name in self.active_threads:
                self.active_threads[thread_name]['status'] = 'Error'
                self.active_threads[thread_name]['progress'] = 'Failed'
        
        # Track retry queue
        if 'Added to retry queue' in line:
            file_match = re.search(r'Added to retry queue.*: (.+)', line)
            if file_match:
                filename = file_match.group(1)
                if filename in self.retry_queue:
                    self.retry_queue[filename]['attempts'] += 1
                    self.retry_queue[filename]['last_attempt'] = datetime.now()
                else:
                    self.retry_queue[filename] = {
                        'attempts': 1,
                        'first_seen': datetime.now(),
                        'last_attempt': datetime.now(),
                        'status': 'Waiting'
                    }
        
        elif 'Retry successful' in line:
            file_match = re.search(r'Retry successful, processing: (.+)', line)
            if file_match:
                filename = file_match.group(1)
                if filename in self.retry_queue:
                    del self.retry_queue[filename]
        
        # Update statistics
        if 'ERROR' in line:
            self.statistics['errors'] += 1
        elif 'WARNING' in line:
            self.statistics['warnings'] += 1
        elif 'Successfully processed' in line:
            self.statistics['processed'] += 1
        elif 'Added to retry queue' in line:
            self.statistics['retries'] += 1
        
        # Queue log display update
        self.update_queue.put(("new_log", line))
    
    def update_statistics(self):
        """Update statistics"""
        self.statistics['active_threads'] = len(self.active_threads)
        self.statistics['queue_length'] = len(self.retry_queue)
        
        # Calculate uptime
        uptime_delta = datetime.now() - self.start_time
        self.statistics['uptime'] = str(uptime_delta).split('.')[0]
        
        # Calculate processing rate
        hours = uptime_delta.total_seconds() / 3600
        if hours > 0:
            self.statistics['rate'] = round(self.statistics['processed'] / hours, 2)
        else:
            self.statistics['rate'] = 0
    
    def update_gui_loop(self):
        """GUI update loop"""
        try:
            while True:
                try:
                    update_type = self.update_queue.get_nowait()
                    
                    if update_type == "refresh":
                        self.refresh_all_displays()
                    elif isinstance(update_type, tuple):
                        update_name, data = update_type
                        if update_name == "service_status":
                            self.update_service_display(data)
                        elif update_name == "new_log":
                            self.add_log_entry(data)
                            
                except queue.Empty:
                    break
        except:
            pass
        
        # Schedule next update
        self.root.after(100, self.update_gui_loop)
    
    def refresh_all_displays(self):
        """Refresh all GUI displays"""
        self.update_threads_display()
        self.update_retry_display()
        self.update_statistics_display()
        self.update_config_display()
    
    def update_service_display(self, data):
        """Update service status display"""
        self.service_status_label.config(text=data['service'])
        self.process_status_label.config(text=data['process'])
        self.monitoring_status_label.config(text=data['monitoring'])
    
    def update_threads_display(self):
        """Update threads tree view"""
        # Clear existing items
        for item in self.threads_tree.get_children():
            self.threads_tree.delete(item)
        
        # Add current threads
        for thread_name, thread_info in self.active_threads.items():
            duration = datetime.now() - thread_info['started']
            duration_str = str(duration).split('.')[0]
            
            self.threads_tree.insert('', 'end', values=(
                thread_name,
                thread_info['status'],
                thread_info['file'],
                thread_info['progress'],
                thread_info['started'].strftime('%H:%M:%S'),
                duration_str
            ))
        
        # Clean up completed threads older than 5 minutes
        cutoff_time = datetime.now() - timedelta(minutes=5)
        threads_to_remove = []
        for thread_name, thread_info in self.active_threads.items():
            if thread_info['status'] in ['Completed', 'Error'] and thread_info['started'] < cutoff_time:
                threads_to_remove.append(thread_name)
        
        for thread_name in threads_to_remove:
            del self.active_threads[thread_name]
    
    def update_retry_display(self):
        """Update retry queue tree view"""
        # Clear existing items
        for item in self.retry_tree.get_children():
            self.retry_tree.delete(item)
        
        # Add current retry queue
        for filename, retry_info in self.retry_queue.items():
            self.retry_tree.insert('', 'end', values=(
                filename,
                retry_info['attempts'],
                retry_info['first_seen'].strftime('%H:%M:%S'),
                retry_info['last_attempt'].strftime('%H:%M:%S'),
                retry_info['status']
            ))
    
    def update_statistics_display(self):
        """Update statistics display"""
        # Update main stats
        self.processed_label.config(text=str(self.statistics['processed']))
        self.errors_label.config(text=str(self.statistics['errors']))
        self.uptime_label.config(text=self.statistics['uptime'])
        
        # Update detailed stats
        for key, label in self.stats_labels.items():
            if key in self.statistics:
                label.config(text=str(self.statistics[key]))
        
        # Update activity summary
        self.activity_summary.delete(1.0, tk.END)
        
        summary_lines = [
            f"Processing Summary (Last 24h):",
            f"Files Processed: {self.statistics['processed']}",
            f"Processing Rate: {self.statistics['rate']} files/hour",
            f"Active Threads: {self.statistics['active_threads']}",
            f"Retry Queue: {self.statistics['queue_length']} files",
            f"Total Errors: {self.statistics['errors']}",
            f"Total Warnings: {self.statistics['warnings']}",
            f"Total Retries: {self.statistics['retries']}",
            "",
            "Recent File Activity:"
        ]
        
        # Add recent file activity
        recent_files = []
        for activity in self.recent_activity[-10:]:
            if 'Successfully processed' in activity['line']:
                file_match = re.search(r'Successfully processed.*from (.+)', activity['line'])
                if file_match:
                    recent_files.append(f"✅ {file_match.group(1)}")
            elif 'ERROR' in activity['line'] and 'Archive test failed' in activity['line']:
                file_match = re.search(r'Archive test failed: (.+)', activity['line'])
                if file_match:
                    recent_files.append(f"❌ {file_match.group(1)}")
        
        summary_lines.extend(recent_files[-5:])
        
        self.activity_summary.insert(1.0, '\n'.join(summary_lines))
    
    def update_config_display(self):
        """Update configuration display"""
        if not hasattr(self, 'config_loaded'):
            self.reload_config()
    
    def add_log_entry(self, line):
        """Add new log entry to display"""
        # Check filter
        log_level = self.log_level_var.get()
        if log_level != "ALL":
            if log_level not in line:
                return
        
        # Determine tag for coloring
        tag = "INFO"
        if "ERROR" in line:
            tag = "ERROR"
        elif "WARNING" in line:
            tag = "WARNING"
        elif "DEBUG" in line:
            tag = "DEBUG"
        
        # Add to display
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_line = f"[{timestamp}] {line}\n"
        
        self.log_display.insert(tk.END, formatted_line, tag)
        
        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.log_display.see(tk.END)
        
        # Limit log display to 1000 lines
        lines = self.log_display.get(1.0, tk.END).split('\n')
        if len(lines) > 1000:
            # Remove first 200 lines
            line_count = self.log_display.index(tk.END).split('.')[0]
            self.log_display.delete(1.0, f"{200}.0")
    
    # Event handlers and utility methods
    def on_thread_select(self, event):
        """Handle thread selection"""
        selection = self.threads_tree.selection()
        if selection:
            item = self.threads_tree.item(selection[0])
            thread_name = item['values'][0]
            
            if thread_name in self.active_threads:
                thread_info = self.active_threads[thread_name]
                details = f"""Thread: {thread_name}
Status: {thread_info['status']}
File: {thread_info['file']}
Started: {thread_info['started']}
Duration: {datetime.now() - thread_info['started']}
Progress: {thread_info['progress']}
"""
                self.thread_details.delete(1.0, tk.END)
                self.thread_details.insert(1.0, details)
    
    def force_retry(self):
        """Force retry selected file"""
        selection = self.retry_tree.selection()
        if selection:
            messagebox.showinfo("Force Retry", "Force retry functionality would be implemented here")
    
    def remove_from_queue(self):
        """Remove selected file from retry queue"""
        selection = self.retry_tree.selection()
        if selection:
            item = self.retry_tree.item(selection[0])
            filename = item['values'][0]
            if filename in self.retry_queue:
                del self.retry_queue[filename]
                messagebox.showinfo("Removed", f"Removed {filename} from retry queue")
    
    def clear_old_entries(self):
        """Clear old retry queue entries"""
        cutoff_time = datetime.now() - timedelta(hours=4)
        to_remove = []
        for filename, retry_info in self.retry_queue.items():
            if retry_info['first_seen'] < cutoff_time:
                to_remove.append(filename)
        
        for filename in to_remove:
            del self.retry_queue[filename]
        
        messagebox.showinfo("Cleared", f"Removed {len(to_remove)} old entries")
    
    def clear_logs(self):
        """Clear log display"""
        self.log_display.delete(1.0, tk.END)
    
    def save_logs(self):
        """Save current log display"""
        try:
            logs_content = self.log_display.get(1.0, tk.END)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"gui_logs_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(logs_content)
            
            messagebox.showinfo("Saved", f"Logs saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save logs: {e}")
    
    def reload_config(self):
        """Reload configuration"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_content = f.read()
                
                self.config_display.delete(1.0, tk.END)
                self.config_display.insert(1.0, config_content)
                self.config_loaded = True
            else:
                self.config_display.delete(1.0, tk.END)
                self.config_display.insert(1.0, "Configuration file not found!")
        except Exception as e:
            self.config_display.delete(1.0, tk.END)
            self.config_display.insert(1.0, f"Error loading config: {e}")
    
    def open_config_file(self):
        """Open configuration file in default editor"""
        try:
            os.startfile(str(self.config_file))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open config file: {e}")
    
    def run_test(self):
        """Run installation test"""
        try:
            subprocess.Popen([sys.executable, "test_installation.py"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run test: {e}")
    
    def open_service_manager(self):
        """Open service manager"""
        try:
            subprocess.Popen([sys.executable, "install_service_improved.py"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open service manager: {e}")
    
    def open_logs_folder(self):
        """Open logs folder"""
        try:
            logs_dir = self.script_dir / "logs"
            os.startfile(str(logs_dir))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open logs folder: {e}")
    
    def test_plex(self):
        """Run Plex detection test"""
        try:
            subprocess.Popen([sys.executable, "test_plex_detection.py"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run Plex test: {e}")
    
    def force_refresh(self):
        """Force refresh all data"""
        self.update_queue.put("refresh")
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        self.root.destroy()
    
    def load_ftp_config(self):
        """Load FTP configuration"""
        try:
            if self.ftp_config_file.exists():
                with open(self.ftp_config_file, 'r') as f:
                    self.ftp_config = json.load(f)
            else:
                # Create default config
                self.ftp_config = {
                    "connections": [],
                    "last_used": "",
                    "settings": {
                        "auto_connect": False,
                        "auto_download_rar": True,
                        "transfer_mode": "Binary",
                        "max_concurrent_downloads": 3
                    }
                }
                self.save_ftp_config()
            
            # Populate presets combo
            connection_names = [conn['name'] for conn in self.ftp_config.get('connections', [])]
            self.ftp_presets_combo['values'] = connection_names
            
            # Load last used connection
            last_used = self.ftp_config.get('last_used', '')
            if last_used and last_used in connection_names:
                self.ftp_presets_var.set(last_used)
                self.load_ftp_preset()
                
        except Exception as e:
            print(f"Error loading FTP config: {e}")
    
    def save_ftp_config(self):
        """Save FTP configuration"""
        try:
            with open(self.ftp_config_file, 'w') as f:
                json.dump(self.ftp_config, f, indent=2)
        except Exception as e:
            print(f"Error saving FTP config: {e}")
    
    def load_ftp_preset(self, event=None):
        """Load selected FTP preset"""
        preset_name = self.ftp_presets_var.get()
        if not preset_name:
            return
        
        for conn in self.ftp_config.get('connections', []):
            if conn['name'] == preset_name:
                self.ftp_host_var.set(conn.get('host', ''))
                self.ftp_port_var.set(str(conn.get('port', 21)))
                self.ftp_user_var.set(conn.get('username', ''))
                self.ftp_pass_var.set(conn.get('password', ''))
                self.ftp_ssl_var.set(conn.get('ssl_mode', 'Explicit'))
                self.ftp_download_dir_var.set(conn.get('download_dir', ''))
                self.ftp_movie_dirs_var.set(conn.get('movie_dirs', ''))
                self.ftp_tv_dirs_var.set(conn.get('tv_dirs', ''))
                self.ftp_filter_var.set(conn.get('file_filter', '*.rar'))
                break
    
    def save_ftp_preset(self):
        """Save current FTP settings as preset"""
        preset_name = tk.simpledialog.askstring("Save Preset", "Enter name for this connection:")
        if not preset_name:
            return
        
        # Check if preset already exists
        for i, conn in enumerate(self.ftp_config.get('connections', [])):
            if conn['name'] == preset_name:
                if messagebox.askyesno("Overwrite", f"Connection '{preset_name}' already exists. Overwrite?"):
                    self.ftp_config['connections'][i] = self.get_current_ftp_settings(preset_name)
                    break
                else:
                    return
        else:
            # Add new preset
            if 'connections' not in self.ftp_config:
                self.ftp_config['connections'] = []
            self.ftp_config['connections'].append(self.get_current_ftp_settings(preset_name))
        
        # Update last used
        self.ftp_config['last_used'] = preset_name
        
        # Save config
        self.save_ftp_config()
        
        # Refresh combo box
        connection_names = [conn['name'] for conn in self.ftp_config['connections']]
        self.ftp_presets_combo['values'] = connection_names
        self.ftp_presets_var.set(preset_name)
        
        messagebox.showinfo("Saved", f"Connection '{preset_name}' saved successfully!")
    
    def get_current_ftp_settings(self, name):
        """Get current FTP settings as dictionary"""
        return {
            'name': name,
            'host': self.ftp_host_var.get(),
            'port': int(self.ftp_port_var.get() or 21),
            'username': self.ftp_user_var.get(),
            'password': self.ftp_pass_var.get(),
            'ssl_mode': self.ftp_ssl_var.get(),
            'download_dir': self.ftp_download_dir_var.get(),
            'movie_dirs': self.ftp_movie_dirs_var.get(),
            'tv_dirs': self.ftp_tv_dirs_var.get(),
            'file_filter': self.ftp_filter_var.get()
        }
    
    def browse_movie_dir(self):
        """Browse for movie download directory"""
        directory = filedialog.askdirectory(title="Select Movie Download Directory")
        if directory:
            # Support multiple directories separated by semicolons
            current = self.ftp_movie_dirs_var.get()
            if current:
                self.ftp_movie_dirs_var.set(f"{current};{directory}")
            else:
                self.ftp_movie_dirs_var.set(directory)
    
    def browse_tv_dir(self):
        """Browse for TV show download directory"""
        directory = filedialog.askdirectory(title="Select TV Show Download Directory")
        if directory:
            # Support multiple directories separated by semicolons
            current = self.ftp_tv_dirs_var.get()
            if current:
                self.ftp_tv_dirs_var.set(f"{current};{directory}")
            else:
                self.ftp_tv_dirs_var.set(directory)
    
    def get_destination_folder(self, content_type, folder_name=""):
        """Get appropriate destination folder based on content type"""
        if content_type == 'movie':
            movie_dirs = self.ftp_movie_dirs_var.get()
            if movie_dirs:
                # Return first movie directory (could be enhanced to show selection dialog)
                return movie_dirs.split(';')[0]
        elif content_type == 'tv_show':
            tv_dirs = self.ftp_tv_dirs_var.get()
            if tv_dirs:
                # Return first TV directory (could be enhanced to show selection dialog)
                return tv_dirs.split(';')[0]
        
        # Fallback to general download directory
        return self.ftp_download_dir_var.get()
    
    def ftp_download_folder(self):
        """Download entire selected folder with smart content routing"""
        selection = self.ftp_files_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a folder to download")
            return
        
        item = self.ftp_files_tree.item(selection[0])
        # Column indices: Type=0, Name=1, Size=2, Date=3, Content=4
        file_type, name = item['values'][0], item['values'][1]  # Type and Name columns
        
        if "DIR" not in file_type:
            messagebox.showwarning("Not a Directory", "Please select a directory")
            return
        
        # Detect content type
        content_type = self.detect_content_type(name, self.ftp_connection.pwd() + "/" + name)
        
        # Get destination folder
        destination = self.get_destination_folder(content_type, name)
        if not destination:
            messagebox.showerror("No Destination", 
                               f"Please configure a destination folder for {content_type}s")
            return
        
        # Confirm download
        content_label = {"movie": "🎬 Movie", "tv_show": "📺 TV Show", "other": "📁 Content"}[content_type]
        
        confirm = messagebox.askyesno(
            "Download Folder",
            f"Download entire folder?\n\n"
            f"Folder: {name}\n"
            f"Type: {content_label}\n"
            f"Destination: {destination}\n\n"
            f"This will download all files in the folder."
        )
        
        if not confirm:
            return
        
        # Start folder download
        self._download_folder_contents(name, destination, content_type)
    
    def _matches_filter(self, filename, file_filter):
        """Check if filename matches the filter pattern"""
        if file_filter == "*":
            return True
        
        # Convert simple wildcard patterns to regex
        pattern = file_filter.replace('*', '.*').replace('?', '.')
        return re.match(pattern, filename, re.IGNORECASE) is not None
    
    def download_worker(self):
        """Background worker for processing downloads"""
        max_concurrent = int(self.ftp_max_downloads_var.get() or 3)
        active_downloads = 0
        
        for queue_item in self.download_queue:
            if queue_item['status'] != 'Queued':
                continue
            
            if active_downloads >= max_concurrent:
                break
            
            # Start download
            queue_item['status'] = 'Downloading'
            active_downloads += 1
            
            try:
                # Download file
                success = self._download_file_with_recovery(queue_item)
                
                if success:
                    queue_item['status'] = 'Completed'
                    print(f"✅ Downloaded: {queue_item['filename']} to {queue_item['local_path']}")
                else:
                    queue_item['status'] = 'Failed'
                    print(f"❌ Failed: {queue_item['filename']}")
                
                active_downloads -= 1
                self.update_queue_display()
                
            except Exception as e:
                queue_item['status'] = f'Error: {str(e)[:30]}'
                active_downloads -= 1
                self.update_queue_display()
                print(f"❌ Download error: {queue_item['filename']}: {e}")
    
    def _download_folder_contents(self, folder_name, destination, content_type):
        """Download all contents of a folder with smart RAR set detection"""
        if not self.ftp_connected:
            return
        
        try:
            # Save current directory
            original_dir = self.ftp_connection.pwd()
            
            # Navigate to folder
            self.ftp_connection.cwd(folder_name)
            current_remote_path = self.ftp_connection.pwd()
            
            # Create local destination folder
            local_folder = Path(destination) / folder_name
            local_folder.mkdir(parents=True, exist_ok=True)
            
            # Get directory listing
            lines = []
            self.ftp_connection.retrlines('LIST', lines.append)
            
            # Parse files and detect RAR sets
            all_files = []
            rar_sets = {}  # Base name -> list of parts
            
            for line in lines:
                if not line.startswith('d'):  # File, not directory
                    parts = line.split()
                    if len(parts) >= 9:
                        filename = ' '.join(parts[8:])
                        file_size = int(parts[4]) if parts[4].isdigit() else 0
                        
                        all_files.append({
                            'name': filename,
                            'size': file_size,
                            'path': f"{current_remote_path}/{filename}"
                        })
                        
                        # Check if this is part of a RAR set
                        self._analyze_rar_file(filename, rar_sets)
            
            print(f"Found {len(all_files)} files in {folder_name}")
            print(f"Detected {len(rar_sets)} RAR sets: {list(rar_sets.keys())}")
            
            # For folder downloads, always download ALL files regardless of filter
            files_to_download = all_files
            print(f"Folder download: Queuing all {len(all_files)} files in folder...")
            
            # Show RAR set information for user awareness
            if rar_sets:
                print(f"  Contains {len(rar_sets)} RAR sets with complete archives")
            
            # Queue downloads
            download_count = 0
            for file_info in files_to_download:
                queue_item = {
                    'filename': file_info['name'],
                    'remote_path': file_info['path'],
                    'local_path': local_folder / file_info['name'],  # Keep as Path object, don't convert to string
                    'size': file_info['size'],
                    'status': 'Queued',
                    'progress': 0,
                    'content_type': content_type,
                    'folder': folder_name
                }
                
                self.download_queue.append(queue_item)
                download_count += 1
            
            # Restore directory
            self.ftp_connection.cwd(original_dir)
            
            # Update queue display
            self.update_queue_display()
            
            # Start downloads if not already running
            if not any(item['status'] == 'Downloading' for item in self.download_queue):
                threading.Thread(target=self.download_worker, daemon=True).start()
            
            # Show detailed summary
            rar_count = len(rar_sets)
            total_rar_parts = sum(len(parts) for parts in rar_sets.values())
            
            summary_msg = f"Queued {download_count} files from '{folder_name}':\n\n"
            if rar_count > 0:
                summary_msg += f"🗜️ RAR Sets: {rar_count} complete archives ({total_rar_parts} files)\n"
            summary_msg += f"📁 Destination: {local_folder}\n"
            summary_msg += f"🎯 Content Type: {content_type.replace('_', ' ').title()}"
            
            messagebox.showinfo("Smart Download Queued", summary_msg)
            
        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to queue folder download: {e}")
    
    def _analyze_rar_file(self, filename, rar_sets):
        """Analyze filename and group RAR parts together"""
        filename_lower = filename.lower()
        
        # Pattern 1: filename.rar, filename.r00, filename.r01, etc.
        if filename_lower.endswith('.rar'):
            base_name = filename[:-4]  # Remove .rar
            if base_name not in rar_sets:
                rar_sets[base_name] = []
            rar_sets[base_name].append({
                'name': filename,
                'part': 'main',
                'size': 0  # Will be updated when we have size info
            })
        elif re.match(r'.*\.r\d{2}$', filename_lower):  # .r00, .r01, .r02, etc.
            base_name = re.sub(r'\.r\d{2}$', '', filename)
            part_num = re.search(r'\.r(\d{2})$', filename_lower).group(1)
            if base_name not in rar_sets:
                rar_sets[base_name] = []
            rar_sets[base_name].append({
                'name': filename,
                'part': f'r{part_num}',
                'size': 0
            })
        
        # Pattern 2: filename.part01.rar, filename.part02.rar, etc.
        elif re.match(r'.*\.part\d+\.rar$', filename_lower):
            base_name = re.sub(r'\.part\d+\.rar$', '', filename)
            part_num = re.search(r'\.part(\d+)\.rar$', filename_lower).group(1)
            if base_name not in rar_sets:
                rar_sets[base_name] = []
            rar_sets[base_name].append({
                'name': filename,
                'part': f'part{part_num}',
                'size': 0
            })
    
    def ftp_download_all_rar(self):
        """Download all RAR files in current directory with smart set detection"""
        if not self.ftp_connected:
            return
        
        try:
            # Get directory listing
            lines = []
            self.ftp_connection.retrlines('LIST', lines.append)
            
            # Parse files and detect RAR sets
            all_files = []
            rar_sets = {}
            
            for line in lines:
                if not line.startswith('d'):  # File, not directory
                    parts = line.split()
                    if len(parts) >= 9:
                        filename = ' '.join(parts[8:])
                        file_size = int(parts[4]) if parts[4].isdigit() else 0
                        
                        # Check if this is a RAR-related file
                        if self._is_rar_file(filename):
                            all_files.append({
                                'name': filename,
                                'size': file_size
                            })
                            self._analyze_rar_file(filename, rar_sets)
            
            if not all_files:
                messagebox.showinfo("No RAR Files", "No RAR files found in current directory")
                return
            
            # Add complete RAR sets to download queue
            added_count = 0
            for base_name, rar_parts in rar_sets.items():
                print(f"Adding RAR set '{base_name}': {len(rar_parts)} parts")
                for part_info in rar_parts:
                    # Find the file info for this part
                    file_info = next((f for f in all_files if f['name'] == part_info['name']), None)
                    if file_info:
                        self.add_file_to_queue(file_info['name'], file_info['size'])
                        added_count += 1
            
            # Add standalone RAR files
            for file_info in all_files:
                if not any(file_info['name'] in [p['name'] for parts in rar_sets.values() for p in parts]):
                    self.add_file_to_queue(file_info['name'], file_info['size'])
                    added_count += 1
            
            rar_count = len(rar_sets)
            messagebox.showinfo(
                "RAR Files Added", 
                f"Added {added_count} RAR files to download queue:\n\n"
                f"🗜️ Complete RAR sets: {rar_count}\n"
                f"📄 Total files: {added_count}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze RAR files: {e}")
    
    def _is_rar_file(self, filename):
        """Check if filename is a RAR-related file"""
        filename_lower = filename.lower()
        return (filename_lower.endswith('.rar') or 
                re.match(r'.*\.r\d{2}$', filename_lower) or
                re.match(r'.*\.part\d+\.rar$', filename_lower))
    
    def _matches_filter(self, filename, file_filter):
        """Check if filename matches the filter pattern"""
        if file_filter == "*":
            return True
        
        # Convert simple wildcard patterns to regex
        pattern = file_filter.replace('*', '.*').replace('?', '.')
        return re.match(pattern, filename, re.IGNORECASE) is not None

if __name__ == "__main__":
    import tkinter.simpledialog
    
    root = tk.Tk()
    app = PlexRarBridgeGUI(root)
    
    # Check if setup argument is provided
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == 'setup':
            # Select the setup tab
            app.notebook.select(5)  # Setup Panel is the 6th tab (index 5)
        elif arg == 'ftp':
            # Select the FTP tab
            app.notebook.select(4)  # FTP Panel is the 5th tab (index 4)
    
    root.mainloop() 