#!/usr/bin/env python3
"""
SSH Connection Manager for Orange Pi CM4 to Remote Server
WARNING: Using password authentication is not recommended for production!
Consider using SSH key-based authentication instead.
"""

import subprocess
import sys
import os

# Server Configuration
SERVER_HOST = "159.223.45.101"
SERVER_USER = "root"
SERVER_PASSWORD = "pass123WORD"  # INSECURE! Use SSH keys instead

def check_ssh_installed():
    """Check if SSH client is installed"""
    try:
        subprocess.run(['which', 'ssh'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ SSH client not installed!")
        print("Install with: sudo apt install openssh-client")
        return False

def check_sshpass_installed():
    """Check if sshpass is installed (needed for password auth)"""
    try:
        subprocess.run(['which', 'sshpass'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        print("⚠️  sshpass not installed (needed for password authentication)")
        print("Install with: sudo apt install sshpass")
        return False

def connect_ssh_interactive():
    """Connect to server with interactive SSH session"""
    print(f"Connecting to {SERVER_USER}@{SERVER_HOST}...")
    print("⚠️  WARNING: Using password authentication (insecure!)")
    
    # Use sshpass for password authentication
    cmd = [
        'sshpass', '-p', SERVER_PASSWORD,
        'ssh',
        '-o', 'StrictHostKeyChecking=no',  # Skip host key verification (first time)
        '-o', 'UserKnownHostsFile=/dev/null',  # Don't save to known_hosts
        f'{SERVER_USER}@{SERVER_HOST}'
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nConnection closed.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

def execute_remote_command(command):
    """Execute a single command on remote server"""
    print(f"Executing on {SERVER_HOST}: {command}")
    
    cmd = [
        'sshpass', '-p', SERVER_PASSWORD,
        'ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'{SERVER_USER}@{SERVER_HOST}',
        command
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Command failed: {e}")
        return False

def upload_file(local_path, remote_path):
    """Upload file to remote server using SCP"""
    print(f"Uploading {local_path} to {SERVER_HOST}:{remote_path}")
    
    cmd = [
        'sshpass', '-p', SERVER_PASSWORD,
        'scp',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        local_path,
        f'{SERVER_USER}@{SERVER_HOST}:{remote_path}'
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ Upload successful!")
        return True
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False

def download_file(remote_path, local_path):
    """Download file from remote server using SCP"""
    print(f"Downloading {SERVER_HOST}:{remote_path} to {local_path}")
    
    cmd = [
        'sshpass', '-p', SERVER_PASSWORD,
        'scp',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'{SERVER_USER}@{SERVER_HOST}:{remote_path}',
        local_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ Download successful!")
        return True
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def setup_ssh_key_auth():
    """Setup SSH key-based authentication (RECOMMENDED)"""
    print("="*60)
    print("SETTING UP SSH KEY AUTHENTICATION (Recommended)")
    print("="*60)
    
    key_path = os.path.expanduser("~/.ssh/id_rsa")
    
    # Check if key exists
    if not os.path.exists(key_path):
        print("\n1. Generating SSH key pair...")
        subprocess.run(['ssh-keygen', '-t', 'rsa', '-b', '4096', '-f', key_path, '-N', ''])
        print("✓ SSH key generated!")
    else:
        print(f"✓ SSH key already exists: {key_path}")
    
    # Copy public key to server
    print("\n2. Copying public key to server...")
    pub_key_path = f"{key_path}.pub"
    
    cmd = [
        'sshpass', '-p', SERVER_PASSWORD,
        'ssh-copy-id',
        '-o', 'StrictHostKeyChecking=no',
        '-i', pub_key_path,
        f'{SERVER_USER}@{SERVER_HOST}'
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ SSH key copied to server!")
        print("\n" + "="*60)
        print("✓ SETUP COMPLETE!")
        print("="*60)
        print("You can now connect without password:")
        print(f"  ssh {SERVER_USER}@{SERVER_HOST}")
        print("\nNOW YOU SHOULD:")
        print("1. Change your server password")
        print("2. Disable password authentication on server")
        print("="*60)
        return True
    except Exception as e:
        print(f"❌ Failed to copy SSH key: {e}")
        return False

def show_menu():
    """Show interactive menu"""
    print("\n" + "="*60)
    print("SSH CONNECTION MANAGER")
    print("="*60)
    print(f"Server: {SERVER_USER}@{SERVER_HOST}")
    print("="*60)
    print("1. Connect (interactive SSH)")
    print("2. Execute remote command")
    print("3. Upload file to server")
    print("4. Download file from server")
    print("5. Setup SSH key authentication (RECOMMENDED)")
    print("6. Test connection")
    print("0. Exit")
    print("="*60)

def main():
    # Check requirements
    if not check_ssh_installed():
        sys.exit(1)
    
    if not check_sshpass_installed():
        sys.exit(1)
    
    while True:
        show_menu()
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '1':
            connect_ssh_interactive()
        
        elif choice == '2':
            command = input("Enter command to execute: ").strip()
            if command:
                execute_remote_command(command)
        
        elif choice == '3':
            local_path = input("Enter local file path: ").strip()
            remote_path = input("Enter remote destination path: ").strip()
            if local_path and remote_path:
                upload_file(local_path, remote_path)
        
        elif choice == '4':
            remote_path = input("Enter remote file path: ").strip()
            local_path = input("Enter local destination path: ").strip()
            if remote_path and local_path:
                download_file(remote_path, local_path)
        
        elif choice == '5':
            setup_ssh_key_auth()
        
        elif choice == '6':
            print("Testing connection...")
            if execute_remote_command("hostname && uptime"):
                print("✓ Connection successful!")
            else:
                print("❌ Connection failed!")
        
        elif choice == '0':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)

