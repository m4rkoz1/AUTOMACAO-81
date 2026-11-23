import paramiko
from scp import SCPClient
import os
import sys

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'
LOCAL_DIR = r'c:\Users\MarcosTi\Desktop\AUTOMACAO 81'
REMOTE_DIR = '/opt/automacao'

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password, timeout=10)
    return client

def main():
    print(f"Connecting to {IP}...")
    ssh = create_ssh_client(IP, USER, PASSWORD)
    scp = SCPClient(ssh.get_transport())

    print(f"Ensuring remote directories exist in {REMOTE_DIR}...")
    remote_dirs = [
        REMOTE_DIR,
        f"{REMOTE_DIR}/downloads",
        f"{REMOTE_DIR}/downloads_036",
        f"{REMOTE_DIR}/screenshots",
        f"{REMOTE_DIR}/screenshots_036"
    ]
    for d in remote_dirs:
        ssh.exec_command(f'mkdir -p {d}')

    # Files to upload
    files_to_upload = [
        'servidor.py',
        'automacao_ssw.py',
        'automacao_036.py',
        'upload_filebrowser.py',
        'requirements.txt',
        'index.html',
        'index_036.html',
        'index_admin.html',
        'RJO.xlsx',
        'FSP.xlsx',
        'BAR.xlsx',
        'ARA.xlsx',
        'TRA.xlsx',
        'relatorio_036.xlsx',
        'storage_state.json'
    ]

    for f in files_to_upload:
        local_path = os.path.join(LOCAL_DIR, f)
        if os.path.exists(local_path):
            print(f"Uploading {f}...")
            scp.put(local_path, remote_path=REMOTE_DIR)
        else:
            print(f"Skip (not found locally): {f}")

    print("Updating python dependencies in remote venv...")
    commands = [
        f'{REMOTE_DIR}/venv/bin/pip install -r {REMOTE_DIR}/requirements.txt'
    ]

    for cmd in commands:
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        if out:
            print(out.strip())
        if err:
            print("Stderr:", err.strip())
        if exit_status != 0:
            print(f"Warning: [{cmd}] exited with code {exit_status}")

    print("Restarting service 'automacao'...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart automacao")
    exit_status = stdout.channel.recv_exit_status()
    print("Service restarted.")

    print("\nChecking service status...")
    stdin, stdout, stderr = ssh.exec_command("systemctl status automacao --no-pager")
    print(stdout.read().decode('utf-8', errors='ignore'))

    scp.close()
    ssh.close()
    print("Deploy to production (192.168.5.26) completed successfully!")

if __name__ == "__main__":
    main()
