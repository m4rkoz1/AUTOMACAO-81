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

print("Updating python packages...")
setup_commands = [
    f'{REMOTE_DIR}/venv/bin/pip install -r {REMOTE_DIR}/requirements.txt'
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

ssh.exec_command("systemctl restart automacao")

print("Update complete. Service 'automacao' restarted.")
scp.close()
ssh.close()
