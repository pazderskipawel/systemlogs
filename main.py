import os
import threading
import queue
import time
import subprocess
import requests
import platform
import json


class LogWorker(threading.Thread):
    def __init__(self, num_logs, batch_size):
        super().__init__()
        self.num_logs = num_logs
        self.batch_size = batch_size
        self.logs = self.get_logs()
        self.stopped = False

    def stop(self):
        self.stopped = True

    def get_logs(self):
        if platform.system() == 'Windows':
            logs = self.get_windows_logs(self.num_logs)
        else:
            logs = self.get_linux_logs(self.num_logs)
        return logs

    def get_windows_logs(self, num_logs):
        cmd = f'powershell -Command Get-WinEvent -FilterHashtable @{{logname=\'Application\',\'System\'; StartTime=(Get-Date).AddMinutes(-60)}} -MaxEvents {num_logs} | Select-Object @{{Name=\'TimeCreated\'; Expression={{(Get-Date $_.TimeCreated).ToString()}}}}, Level, Message, ProviderName, MachineName, ContainerName | ConvertTo-Json'
        output = subprocess.check_output(cmd, encoding='utf-8', errors='replace')
        logs = json.loads(output)
        result = []
        for log in logs:
            result.append({
                'os': 'Windows',
                'severity': log['Level'],
                'message': log['Message'],
                'timestamp': log['TimeCreated'],
                'hostname': log['MachineName'],
                'unit': log['ProviderName'],
                'type': log['ContainerName'],
                'raw': log
            })
        return result

    def get_linux_logs(self, num_logs):
        cmd = f'journalctl --lines={num_logs} --output=json | jq \'.[] | {{os: "Linux", severity: .PRIORITY, message: .MESSAGE, timestamp: (.__REALTIME_TIMESTAMP / 1000000 | floor), hostname: hosthostname, unit: ._SYSTEMD_UNIT, type: if (.["_EXE"] | test("(?i)/opt|/snap")) then "Application" else "System" end, raw: .}}\''
        output = subprocess.check_output(cmd, encoding='utf-8', errors='replace', shell=True, executable="/bin/bash")
        logs = json.loads(output)
        return logs

    def run(self):
        while not self.stopped:
            logs = self.get_logs()
            batch = []
            for _ in range(self.batch_size):
                batch.append(self.get_logs())
            log_queue.put(batch)
            time.sleep(10)


class LogSender(threading.Thread):
    def __init__(self, endpoint):
        super().__init__()
        self.endpoint = endpoint
        self.stopped = False

    def stop(self):
        self.stopped = True

    def run(self):
        while not self.stopped or not log_queue.empty():
            try:
                batch = log_queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                response = requests.post(self.endpoint, json=batch)
                if response.status_code == 200:
                    num_logs = sum([len(item) for item in batch])
                    print(f"Sent batch with {num_logs} logs")
                else:
                    print(f"Failed to send logs with status code {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to send logs: {e}")
            time.sleep(10)


if __name__ == '__main__':
    num_logs = 10
    batch_size = 2  # how many times it gets logs eg. if num_log = 10 and batch_size = 2 then 20 logs will be sent
    endpoint = "http://localhost:5000/logs"

    log_queue = queue.Queue()
    log_worker = LogWorker(num_logs, batch_size)
    log_sender = LogSender(endpoint)

    try:
        log_worker.start()
        log_sender.start()
        input("Press enter to stop...")
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        log_worker.stop()
        log_worker.join()
        log_sender.stop()
        log_sender.join()
