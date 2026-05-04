import paramiko

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

with open('status.txt', 'w', encoding='utf-8') as f:
    f.write("--- systemctl status automacao ---\n")
    stdin, stdout, stderr = client.exec_command('systemctl status automacao')
    f.write(stdout.read().decode('utf-8'))

    f.write("\n--- journalctl -u automacao -n 50 --no-pager ---\n")
    stdin, stdout, stderr = client.exec_command('journalctl -u automacao -n 50 --no-pager')
    f.write(stdout.read().decode('utf-8'))

client.close()
