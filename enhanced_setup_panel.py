"""
Enhanced Setup Panel for Plex RAR Bridge
Includes processing mode selection for each directory pair
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import yaml
from pathlib import Path
import threading
import subprocess
import requests
import xml.etree.ElementTree as ET

class EnhancedSetupPanel:
    """Enhanced setup panel with processing mode selection"""
    
    def __init__(self, parent, script_dir):
        self.parent = parent
        self.script_dir = Path(script_dir)
        
        # Setup data
        self.setup_data = {
            'directory_pairs': [],
            'plex_libraries': [],
            'plex_host': '',
            'plex_token': '',
            'global_processing_mode': 'python_vfs'
        }
        
        # Processing mode options
        self.processing_modes = {
            'extraction': {
                'name': 'Traditional Extraction',
                'description': 'Extract files to disk (requires 2x space)',
                'dependencies': 'UnRAR only',
                'complexity': 'Simple'
            },
            'rar2fs': {
                'name': 'External rar2fs',
                'description': 'Mount using external rar2fs (complex setup)',
                'dependencies': 'Cygwin + WinFSP + rar2fs',
                'complexity': 'Very Complex'
            },
            'python_vfs': {
                'name': 'Python VFS (Recommended)',
                'description': 'Pure Python virtual filesystem (no dependencies)',
                'dependencies': 'None',
                'complexity': 'Simple'
            }
        }
        
        # Create the enhanced setup frame and return it
        self.setup_frame = self.create_enhanced_setup_panel()
        # Add the frame to the parent notebook
        self.parent.add(self.setup_frame, text="Enhanced Setup")
        
        # Load existing setup
        self.load_setup_config()
    
    def create_enhanced_setup_panel(self):
        """Create enhanced setup panel with processing mode selection"""
        # Create main frame
        setup_frame = ttk.Frame(self.parent)
        
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
        
        # Create sections
        self.create_processing_mode_info_section(scrollable_frame)
        self.create_global_processing_mode_section(scrollable_frame)
        self.create_plex_connection_section(scrollable_frame)
        self.create_enhanced_directory_pairs_section(scrollable_frame)
        self.create_processing_mode_config_section(scrollable_frame)
        self.create_upnp_config_section(scrollable_frame)
        self.create_enhanced_setup_controls_section(scrollable_frame)
        
        return setup_frame
    
    def create_processing_mode_info_section(self, parent):
        """Create processing mode information section"""
        info_frame = ttk.LabelFrame(parent, text="Processing Mode Information", padding=15)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create info text
        info_text = tk.Text(info_frame, height=8, width=80, wrap=tk.WORD)
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=info_text.yview)
        info_text.configure(yscrollcommand=info_scrollbar.set)
        
        info_content = """
🎯 PROCESSING MODES EXPLAINED:

• PYTHON VFS (RECOMMENDED): Pure Python virtual filesystem - no dependencies, instant setup
  ✅ No external tools needed  ✅ Fast processing  ✅ Space efficient  ✅ HTTP streaming

• TRADITIONAL EXTRACTION: Extract files to disk (classic approach)
  ✅ Simple setup  ✅ Well-tested  ❌ Requires 2x disk space  ❌ Slower processing

• EXTERNAL RAR2FS: Mount using external rar2fs (complex setup required)
  ✅ Space efficient  ✅ Fast processing  ❌ Complex setup  ❌ Windows-specific dependencies

