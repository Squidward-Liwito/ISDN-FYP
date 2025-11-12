# Orange Pi CM4 → Server Connection Scripts

✅ **Connection Tested Successfully!**  
Server: `root@159.223.45.101` (smartFridge)

---

## ⚠️ CRITICAL SECURITY WARNINGS

### 1. **YOU SHARED YOUR ROOT PASSWORD PUBLICLY!**
- The password `pass123WORD` is now compromised
- **Action Required**: Change it immediately on your server:
  ```bash
  passwd  # Run this on the server
  ```

### 2. **Root Access with Password Authentication is DANGEROUS**
- Your server can be brute-forced
- Bots constantly scan for SSH servers
- **STRONGLY RECOMMENDED**: Use SSH keys instead (see below)

---

## 📁 Files Created

### 1. `connect_server.py` - Full-Featured Connection Manager
Interactive Python script with menu:
- Connect to server (interactive shell)
- Execute remote commands
- Upload/download files
- **Setup SSH key authentication (RECOMMENDED!)**
- Test connection

### 2. `quick_connect.sh` - Quick One-Line Connect
Simple bash script for instant connection

---

## 🚀 Usage

### Method 1: Interactive Python Manager (Recommended)
```bash
python3 /home/orangepi/Desktop/connect_server.py
```

**Menu Options:**
```
1. Connect (interactive SSH)       - Open SSH terminal on server
2. Execute remote command          - Run single command
3. Upload file to server           - SCP upload
4. Download file from server       - SCP download
5. Setup SSH key authentication    - ⭐ DO THIS FIRST!
6. Test connection                 - Verify connectivity
0. Exit
```

### Method 2: Quick Connect Script
```bash
/home/orangepi/Desktop/quick_connect.sh
```
Instantly connects you to the server shell.

### Method 3: Direct Command Line
```bash
# Interactive connection
sshpass -p 'pass123WORD' ssh root@159.223.45.101

# Execute single command
sshpass -p 'pass123WORD' ssh root@159.223.45.101 "ls -la"

# Upload file
sshpass -p 'pass123WORD' scp myfile.txt root@159.223.45.101:/root/

# Download file
sshpass -p 'pass123WORD' scp root@159.223.45.101:/root/myfile.txt ./
```

---

## 🔐 SETUP SSH KEY AUTHENTICATION (Do This NOW!)

**Why?**
- ✅ No password needed
- ✅ Much more secure
- ✅ Can disable password login on server
- ✅ Automated scripts work safely

**How to Setup:**

### Step 1: Run the setup in Python script
```bash
python3 connect_server.py
# Choose option: 5
```

### Step 2: On your server, disable password authentication
```bash
# SSH to server first
ssh root@159.223.45.101

# Edit SSH config
nano /etc/ssh/sshd_config

# Change these lines:
PasswordAuthentication no
PermitRootLogin prohibit-password

# Restart SSH
systemctl restart sshd
```

### Step 3: Test key-based connection
```bash
# Should work without password!
ssh root@159.223.45.101
```

---

## 📤 Example Use Cases

### Upload Camera Photo to Server
```python
from connect_server import upload_file

# After taking photo with camera
upload_file("/home/orangepi/fridge_photos/photo.jpg", "/root/photos/")
```

### Execute Remote Command
```python
from connect_server import execute_remote_command

# Check server disk space
execute_remote_command("df -h")

# Check server temperature
execute_remote_command("cat /sys/class/thermal/thermal_zone0/temp")
```

### Automated Backup Script
```bash
#!/bin/bash
# Backup photos to server every hour

PHOTO_DIR="/home/orangepi/fridge_photos"
SERVER="root@159.223.45.101"
REMOTE_DIR="/root/backups/fridge_photos"

sshpass -p 'pass123WORD' ssh $SERVER "mkdir -p $REMOTE_DIR"
sshpass -p 'pass123WORD' scp -r $PHOTO_DIR/* $SERVER:$REMOTE_DIR/

echo "Backup completed: $(date)"
```

---

## 🔧 Integration with Fridge Camera

### Example: Upload Photo After Capture

```python
#!/usr/bin/env python3
import cv2
from datetime import datetime
from connect_server import upload_file

def capture_and_upload():
    # Capture photo
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    
    if ret:
        # Save locally
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_file = f"/home/orangepi/fridge_photos/fridge_{timestamp}.jpg"
        cv2.imwrite(local_file, frame)
        
        # Upload to server
        remote_path = f"/root/fridge_photos/fridge_{timestamp}.jpg"
        upload_file(local_file, remote_path)
        
        print(f"✓ Photo captured and uploaded: {timestamp}")
    
    cap.release()

if __name__ == "__main__":
    capture_and_upload()
```

---

## 🛡️ Security Checklist

- [ ] Change server password immediately
- [ ] Setup SSH key authentication
- [ ] Disable password authentication on server
- [ ] Enable UFW firewall on server
- [ ] Regularly update server: `apt update && apt upgrade`
- [ ] Monitor server logs: `/var/log/auth.log`
- [ ] Consider changing SSH port from default 22
- [ ] Setup fail2ban on server

---

## 📊 Server Info

**Hostname:** smartFridge  
**IP:** 159.223.45.101  
**User:** root  
**OS:** (Check with: `ssh root@159.223.45.101 "cat /etc/os-release"`)

---

## 🆘 Troubleshooting

### Connection Refused
```bash
# Check if SSH service is running on server
ssh root@159.223.45.101 "systemctl status sshd"
```

### Permission Denied
```bash
# Verify password is correct
# Try typing password manually:
ssh root@159.223.45.101
```

### Host Key Verification Failed
```bash
# Remove old host key
ssh-keygen -R 159.223.45.101
```

---

## 📝 Notes

- Connection tested successfully: ✅
- Server hostname: `smartFridge`
- sshpass already installed: ✅
- Scripts are executable: ✅

**Next Steps:**
1. **CHANGE YOUR PASSWORD** on the server
2. Setup SSH key authentication
3. Test the scripts
4. Integrate with your fridge camera project

---

## 🔗 Related Files

- `t3.py` - Camera control script with settings
- `connect_server.py` - This connection manager
- `quick_connect.sh` - Quick connect script
- Future: `fridge_camera.py` - Integrated fridge monitoring system

**Happy Coding! 🚀**

