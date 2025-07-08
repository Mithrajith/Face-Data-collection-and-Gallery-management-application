import subprocess
import os
from typing import Dict, Any

from config.settings import BASE_DIR, COLLECTION_APP_HOST, COLLECTION_APP_PORT

# Global variable to track collection app process
collection_app_process_name = "data-collection-app"  # Name of the process in PM2

def start_collection_app() -> Dict[str, Any]:
    """Start the face collection application server using the launch script"""
    try:
        # Check if already running in PM2
        status_cmd = subprocess.run(
            ["pm2", "list"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # Check if our app is in the list and online
        if collection_app_process_name in status_cmd.stdout and "online" in status_cmd.stdout:
            return {
                "success": True,
                "message": "Face Collection App is already running in PM2",
                "process_name": collection_app_process_name
            }
        
        # Path to the launch script
        launch_script = os.path.join(BASE_DIR, "data_collection", "launch.sh")
        
        # Execute the launch script
        start_cmd = subprocess.run(
            ["/bin/bash", launch_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if start_cmd.returncode == 0:
            return {
                "success": True,
                "message": "Face Collection App started successfully",
                "process_name": collection_app_process_name
            }
        else:
            return {
                "success": False,
                "message": f"Failed to start Face Collection App: {start_cmd.stderr}"
            }
                
    except Exception as e:
        return {
            "success": False,
            "message": f"Error starting Face Collection App: {str(e)}"
        }

def stop_collection_app() -> Dict[str, Any]:
    """Stop the face collection application server using PM2"""
    try:
        # Check if running in PM2
        status_cmd = subprocess.run(
            ["pm2", "list"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # If process is not in the list, it's not running
        if collection_app_process_name not in status_cmd.stdout:
            return {
                "success": True,
                "message": "Face Collection App was not running"
            }
        
        # Stop the app with PM2
        stop_cmd = subprocess.run(
            ["pm2", "delete", collection_app_process_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if stop_cmd.returncode == 0:
            return {
                "success": True,
                "message": f"Face Collection App stopped successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to stop Face Collection App: {stop_cmd.stderr}"
            }
                
    except Exception as e:
        return {
            "success": False,
            "message": f"Error stopping Face Collection App: {str(e)}"
        }

def get_collection_app_status() -> Dict[str, Any]:
    """Check if the face collection application is running using PM2"""
    try:
        # Get status from PM2
        status_cmd = subprocess.run(
            ["pm2", "list"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # Check if our process is in the list and running
        is_running = collection_app_process_name in status_cmd.stdout and "online" in status_cmd.stdout
        
        if is_running:
            # Get more details if needed
            detail_cmd = subprocess.run(
                ["pm2", "describe", collection_app_process_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return {
                "running": True,
                "process_name": collection_app_process_name,
                "details": detail_cmd.stdout
            }
        else:
            return {
                "running": False,
                "process_name": collection_app_process_name
            }
                
    except Exception as e:
        return {
            "running": False,
            "error": str(e)
        }

def get_collection_app_config() -> Dict[str, Any]:
    """Get face collection app configuration"""
    return {
        "host": COLLECTION_APP_HOST,
        "port": COLLECTION_APP_PORT
    }
