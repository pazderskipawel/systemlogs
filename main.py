import subprocess
import json
import platform

def main(num_logs):

    if platform.system() == 'Windows':
        cmd = ['powershell', '-Command', f'Get-WinEvent -LogName System -MaxEvents {num_logs}  | ConvertTo-Json']
    else:
        cmd = ['journalctl', f'-n {num_logs}', '--output=json']

    output = subprocess.check_output(cmd, encoding='utf-8', errors='replace')
    logs = output.strip().split('\n')

    for log in logs:
        print(log)

if __name__ == '__main__':
    num_logs = 100
    main(num_logs)
