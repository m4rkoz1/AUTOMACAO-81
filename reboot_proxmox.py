import paramiko
import time

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

print("Commanding container to reboot...")
try:
    client.exec_command('reboot')
    # Sleep to allow the command to transmit before closing
    time.sleep(1)
except Exception as e:
    print(f"Expected disconnect exception: {e}")

client.close()
print("Container is restarting.")
