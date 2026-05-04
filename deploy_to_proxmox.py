import paramiko
from scp import SCPClient
import os

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'
LOCAL_DIR = r'c:\Users\MarcosTi\Desktop\AUTOMACAO 81'
REMOTE_DIR = '/opt/automacao'

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

print(f"Connecting to {IP}...")
ssh = create_ssh_client(IP, USER, PASSWORD)
scp = SCPClient(ssh.get_transport())

print(f"Creating remote directory {REMOTE_DIR}...")
ssh.exec_command(f'mkdir -p {REMOTE_DIR}')

# Upload files
files_to_upload = [
    'servidor.py', 'automacao_ssw.py', 'requirements.txt', 'index.html', 'RJO.xlsx'
]

for f in files_to_upload:
    local_path = os.path.join(LOCAL_DIR, f)
    if os.path.exists(local_path):
        print(f"Uploading {f}...")
        scp.put(local_path, remote_path=REMOTE_DIR)

# Upload directories
dirs_to_upload = ['downloads', 'screenshots']
for d in dirs_to_upload:
    local_path = os.path.join(LOCAL_DIR, d)
    if os.path.exists(local_path):
        print(f"Uploading directory {d}...")
        scp.put(local_path, recursive=True, remote_path=REMOTE_DIR)

print("Setting up Debian environment (venv, pip, playwright)...")
setup_commands = [
    'apt-get update',
    'apt-get install -y python3 python3-pip python3-venv libglib2.0-0 libnss3 libx11-xcb1 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpangocairo-1.0-0 libpango-1.0-0',
    f'cd {REMOTE_DIR} && python3 -m venv venv',
    f'{REMOTE_DIR}/venv/bin/pip install -r {REMOTE_DIR}/requirements.txt',
    f'{REMOTE_DIR}/venv/bin/playwright install --with-deps chromium'
]

for cmd in setup_commands:
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out:
        print(out)
    if err:
        print("Error:", err)
    if exit_status != 0:
        print(f"[{cmd}] failed with status {exit_status}")

# Create systemd service
print("Configuring systemd service...")
service_file = f"""[Unit]
Description=Automacao SSW Service
After=network.target

[Service]
User=root
WorkingDirectory={REMOTE_DIR}
Environment="PATH={REMOTE_DIR}/venv/bin"
ExecStart={REMOTE_DIR}/venv/bin/python {REMOTE_DIR}/servidor.py
Restart=always

[Install]
WantedBy=multi-user.target
"""
ssh.exec_command(f"cat << 'EOF' > /etc/systemd/system/automacao.service\n{service_file}\nEOF")
ssh.exec_command("systemctl daemon-reload")
ssh.exec_command("systemctl enable automacao")
ssh.exec_command("systemctl restart automacao")

print("Deployment complete. Service 'automacao' restarted.")
scp.close()
ssh.close()
