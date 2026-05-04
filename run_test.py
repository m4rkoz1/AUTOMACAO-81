import paramiko
from scp import SCPClient

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'
REMOTE_DIR = '/opt/automacao'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)
scp = SCPClient(client.get_transport())

# Upload script
scp.put(r'c:\Users\MarcosTi\Desktop\AUTOMACAO 81\test_full.py', remote_path=REMOTE_DIR)

print("Running full branch test on server...")
stdin, stdout, stderr = client.exec_command(f'{REMOTE_DIR}/venv/bin/python {REMOTE_DIR}/test_full.py', timeout=120)

with open('test_result.txt', 'w', encoding='utf-8') as f:
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    f.write("STDOUT:\n" + out + "\n\nSTDERR:\n" + err)
    print(out)
    if err.strip():
        print("STDERR:", err[:500])

scp.close()
client.close()
