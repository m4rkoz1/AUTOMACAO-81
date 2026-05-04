import paramiko

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

with open('inputs.txt', 'w', encoding='utf-8') as f:
    stdin, stdout, stderr = client.exec_command('grep -Eio "<input[^>]+" /opt/automacao/ssw0052.html')
    f.write(stdout.read().decode())

client.close()
