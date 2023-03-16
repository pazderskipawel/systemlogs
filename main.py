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
        self.stopped = False

    def stop(self):
        self.stopped = True

    def get_windows_logs(self, num_logs):
        cmd = ['powershell', '-Command', f'Get-WinEvent -LogName System -MaxEvents {num_logs} -Oldest | ConvertTo-Json']
        output = subprocess.check_output(cmd, encoding='utf-8', errors='replace')
        logs = output.strip().split('\n')
        return logs

    def get_linux_logs(self, num_logs):
        cmd = [f"journalctl --lines={num_logs} --output=json"]
        output = subprocess.check_output(cmd, encoding='utf-8', errors='replace', shell=True, executable="/bin/bash")
        logs = output.strip().split('\n')
        return logs

    def run(self):
        while not self.stopped:
            if platform.system() == 'Windows':
                logs = self.get_windows_logs(self.num_logs)
            else:
                logs = self.get_linux_logs(self.num_logs)
            print(logs)
            log_queue.put(logs)
            # for log in logs:
            #     print(log)
            #     log_queue.put(log)

            # Check the stopped flag before sleeping
            for i in range(10):
                if self.stopped:
                    return  # exit the thread
                time.sleep(1)


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

            # Check the stopped flag before sleeping
            for i in range(10):
                if self.stopped and log_queue.empty():
                    return  # exit the thread
                time.sleep(1)


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
