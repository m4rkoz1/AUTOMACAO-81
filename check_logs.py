import paramiko

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'
REMOTE_DIR = '/opt/automacao'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

with open('logs.txt', 'w', encoding='utf-8') as f:
    f.write("--- RECENT LOGS ---\n")
    stdin, stdout, stderr = client.exec_command('journalctl -u automacao -n 250 --no-pager')
    f.write(stdout.read().decode('utf-8') + "\n")

    f.write("\n--- SPREADSHEETS ---\n")
    stdin, stdout, stderr = client.exec_command(f'ls -lat {REMOTE_DIR}/*.xlsx')
    f.write(stdout.read().decode('utf-8') + "\n")

client.close()