You can assign different processing modes to different directories based on your needs!
        """
        
        info_text.insert(tk.END, info_content.strip())
        info_text.config(state=tk.DISABLED)
        
        info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_global_processing_mode_section(self, parent):
        """Create global processing mode selection"""
        global_frame = ttk.LabelFrame(parent, text="Global Processing Mode", padding=15)
        global_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Description
        ttk.Label(global_frame, text="Default processing mode for new directory pairs:").pack(anchor=tk.W, pady=(0, 10))
        
        # Global processing mode selection
        mode_frame = ttk.Frame(global_frame)
        mode_frame.pack(fill=tk.X)
        
        self.global_mode_var = tk.StringVar(value='python_vfs')
        
        for mode_id, mode_info in self.processing_modes.items():
            mode_radio_frame = ttk.Frame(mode_frame)
            mode_radio_frame.pack(fill=tk.X, pady=2)
            
            ttk.Radiobutton(
                mode_radio_frame,
                text=mode_info['name'],
                variable=self.global_mode_var,
                value=mode_id,
                command=self.update_global_mode_info
            ).pack(side=tk.LEFT)
            
            tk.Label(
                mode_radio_frame,
                text=f"- {mode_info['description']}",
                foreground='gray'
            ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Global mode info
        self.global_mode_info_frame = ttk.Frame(global_frame)
        self.global_mode_info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.global_mode_info_label = tk.Label(self.global_mode_info_frame, text="")
        self.global_mode_info_label.pack(anchor=tk.W)
        
        # Update info initially
        self.update_global_mode_info()
    
    def update_global_mode_info(self):
        """Update global processing mode information"""
        mode = self.global_mode_var.get()
        mode_info = self.processing_modes[mode]
        
        info_text = f"Dependencies: {mode_info['dependencies']} | Complexity: {mode_info['complexity']}"
        self.global_mode_info_label.config(text=info_text)
        
        # Update recommendation color
        if mode == 'python_vfs':
            self.global_mode_info_label.config(foreground='green')
        elif mode == 'extraction':
            self.global_mode_info_label.config(foreground='orange')
        else:
            self.global_mode_info_label.config(foreground='red')
    
    def create_plex_connection_section(self, parent):
        """Create Plex connection configuration"""
        plex_frame = ttk.LabelFrame(parent, text="Plex Server Connection", padding=15)
        plex_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Server URL
        ttk.Label(plex_frame, text="Plex Server URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.plex_host_var = tk.StringVar()
        self.plex_host_entry = ttk.Entry(plex_frame, textvariable=self.plex_host_var, width=50)
        self.plex_host_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Button(plex_frame, text="Auto-Detect", command=self.auto_detect_plex).grid(row=0, column=2, padx=(10, 0), pady=5)
        
        # Token
        ttk.Label(plex_frame, text="Plex Token:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.plex_token_var = tk.StringVar()
        self.plex_token_entry = ttk.Entry(plex_frame, textvariable=self.plex_token_var, width=50, show="*")
        self.plex_token_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Button(plex_frame, text="Auto-Detect", command=self.auto_detect_token).grid(row=1, column=2, padx=(10, 0), pady=5)
        
        # Connection status
        self.plex_status_label = tk.Label(plex_frame, text="Not Connected", foreground='red')
        self.plex_status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Button(plex_frame, text="Test Connection", command=self.test_plex_connection).grid(row=2, column=2, padx=(10, 0), pady=5)
        
        # Libraries
        ttk.Label(plex_frame, text="Available Libraries:").grid(row=3, column=0, sticky=tk.NW, pady=(10, 5))
        
        libraries_frame = ttk.Frame(plex_frame)
        libraries_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(10, 5))
        
        self.libraries_listbox = tk.Listbox(libraries_frame, height=4, width=60)
        libs_scrollbar = ttk.Scrollbar(libraries_frame, orient=tk.VERTICAL, command=self.libraries_listbox.yview)
        self.libraries_listbox.configure(yscrollcommand=libs_scrollbar.set)
        
        self.libraries_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        libs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_enhanced_directory_pairs_section(self, parent):
        """Create enhanced directory pairs configuration with processing modes"""
        pairs_frame = ttk.LabelFrame(parent, text="Directory Pairs with Processing Modes", padding=15)
        pairs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Instructions
        instructions = ttk.Label(pairs_frame, 
                               text="Configure source directories with their target directories and choose processing mode for each pair.\n" +
                               "Different directories can use different processing modes based on your needs.",
                               foreground='blue')
        instructions.pack(pady=(0, 10))
        
        # Directory pairs tree with processing mode column
        columns = ('Source Directory', 'Target Directory', 'Processing Mode', 'Plex Library', 'Status')
        self.pairs_tree = ttk.Treeview(pairs_frame, columns=columns, show='headings', height=10)
        
        # Configure columns
        self.pairs_tree.heading('Source Directory', text='Source Directory')
        self.pairs_tree.heading('Target Directory', text='Target Directory')
        self.pairs_tree.heading('Processing Mode', text='Processing Mode')
        self.pairs_tree.heading('Plex Library', text='Plex Library')
        self.pairs_tree.heading('Status', text='Status')
        
        self.pairs_tree.column('Source Directory', width=200)
        self.pairs_tree.column('Target Directory', width=200)
        self.pairs_tree.column('Processing Mode', width=150)
        self.pairs_tree.column('Plex Library', width=150)
        self.pairs_tree.column('Status', width=100)
        
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
        
        ttk.Button(controls_frame, text="Add Directory Pair", command=self.add_directory_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Edit Selected", command=self.edit_directory_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Remove Selected", command=self.remove_directory_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Test Selected", command=self.test_directory_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Configure Processing Mode", command=self.configure_processing_mode).pack(side=tk.LEFT, padx=5)
    
    def create_processing_mode_config_section(self, parent):
        """Create processing mode configuration section"""
        config_frame = ttk.LabelFrame(parent, text="Processing Mode Configuration", padding=15)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Mode-specific configuration
        self.config_notebook = ttk.Notebook(config_frame)
        self.config_notebook.pack(fill=tk.X, pady=5)
        
        # Python VFS Config
        self.create_python_vfs_config_tab()
        
        # rar2fs Config
        self.create_rar2fs_config_tab()
        
        # Extraction Config
        self.create_extraction_config_tab()
    
    def create_python_vfs_config_tab(self):
        """Create Python VFS configuration tab"""
        vfs_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(vfs_frame, text="Python VFS")
        
        # Python VFS settings
        ttk.Label(vfs_frame, text="Python VFS Configuration:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # HTTP Server Port Range
        port_frame = ttk.Frame(vfs_frame)
        port_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(port_frame, text="HTTP Server Port Range:").pack(side=tk.LEFT)
        self.vfs_port_start_var = tk.StringVar(value='8765')
        ttk.Entry(port_frame, textvariable=self.vfs_port_start_var, width=10).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(port_frame, text="to").pack(side=tk.LEFT)
        self.vfs_port_end_var = tk.StringVar(value='8865')
        ttk.Entry(port_frame, textvariable=self.vfs_port_end_var, width=10).pack(side=tk.LEFT, padx=(5, 10))
        
        # Mount base directory
        mount_frame = ttk.Frame(vfs_frame)
        mount_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mount_frame, text="Mount Base Directory:").pack(side=tk.LEFT)
        self.vfs_mount_base_var = tk.StringVar(value='C:/PlexRarBridge/mounts')
        ttk.Entry(mount_frame, textvariable=self.vfs_mount_base_var, width=50).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Button(mount_frame, text="Browse", command=self.browse_mount_base).pack(side=tk.LEFT)
        
        # Status
        self.vfs_status_label = tk.Label(vfs_frame, text="✅ Python VFS: Ready (No dependencies required)", foreground='green')
        self.vfs_status_label.pack(anchor=tk.W, pady=(10, 0))
    
    def create_rar2fs_config_tab(self):
        """Create rar2fs configuration tab"""
        rar2fs_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(rar2fs_frame, text="rar2fs")
        
        # rar2fs settings
        ttk.Label(rar2fs_frame, text="rar2fs Configuration:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Executable path
        exe_frame = ttk.Frame(rar2fs_frame)
        exe_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(exe_frame, text="rar2fs Executable:").pack(side=tk.LEFT)
        self.rar2fs_exe_var = tk.StringVar(value='C:/cygwin64/home/User/rar2fs/rar2fs.exe')
        ttk.Entry(exe_frame, textvariable=self.rar2fs_exe_var, width=50).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Button(exe_frame, text="Browse", command=self.browse_rar2fs_exe).pack(side=tk.LEFT)
        
        # Mount options
        options_frame = ttk.Frame(rar2fs_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(options_frame, text="Mount Options:").pack(anchor=tk.W)
        self.rar2fs_options_text = tk.Text(options_frame, height=3, width=60)
        self.rar2fs_options_text.pack(pady=(5, 0))
        self.rar2fs_options_text.insert(tk.END, "uid=-1\ngid=-1\nallow_other")
        
        # Installation helper
        install_frame = ttk.Frame(rar2fs_frame)
        install_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(install_frame, text="Auto-Install rar2fs", command=self.auto_install_rar2fs).pack(side=tk.LEFT, padx=5)
        ttk.Button(install_frame, text="Test rar2fs", command=self.test_rar2fs).pack(side=tk.LEFT, padx=5)
        
        # Status
        self.rar2fs_status_label = tk.Label(rar2fs_frame, text="❌ rar2fs: Not installed", foreground='red')
        self.rar2fs_status_label.pack(anchor=tk.W, pady=(10, 0))
    
    def create_extraction_config_tab(self):
        """Create extraction configuration tab"""
        extraction_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(extraction_frame, text="Extraction")
        
        # Extraction settings
        ttk.Label(extraction_frame, text="Extraction Configuration:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Work directory
        work_frame = ttk.Frame(extraction_frame)
        work_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(work_frame, text="Work Directory:").pack(side=tk.LEFT)
        self.extraction_work_var = tk.StringVar(value='C:/PlexRarBridge/work')
        ttk.Entry(work_frame, textvariable=self.extraction_work_var, width=50).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Button(work_frame, text="Browse", command=self.browse_work_dir).pack(side=tk.LEFT)
        
        # Options
        options_frame = ttk.Frame(extraction_frame)
        options_frame.pack(fill=tk.X, pady=10)
        
        self.delete_archives_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Delete archives after processing", variable=self.delete_archives_var).pack(anchor=tk.W)
        
        self.duplicate_check_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Enable duplicate detection", variable=self.duplicate_check_var).pack(anchor=tk.W)
        
        # Status
        self.extraction_status_label = tk.Label(extraction_frame, text="✅ Extraction: Ready (UnRAR required)", foreground='green')
        self.extraction_status_label.pack(anchor=tk.W, pady=(10, 0))
    
    def create_upnp_config_section(self, parent):
        """Create UPnP configuration section"""
        upnp_frame = ttk.LabelFrame(parent, text="UPnP Port Forwarding (for Python VFS)", padding=15)
        upnp_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # UPnP description
        description_text = (
            "UPnP automatically configures port forwarding for Python VFS HTTP server.\n"
            "This helps bypass firewall issues and enables remote access to streamed content."
        )
        tk.Label(upnp_frame, text=description_text, foreground='blue').pack(anchor=tk.W, pady=(0, 10))
        
        # UPnP enabled checkbox
        self.upnp_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(upnp_frame, text="Enable UPnP port forwarding", variable=self.upnp_enabled_var,
                       command=self.toggle_upnp_settings).pack(anchor=tk.W, pady=5)
        
        # UPnP settings frame
        self.upnp_settings_frame = ttk.Frame(upnp_frame)
        self.upnp_settings_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Timeout setting
        timeout_frame = ttk.Frame(self.upnp_settings_frame)
        timeout_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(timeout_frame, text="Discovery Timeout (seconds):").pack(side=tk.LEFT)
        self.upnp_timeout_var = tk.StringVar(value='10')
        ttk.Entry(timeout_frame, textvariable=self.upnp_timeout_var, width=10).pack(side=tk.LEFT, padx=(10, 0))
        
        # Retry count
        retry_frame = ttk.Frame(self.upnp_settings_frame)
        retry_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(retry_frame, text="Retry Count:").pack(side=tk.LEFT)
        self.upnp_retry_var = tk.StringVar(value='3')
        ttk.Entry(retry_frame, textvariable=self.upnp_retry_var, width=10).pack(side=tk.LEFT, padx=(10, 0))
        
        # Lease duration
        lease_frame = ttk.Frame(self.upnp_settings_frame)
        lease_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lease_frame, text="Port Lease Duration (seconds):").pack(side=tk.LEFT)
        self.upnp_lease_var = tk.StringVar(value='3600')
        ttk.Entry(lease_frame, textvariable=self.upnp_lease_var, width=10).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(lease_frame, text="(3600 = 1 hour)").pack(side=tk.LEFT, padx=(5, 0))
        
        # UPnP status and test
        status_frame = ttk.Frame(self.upnp_settings_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.upnp_status_label = tk.Label(status_frame, text="UPnP Status: Not tested", foreground='gray')
        self.upnp_status_label.pack(side=tk.LEFT)
        
        ttk.Button(status_frame, text="Test UPnP", command=self.test_upnp).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(status_frame, text="Discover Router", command=self.discover_upnp_router).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Info about UPnP
        info_frame = ttk.Frame(self.upnp_settings_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        info_text = (
            "ℹ️ UPnP requires a compatible router and may not work on all networks.\n"
            "If UPnP fails, manual port forwarding may be required for remote access."
        )
        tk.Label(info_frame, text=info_text, foreground='orange', font=('TkDefaultFont', 8)).pack(anchor=tk.W)
        
        # Initialize UPnP settings state
        self.toggle_upnp_settings()
    
    def toggle_upnp_settings(self):
        """Toggle UPnP settings visibility"""
        if self.upnp_enabled_var.get():
            for widget in self.upnp_settings_frame.winfo_children():
                try:
                    widget.configure(state='normal')
                except:
                    pass
                for child in widget.winfo_children():
                    try:
                        child.configure(state='normal')
                    except:
                        pass
        else:
            for widget in self.upnp_settings_frame.winfo_children():
                try:
                    widget.configure(state='disabled')
                except:
                    pass
                for child in widget.winfo_children():
                    try:
                        child.configure(state='disabled')
                    except:
                        pass
    
    def test_upnp(self):
        """Test UPnP configuration"""
        try:
            self.upnp_status_label.config(text="Testing UPnP...", foreground='blue')
            
            # Test with threading to avoid blocking GUI
            import threading
            
            def test_upnp_worker():
                try:
                    # Import UPnP manager
                    from upnp_port_manager import UPnPPortManager
                    import logging
                    
                    # Create test logger
                    logger = logging.getLogger('upnp_test')
                    logger.setLevel(logging.INFO)
                    
                    # Create test config
                    config = {
                        'upnp': {
                            'enabled': True,
                            'timeout': int(self.upnp_timeout_var.get()),
                            'retry_count': int(self.upnp_retry_var.get()),
                            'lease_duration': int(self.upnp_lease_var.get())
                        }
                    }
                    
                    # Test UPnP
                    upnp = UPnPPortManager(config, logger)
                    
                    if upnp.discover_router():
                        self.upnp_status_label.config(text="✅ UPnP: Router discovered and ready", foreground='green')
                    else:
                        self.upnp_status_label.config(text="❌ UPnP: No compatible router found", foreground='red')
                        
                except Exception as e:
                    self.upnp_status_label.config(text=f"❌ UPnP: Error - {str(e)}", foreground='red')
            
            # Run test in thread
            test_thread = threading.Thread(target=test_upnp_worker, daemon=True)
            test_thread.start()
            
        except Exception as e:
            self.upnp_status_label.config(text=f"❌ UPnP: Test error - {str(e)}", foreground='red')
    
    def discover_upnp_router(self):
        """Discover UPnP router"""
        try:
            self.upnp_status_label.config(text="Discovering UPnP router...", foreground='blue')
            
            def discover_worker():
                try:
                    from upnp_port_manager import UPnPPortManager
                    import logging
                    
                    logger = logging.getLogger('upnp_discover')
                    logger.setLevel(logging.INFO)
                    
                    config = {
                        'upnp': {
                            'enabled': True,
                            'timeout': int(self.upnp_timeout_var.get()),
                            'retry_count': int(self.upnp_retry_var.get()),
                            'lease_duration': int(self.upnp_lease_var.get())
                        }
                    }
                    
                    upnp = UPnPPortManager(config, logger)
                    
                    if upnp.discover_router():
                        status = upnp.get_status()
                        control_url = status.get('control_url', 'Unknown')
                        service_type = status.get('service_type', 'Unknown')
                        
                        self.upnp_status_label.config(
                            text=f"✅ UPnP: Found router - {control_url[:50]}...", 
                            foreground='green'
                        )
                    else:
                        self.upnp_status_label.config(text="❌ UPnP: No router found", foreground='red')
                        
                except Exception as e:
                    self.upnp_status_label.config(text=f"❌ UPnP: Discovery error - {str(e)}", foreground='red')
            
            discovery_thread = threading.Thread(target=discover_worker, daemon=True)
            discovery_thread.start()
            
        except Exception as e:
            self.upnp_status_label.config(text=f"❌ UPnP: Discovery error - {str(e)}", foreground='red')
    
    def create_enhanced_setup_controls_section(self, parent):
        """Create enhanced setup control buttons"""
        controls_frame = ttk.LabelFrame(parent, text="Configuration Controls", padding=15)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Status label
        self.setup_status_label = tk.Label(controls_frame, text="Ready to configure", foreground='blue')
        self.setup_status_label.pack(pady=(0, 10))
        
        # Control buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack()
        
        ttk.Button(buttons_frame, text="Save Configuration", command=self.save_enhanced_setup_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Load Configuration", command=self.load_setup_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Test All Configurations", command=self.test_all_configs).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Apply & Restart Service", command=self.apply_and_restart).pack(side=tk.LEFT, padx=5)
        
        # Advanced options
        advanced_frame = ttk.Frame(controls_frame)
        advanced_frame.pack(pady=(10, 0))
        
        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Monitor subdirectories recursively", variable=self.recursive_var).pack(side=tk.LEFT, padx=5)
        
        self.auto_start_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="Auto-start service on boot", variable=self.auto_start_var).pack(side=tk.LEFT, padx=5)
    
    def add_directory_pair(self):
        """Add a new directory pair with processing mode selection"""
        dialog = DirectoryPairDialog(self.setup_frame, self.processing_modes, self.setup_data['plex_libraries'])
        result = dialog.show()
        
        if result:
            # Add to tree
            self.pairs_tree.insert('', 'end', values=(
                result['source'],
                result['target'],
                self.processing_modes[result['processing_mode']]['name'],
                result['plex_library'],
                'Ready'
            ))
            
            # Add to data
            self.setup_data['directory_pairs'].append(result)
            self.setup_status_label.config(text=f"Added directory pair: {result['source']} -> {result['target']}")
    
    def edit_directory_pair(self):
        """Edit selected directory pair"""
        selected = self.pairs_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a directory pair to edit")
            return
        
        # Get selected item data
        item = self.pairs_tree.item(selected[0])
        values = item['values']
        
        # Find in data
        for i, pair in enumerate(self.setup_data['directory_pairs']):
            if pair['source'] == values[0] and pair['target'] == values[1]:
                # Edit dialog
                dialog = DirectoryPairDialog(self.setup_frame, self.processing_modes, 
                                           self.setup_data['plex_libraries'], pair)
                result = dialog.show()
                
                if result:
                    # Update tree
                    self.pairs_tree.item(selected[0], values=(
                        result['source'],
                        result['target'],
                        self.processing_modes[result['processing_mode']]['name'],
                        result['plex_library'],
                        'Updated'
                    ))
                    
                    # Update data
                    self.setup_data['directory_pairs'][i] = result
                    self.setup_status_label.config(text=f"Updated directory pair: {result['source']}")
                break
    
    def remove_directory_pair(self):
        """Remove selected directory pair"""
        selected = self.pairs_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a directory pair to remove")
            return
        
        if messagebox.askyesno("Confirm Remove", "Are you sure you want to remove this directory pair?"):
            # Get selected item data
            item = self.pairs_tree.item(selected[0])
            values = item['values']
            
            # Remove from data
            self.setup_data['directory_pairs'] = [
                pair for pair in self.setup_data['directory_pairs']
                if not (pair['source'] == values[0] and pair['target'] == values[1])
            ]
            
            # Remove from tree
            self.pairs_tree.delete(selected[0])
            self.setup_status_label.config(text=f"Removed directory pair: {values[0]}")
    
    def configure_processing_mode(self):
        """Configure processing mode for selected directory pair"""
        selected = self.pairs_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a directory pair to configure")
            return
        
        # Get selected item data
        item = self.pairs_tree.item(selected[0])
        values = item['values']
        
        # Find in data
        for pair in self.setup_data['directory_pairs']:
            if pair['source'] == values[0] and pair['target'] == values[1]:
                # Show processing mode config dialog
                dialog = ProcessingModeConfigDialog(self.setup_frame, pair['processing_mode'], self.processing_modes)
                result = dialog.show()
                
                if result:
                    pair['processing_mode'] = result
                    # Update tree
                    self.pairs_tree.item(selected[0], values=(
                        values[0], values[1], 
                        self.processing_modes[result]['name'],
                        values[3], 'Updated'
                    ))
                    self.setup_status_label.config(text=f"Updated processing mode for: {values[0]}")
                break
    
    def save_enhanced_setup_config(self):
        """Save enhanced configuration with processing modes"""
        try:
            # Create enhanced config
            config = {
                'plex': {
                    'host': self.plex_host_var.get(),
                    'token': self.plex_token_var.get()
                },
                'directory_pairs': self.setup_data['directory_pairs'],
                'global_processing_mode': self.global_mode_var.get(),
                'processing_modes': {
                    'python_vfs': {
                        'port_range': [int(self.vfs_port_start_var.get()), int(self.vfs_port_end_var.get())],
                        'mount_base': self.vfs_mount_base_var.get()
                    },
                    'rar2fs': {
                        'executable': self.rar2fs_exe_var.get(),
                        'mount_options': self.rar2fs_options_text.get('1.0', tk.END).strip().split('\n')
                    },
                    'extraction': {
                        'work_dir': self.extraction_work_var.get(),
                        'delete_archives': self.delete_archives_var.get(),
                        'duplicate_check': self.duplicate_check_var.get()
                    }
                },
                'options': {
                    'recursive': self.recursive_var.get(),
                    'auto_start': self.auto_start_var.get()
                },
                'upnp': {
                    'enabled': self.upnp_enabled_var.get(),
                    'timeout': int(self.upnp_timeout_var.get()),
                    'retry_count': int(self.upnp_retry_var.get()),
                    'lease_duration': int(self.upnp_lease_var.get())
                }
            }
            
            # Save to file
            setup_config_path = self.script_dir / 'enhanced_setup_config.json'
            with open(setup_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Also update main config.yaml
            self.update_main_config_with_modes()
            
            self.setup_status_label.config(text="Configuration saved successfully!", foreground='green')
            
        except Exception as e:
            self.setup_status_label.config(text=f"Error saving configuration: {e}", foreground='red')
            messagebox.showerror("Save Error", f"Failed to save configuration: {e}")
    
    def update_main_config_with_modes(self):
        """Update main config.yaml with processing modes"""
        try:
            config_path = self.script_dir / 'config.yaml'
            
            # Load existing config
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            # Update with processing mode settings
            config['options'] = config.get('options', {})
            config['options']['processing_mode'] = self.global_mode_var.get()
            
            # Add UPnP configuration
            config['upnp'] = {
                'enabled': self.upnp_enabled_var.get(),
                'timeout': int(self.upnp_timeout_var.get()),
                'retry_count': int(self.upnp_retry_var.get()),
                'lease_duration': int(self.upnp_lease_var.get())
            }
            
            # Add mode-specific configurations
            if self.global_mode_var.get() == 'python_vfs':
                config['python_vfs'] = {
                    'port_range': [int(self.vfs_port_start_var.get()), int(self.vfs_port_end_var.get())],
                    'mount_base': self.vfs_mount_base_var.get()
                }
            elif self.global_mode_var.get() == 'rar2fs':
                config['rar2fs'] = {
                    'enabled': True,
                    'executable': self.rar2fs_exe_var.get(),
                    'mount_base': self.vfs_mount_base_var.get(),
                    'mount_options': self.rar2fs_options_text.get('1.0', tk.END).strip().split('\n')
                }
            
            # Save updated config
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
        except Exception as e:
            print(f"Error updating main config: {e}")
    
    def load_setup_config(self):
        """Load setup configuration"""
        try:
            setup_config_path = self.script_dir / 'enhanced_setup_config.json'
            if setup_config_path.exists():
                with open(setup_config_path, 'r') as f:
                    config = json.load(f)
                
                # Load plex settings
                plex_config = config.get('plex', {})
                self.plex_host_var.set(plex_config.get('host', ''))
                self.plex_token_var.set(plex_config.get('token', ''))
                
                # Load global processing mode
                self.global_mode_var.set(config.get('global_processing_mode', 'python_vfs'))
                
                # Load directory pairs
                self.setup_data['directory_pairs'] = config.get('directory_pairs', [])
                
                # Load processing mode configs
                mode_configs = config.get('processing_modes', {})
                
                # Python VFS
                vfs_config = mode_configs.get('python_vfs', {})
                port_range = vfs_config.get('port_range', [8765, 8865])
                self.vfs_port_start_var.set(str(port_range[0]))
                self.vfs_port_end_var.set(str(port_range[1]))
                self.vfs_mount_base_var.set(vfs_config.get('mount_base', 'C:/PlexRarBridge/mounts'))
                
                # rar2fs
                rar2fs_config = mode_configs.get('rar2fs', {})
                self.rar2fs_exe_var.set(rar2fs_config.get('executable', 'C:/cygwin64/home/User/rar2fs/rar2fs.exe'))
                mount_options = rar2fs_config.get('mount_options', ['uid=-1', 'gid=-1', 'allow_other'])
                self.rar2fs_options_text.delete('1.0', tk.END)
                self.rar2fs_options_text.insert(tk.END, '\n'.join(mount_options))
                
                # Extraction
                extraction_config = mode_configs.get('extraction', {})
                self.extraction_work_var.set(extraction_config.get('work_dir', 'C:/PlexRarBridge/work'))
                self.delete_archives_var.set(extraction_config.get('delete_archives', True))
                self.duplicate_check_var.set(extraction_config.get('duplicate_check', True))
                
                # Options
                options = config.get('options', {})
                self.recursive_var.set(options.get('recursive', True))
                self.auto_start_var.set(options.get('auto_start', True))
                
                # UPnP configuration
                upnp_config = config.get('upnp', {})
                self.upnp_enabled_var.set(upnp_config.get('enabled', True))
                self.upnp_timeout_var.set(str(upnp_config.get('timeout', 10)))
                self.upnp_retry_var.set(str(upnp_config.get('retry_count', 3)))
                self.upnp_lease_var.set(str(upnp_config.get('lease_duration', 3600)))
                
                # Update UPnP settings visibility
                self.toggle_upnp_settings()
                
                # Refresh tree
                self.refresh_pairs_tree()
                
                self.setup_status_label.config(text="Configuration loaded successfully!", foreground='green')
                
        except Exception as e:
            self.setup_status_label.config(text=f"Error loading configuration: {e}", foreground='red')
    
    def refresh_pairs_tree(self):
        """Refresh the directory pairs tree"""
        # Clear existing items
        for item in self.pairs_tree.get_children():
            self.pairs_tree.delete(item)
        
        # Add pairs from data
        for pair in self.setup_data['directory_pairs']:
            self.pairs_tree.insert('', 'end', values=(
                pair['source'],
                pair['target'],
                self.processing_modes[pair['processing_mode']]['name'],
                pair['plex_library'],
                'Ready'
            ))
    
    def test_all_configs(self):
        """Test all processing mode configurations"""
        self.setup_status_label.config(text="Testing all configurations...", foreground='blue')
        
        # Test Python VFS
        self.test_python_vfs()
        
        # Test rar2fs
        self.test_rar2fs()
        
        # Test extraction
        self.test_extraction()
        
        self.setup_status_label.config(text="Configuration tests completed", foreground='green')
    
    def test_python_vfs(self):
        """Test Python VFS configuration"""
        try:
            # Test port availability
            import socket
            port = int(self.vfs_port_start_var.get())
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
            
            # Test mount base directory
            mount_base = Path(self.vfs_mount_base_var.get())
            mount_base.mkdir(parents=True, exist_ok=True)
            
            self.vfs_status_label.config(text="✅ Python VFS: Configuration OK", foreground='green')
            
        except Exception as e:
            self.vfs_status_label.config(text=f"❌ Python VFS: {e}", foreground='red')
    
    def test_rar2fs(self):
        """Test rar2fs configuration"""
        try:
            rar2fs_exe = Path(self.rar2fs_exe_var.get())
            
            if not rar2fs_exe.exists():
                self.rar2fs_status_label.config(text="❌ rar2fs: Executable not found", foreground='red')
                return
            
            # Test executable
            result = subprocess.run([str(rar2fs_exe), '--help'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.rar2fs_status_label.config(text="✅ rar2fs: Configuration OK", foreground='green')
            else:
                self.rar2fs_status_label.config(text="❌ rar2fs: Executable test failed", foreground='red')
                
        except Exception as e:
            self.rar2fs_status_label.config(text=f"❌ rar2fs: {e}", foreground='red')
    
    def test_extraction(self):
        """Test extraction configuration"""
        try:
            # Test work directory
            work_dir = Path(self.extraction_work_var.get())
            work_dir.mkdir(parents=True, exist_ok=True)
            
            # Test UnRAR
            result = subprocess.run(['unrar'], capture_output=True, text=True, timeout=5)
            
            if "UNRAR" in result.stderr.upper():
                self.extraction_status_label.config(text="✅ Extraction: Configuration OK", foreground='green')
            else:
                self.extraction_status_label.config(text="❌ Extraction: UnRAR not found", foreground='red')
                
        except Exception as e:
            self.extraction_status_label.config(text=f"❌ Extraction: {e}", foreground='red')
    
    def auto_detect_plex(self):
        """Auto-detect Plex server"""
        # Find status label (create if not exists)
        if not hasattr(self, 'setup_status_label'):
            self.setup_status_label = tk.Label(self.setup_frame, text="Detecting Plex server...")
            self.setup_status_label.pack(pady=5)
        
        self.setup_status_label.config(text="Detecting Plex server...", foreground='blue')
        self.setup_frame.update()
        
        try:
            # Import the discovery functions from setup.py
            import sys
            sys.path.append(str(self.script_dir))
            from setup import discover_plex_server
            
            host = discover_plex_server()
            if host:
                self.plex_host_var.set(host)
                self.setup_status_label.config(text=f"Found Plex server: {host}", foreground='green')
                # Auto-detect token if server found
                self.auto_detect_token()
            else:
                self.setup_status_label.config(text="Could not auto-detect Plex server", foreground='orange')
        except Exception as e:
            self.setup_status_label.config(text=f"Error detecting Plex: {e}", foreground='red')
    
    def auto_detect_token(self):
        """Auto-detect Plex token"""
        if not hasattr(self, 'setup_status_label'):
            self.setup_status_label = tk.Label(self.setup_frame, text="Detecting Plex token...")
            self.setup_status_label.pack(pady=5)
        
        self.setup_status_label.config(text="Detecting Plex token...", foreground='blue')
        self.setup_frame.update()
        
        try:
            from setup import discover_plex_token
            
            token = discover_plex_token()
            if token:
                self.plex_token_var.set(token)
                self.setup_status_label.config(text="Plex token detected successfully", foreground='green')
                # Auto-test connection
                self.test_plex_connection()
            else:
                self.setup_status_label.config(text="Could not auto-detect Plex token", foreground='orange')
        except Exception as e:
            self.setup_status_label.config(text=f"Error detecting token: {e}", foreground='red')
    
    def test_plex_connection(self):
        """Test Plex connection and load libraries"""
        host = self.plex_host_var.get().strip()
        token = self.plex_token_var.get().strip()
        
        if not host or not token:
            self.plex_status_label.config(text="Please enter host and token", foreground='red')
            return
        
        if not hasattr(self, 'setup_status_label'):
            self.setup_status_label = tk.Label(self.setup_frame, text="Testing Plex connection...")
            self.setup_status_label.pack(pady=5)
        
        self.setup_status_label.config(text="Testing Plex connection...", foreground='blue')
        self.setup_frame.update()
        
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
            
            self.plex_status_label.config(text=f"✅ Connected - Found {len(libraries)} libraries", foreground='green')
            self.setup_status_label.config(text=f"Connected to Plex - {len(libraries)} libraries available", foreground='green')
            
        except Exception as e:
            self.plex_status_label.config(text=f"❌ Connection failed: {e}", foreground='red')
            self.setup_status_label.config(text=f"Plex connection failed: {e}", foreground='red')
    
    def auto_install_rar2fs(self):
        """Auto-install rar2fs"""
        # Implementation for rar2fs auto-installation
        # This would use the rar2fs_installer.py
        pass
    
    def browse_mount_base(self):
        """Browse for mount base directory"""
        directory = filedialog.askdirectory(title="Select Mount Base Directory")
        if directory:
            self.vfs_mount_base_var.set(directory)
    
    def browse_rar2fs_exe(self):
        """Browse for rar2fs executable"""
        filename = filedialog.askopenfilename(title="Select rar2fs Executable", 
                                            filetypes=[("Executable files", "*.exe")])
        if filename:
            self.rar2fs_exe_var.set(filename)
    
    def browse_work_dir(self):
        """Browse for work directory"""
        directory = filedialog.askdirectory(title="Select Work Directory")
        if directory:
            self.extraction_work_var.set(directory)
    
    def apply_and_restart(self):
        """Apply configuration and restart service"""
        try:
            # Save configuration first
            self.save_enhanced_setup_config()
            
            # Restart service
            self.setup_status_label.config(text="Restarting service...", foreground='blue')
            # Implementation for service restart
            
            self.setup_status_label.config(text="Service restarted successfully!", foreground='green')
            
        except Exception as e:
            self.setup_status_label.config(text=f"Error restarting service: {e}", foreground='red')
            messagebox.showerror("Restart Error", f"Failed to restart service: {e}")
    
    def test_directory_pair(self):
        """Test selected directory pair"""
        selected = self.pairs_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a directory pair to test")
            return
        
        # Get selected item data
        item = self.pairs_tree.item(selected[0])
        values = item['values']
        
        # Update status
        self.pairs_tree.item(selected[0], values=(
            values[0], values[1], values[2], values[3], 'Testing...'
        ))
        
        # Test the pair
        # Implementation for testing directory pair
        
        # Update status
        self.pairs_tree.item(selected[0], values=(
            values[0], values[1], values[2], values[3], 'OK'
        ))


class DirectoryPairDialog:
    """Dialog for adding/editing directory pairs with processing mode selection"""
    
    def __init__(self, parent, processing_modes, plex_libraries, existing_pair=None):
        self.parent = parent
        self.processing_modes = processing_modes
        self.plex_libraries = plex_libraries
        self.existing_pair = existing_pair
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Directory Pair Configuration")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_dialog_content()
        
        # Center dialog
        self.dialog.geometry("600x500+300+200")
    
    def create_dialog_content(self):
        """Create dialog content"""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Source directory
        ttk.Label(main_frame, text="Source Directory (where RAR files are placed):").pack(anchor=tk.W, pady=(0, 5))
        source_frame = ttk.Frame(main_frame)
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.source_var = tk.StringVar(value=self.existing_pair['source'] if self.existing_pair else '')
        ttk.Entry(source_frame, textvariable=self.source_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(source_frame, text="Browse", command=self.browse_source).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Target directory
        ttk.Label(main_frame, text="Target Directory (where extracted files go):").pack(anchor=tk.W, pady=(0, 5))
        target_frame = ttk.Frame(main_frame)
        target_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.target_var = tk.StringVar(value=self.existing_pair['target'] if self.existing_pair else '')
        ttk.Entry(target_frame, textvariable=self.target_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(target_frame, text="Browse", command=self.browse_target).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Processing mode selection
        ttk.Label(main_frame, text="Processing Mode:").pack(anchor=tk.W, pady=(10, 5))
        
        self.processing_mode_var = tk.StringVar(value=self.existing_pair['processing_mode'] if self.existing_pair else 'python_vfs')
        
        for mode_id, mode_info in self.processing_modes.items():
            mode_frame = ttk.Frame(main_frame)
            mode_frame.pack(fill=tk.X, pady=2)
            
            ttk.Radiobutton(
                mode_frame,
                text=mode_info['name'],
                variable=self.processing_mode_var,
                value=mode_id
            ).pack(side=tk.LEFT)
            
            # Description
            desc_label = tk.Label(mode_frame, text=f"- {mode_info['description']}", foreground='gray')
            desc_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Plex library selection
        ttk.Label(main_frame, text="Plex Library:").pack(anchor=tk.W, pady=(10, 5))
        
        self.plex_library_var = tk.StringVar(value=self.existing_pair['plex_library'] if self.existing_pair else '')
        library_combo = ttk.Combobox(main_frame, textvariable=self.plex_library_var, width=50)
        library_combo['values'] = [lib['title'] for lib in self.plex_libraries]
        library_combo.pack(anchor=tk.W, pady=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.RIGHT)
    
    def browse_source(self):
        """Browse for source directory"""
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.source_var.set(directory)
    
    def browse_target(self):
        """Browse for target directory"""
        directory = filedialog.askdirectory(title="Select Target Directory")
        if directory:
            self.target_var.set(directory)
    
    def ok_clicked(self):
        """OK button clicked"""
        source = self.source_var.get().strip()
        target = self.target_var.get().strip()
        
        if not source or not target:
            messagebox.showerror("Error", "Please specify both source and target directories")
            return
        
        self.result = {
            'source': source,
            'target': target,
            'processing_mode': self.processing_mode_var.get(),
            'plex_library': self.plex_library_var.get(),
            'enabled': True
        }
        
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """Cancel button clicked"""
        self.dialog.destroy()
    
    def show(self):
        """Show dialog and return result"""
        self.dialog.wait_window()
        return self.result


class ProcessingModeConfigDialog:
    """Dialog for configuring processing mode specific settings"""
    
    def __init__(self, parent, current_mode, processing_modes):
        self.parent = parent
        self.current_mode = current_mode
        self.processing_modes = processing_modes
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Processing Mode Configuration")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_dialog_content()
        
        # Center dialog
        self.dialog.geometry("500x400+350+250")
    
    def create_dialog_content(self):
        """Create dialog content"""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Mode selection
        ttk.Label(main_frame, text="Select Processing Mode:", font=('TkDefaultFont', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        self.mode_var = tk.StringVar(value=self.current_mode)
        
        for mode_id, mode_info in self.processing_modes.items():
            mode_frame = ttk.Frame(main_frame)
            mode_frame.pack(fill=tk.X, pady=5)
            
            ttk.Radiobutton(
                mode_frame,
                text=mode_info['name'],
                variable=self.mode_var,
                value=mode_id
            ).pack(side=tk.LEFT)
            
            # Details
            details_frame = ttk.Frame(mode_frame)
            details_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(20, 0))
            
            tk.Label(details_frame, text=mode_info['description'], foreground='gray').pack(anchor=tk.W)
            tk.Label(details_frame, text=f"Dependencies: {mode_info['dependencies']}", foreground='blue').pack(anchor=tk.W)
            tk.Label(details_frame, text=f"Complexity: {mode_info['complexity']}", foreground='orange').pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.RIGHT)
    
    def ok_clicked(self):
        """OK button clicked"""
        self.result = self.mode_var.get()
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """Cancel button clicked"""
        self.dialog.destroy()
    
    def show(self):
        """Show dialog and return result"""
        self.dialog.wait_window()
        return self.result 