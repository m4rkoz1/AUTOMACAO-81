import paramiko

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

commands = [
    'timedatectl set-timezone America/Sao_Paulo',
    'systemctl enable automacao',
    'systemctl restart automacao',
    'date'
]

for cmd in commands:
    print(f"Running: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    if out.strip(): print(f"Output: {out.strip()}")
    if err.strip(): print(f"Error: {err.strip()}")

client.close()
