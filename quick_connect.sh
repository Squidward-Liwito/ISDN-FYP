#!/bin/bash
# Quick SSH connection script
# WARNING: Password authentication is insecure!

SERVER="root@159.223.45.101"
PASSWORD="pass123WORD"

echo "Connecting to $SERVER..."
echo "WARNING: Using password authentication (insecure!)"

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $SERVER

