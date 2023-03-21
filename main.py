import os
import threading
import queue
import time
import subprocess
import requests
import platform


class LogWorker(threading.Thread):
    def __init__(self, num_logs):
        super().__init__()
        self.num_logs = num_logs
        logs = self.get_logs(num_logs)
        self.logs = logs
        self.stopped = False

    def stop(self):
        self.stopped = True

    def get_logs(self, num_logs):
        if platform.system() == 'Windows':
            logs = self.get_windows_logs(self.num_logs)
        else:
            logs = self.get_linux_logs(self.num_logs)
        logs = logs.strip().split('\n')
        return logs

    def get_windows_logs(self, num_logs):
        cmd = f'powershell -Command Get-WinEvent -LogName System -MaxEvents {num_logs} | Select-Object TimeCreated, ProcessId, LogName, Level, ProviderName, Message | ConvertTo-Json'
        return subprocess.check_output(cmd, encoding='utf-8', errors='replace')

    def get_linux_logs(self, num_logs):
        cmd = f'journalctl --lines={num_logs} --output=json | jq \'[.[] | {{TimeCreated: .__REALTIME_TIMESTAMP / 1000000, ProcessId: ._PID, LogName: ._SYSLOG_IDENTIFIER ,Level: .PRIORITY, ProviderName: .SYSLOG_IDENTIFIER, Message: .MESSAGE}}]\''
        return subprocess.check_output(cmd, encoding='utf-8', errors='replace', shell=True, executable="/bin/bash")

    def run(self):
        while not self.stopped:
            print(self.logs)
            log_queue.put(self.logs)
            time.sleep(10)


class LogSender(threading.Thread):
    def __init__(self, batch_size, endpoint):
        super().__init__()
        self.batch_size = batch_size
        self.endpoint = endpoint
        self.stopped = False

    def stop(self):
        self.stopped = True

    def run(self):
        while not self.stopped or not log_queue.empty():
#TODO batch in LogWorker
            batch = []
            for i in range(self.batch_size):
                try:
                    log = log_queue.get(timeout=1)
                    batch.append(log)
                except queue.Empty:
                    break

            if batch:
                try:
                    requests.post(self.endpoint, json=batch)
                    print("Logs sent")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to send logs: {e}")

            #
            time.sleep(10)


if __name__ == '__main__':
    num_logs = 10
    batch_size = 5
    endpoint = "http://localhost:5000/logs"

    log_queue = queue.Queue()
    log_worker = LogWorker(num_logs)
    log_sender = LogSender(batch_size, endpoint)

    try:
        log_worker.start()
        log_sender.start()
        input("Press enter to stop...")
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        log_worker.stop()
        log_sender.stop()
        log_worker.join()
        log_sender.join()
