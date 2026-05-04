import paramiko
import time
import requests

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'

print("Connecting to Proxmox container to restart service...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

try:
    print("Restarting automacao.service...")
    client.exec_command('systemctl restart automacao')
    time.sleep(2)
    
    # Also check if it's running
    stdin, stdout, stderr = client.exec_command('systemctl status automacao')
    status = stdout.read().decode('utf-8')
    print("Service status excerpt:")
    for line in status.split('\n')[:5]:
        print(line)
        
    print("\nCalling the execution endpoint...")
    try:
        r = requests.post("http://192.168.5.26:5000/api/executar", timeout=5)
        print("Trigger response:", r.json())
    except Exception as e:
        print("Failed to trigger execution HTTP endpoint:", e)
        
except Exception as e:
    print(f"Error: {e}")

client.close()
print("Done.")
