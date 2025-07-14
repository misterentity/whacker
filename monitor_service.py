#!/usr/bin/env python3
"""
Service monitoring script for Plex RAR Bridge
Shows current status and recent activity
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import re

class ServiceMonitor:
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.log_file = self.script_dir / "logs" / "bridge.log"
        self.service_name = "PlexRarBridge"
    
    def check_service_status(self):
        """Check if service is running"""
        try:
            result = subprocess.run(['sc', 'query', self.service_name], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and 'RUNNING' in result.stdout:
                return "🟢 RUNNING"
            elif result.returncode == 0 and 'STOPPED' in result.stdout:
                return "🔴 STOPPED"
            else:
                return "❓ UNKNOWN"
        except:
            return "❌ ERROR"
    
    def get_process_status(self):
        """Check if Python process is running"""
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                                  capture_output=True, text=True)
            if 'plex_rar_bridge.py' in result.stdout:
                return "🟢 PROCESS ACTIVE"
            else:
                return "🔴 PROCESS NOT FOUND"
        except:
            return "❓ UNKNOWN"
    
    def get_log_stats(self):
        """Analyze recent log activity"""
        if not self.log_file.exists():
            return {"status": "❌ NO LOG FILE", "lines": 0, "recent": []}
        
        try:
            # Read last 100 lines
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            # Count activity types
            processed = len([l for l in recent_lines if 'Successfully processed' in l])
            errors = len([l for l in recent_lines if 'ERROR' in l])
            warnings = len([l for l in recent_lines if 'WARNING' in l])
            
            # Get last few important entries
            important = []
            for line in reversed(recent_lines[-20:]):
                if any(keyword in line for keyword in [
                    'Started monitoring', 'Processing existing', 'Successfully processed',
                    'ERROR', 'Started monitoring directory', 'ready for new files'
                ]):
                    important.append(line.strip())
                    if len(important) >= 5:
                        break
            
            return {
                "status": "✅ ACTIVE",
                "total_lines": len(lines),
                "processed": processed,
                "errors": errors,
                "warnings": warnings,
                "recent": list(reversed(important))
            }
        except Exception as e:
            return {"status": f"❌ ERROR: {e}", "lines": 0, "recent": []}
    
    def check_directories(self):
        """Check if required directories exist"""
        config_file = self.script_dir / "config.yaml"
        if not config_file.exists():
            return {"status": "❌ NO CONFIG", "dirs": []}
        
        try:
            import yaml
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            dirs = []
            for key, path in config.get('paths', {}).items():
                path_obj = Path(path)
                if path_obj.exists():
                    dirs.append(f"✅ {key}: {path}")
                else:
                    dirs.append(f"❌ {key}: {path}")
            
            return {"status": "✅ CHECKED", "dirs": dirs}
        except Exception as e:
            return {"status": f"❌ ERROR: {e}", "dirs": []}
    
    def display_status(self):
        """Display comprehensive status"""
        print("=" * 60)
        print("🔍 PLEX RAR BRIDGE - SERVICE MONITOR")
        print("=" * 60)
        
        # Service Status
        service_status = self.check_service_status()
        process_status = self.get_process_status()
        print(f"\n📊 SERVICE STATUS:")
        print(f"   Windows Service: {service_status}")
        print(f"   Python Process:  {process_status}")
        
        # Log Analysis
        log_stats = self.get_log_stats()
        print(f"\n📋 LOG ANALYSIS:")
        print(f"   Status: {log_stats['status']}")
        if 'total_lines' in log_stats:
            print(f"   Total log lines: {log_stats['total_lines']:,}")
            print(f"   Recent processed: {log_stats['processed']}")
            print(f"   Recent errors: {log_stats['errors']}")
            print(f"   Recent warnings: {log_stats['warnings']}")
        
        # Recent Activity
        if log_stats.get('recent'):
            print(f"\n🕐 RECENT ACTIVITY:")
            for entry in log_stats['recent']:
                # Extract timestamp and message
                parts = entry.split(' ', 2)
                if len(parts) >= 3:
                    timestamp = f"{parts[0]} {parts[1]}"
                    message = parts[2]
                    print(f"   {timestamp}: {message}")
        
        # Directory Status
        dir_status = self.check_directories()
        print(f"\n📁 DIRECTORIES:")
        print(f"   Status: {dir_status['status']}")
        for dir_info in dir_status['dirs']:
            print(f"   {dir_info}")
        
        # Usage Tips
        print(f"\n💡 MONITORING TIPS:")
        print(f"   Live logs: Get-Content logs\\bridge.log -Wait -Tail 10")
        print(f"   Service mgmt: python install_service_improved.py")
        print(f"   Full test: python test_installation.py")
        print(f"   Plex test: python test_plex_detection.py")
        
        print("\n" + "=" * 60)
    
    def run(self):
        """Main monitoring function"""
        try:
            self.display_status()
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
        except Exception as e:
            print(f"Error: {e}")
            
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    monitor = ServiceMonitor()
    monitor.run() 