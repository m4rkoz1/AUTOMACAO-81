import paramiko
from scp import SCPClient

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'
REMOTE_DIR = '/opt/automacao'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

with open('frames_dump.txt', 'w', encoding='utf-8') as fout:
    fout.write("Frames inputs:\n")
    for idx in range(5):
        stdin, stdout, stderr = client.exec_command(f'grep -Eio "<input[^>]+" {REMOTE_DIR}/frame_{idx}.html | head -n 30')
        out = stdout.read().decode()
        if out.strip():
            fout.write(f"--- frame_{idx}.html ---\n")
            fout.write(out + "\n")

client.close()
