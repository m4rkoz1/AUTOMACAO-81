import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.5.26', username='root', password='gustgia*')

# Script para iniciar os processos
start_script = """#!/bin/bash
fuser -k 5900/tcp 6080/tcp 2>/dev/null
killall -9 Xvfb x11vnc websockify 2>/dev/null
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
sleep 1
Xvfb :99 -screen 0 1280x800x24 -ac +extension GLX -noreset &
sleep 1
x11vnc -display :99 -forever -nopw -shared -rfbport 5900 -bg
sleep 1
exec websockify --web /usr/share/novnc 6080 localhost:5900
"""

sftp = ssh.open_sftp()
with sftp.open('/usr/local/bin/start_novnc.sh', 'w') as f:
    f.write(start_script)
sftp.chmod('/usr/local/bin/start_novnc.sh', 0o755)

service_content = """[Unit]
Description=noVNC Web Display Service for SSW Login
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/start_novnc.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""

with sftp.open('/etc/systemd/system/novnc.service', 'w') as f:
    f.write(service_content)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('systemctl daemon-reload && systemctl enable novnc && systemctl restart novnc')
print('Configured service.')
time.sleep(2)

stdin, stdout, stderr = ssh.exec_command('systemctl status novnc --no-pager')
print(stdout.read().decode())
ssh.close()
