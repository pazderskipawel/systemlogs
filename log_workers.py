import platform
import subprocess
import threading
import time
import queue


class LogWorker(threading.Thread):
    def __init__(self):
        super().__init__()
        self.stopped = False
        self.num_logs = 10
        self.logs_queue = queue.Queue()

    def stop(self):
        self.stopped = True

    def get_windows_logs(self, num_logs):
        cmd = ['powershell', '-Command', f'Get-WinEvent -LogName System -MaxEvents {num_logs} -Oldest | ConvertTo-Json']
        output = subprocess.check_output(cmd, encoding='utf-8', errors='replace')
        logs = output.strip().split('\n')
        return logs

    def get_linux_logs(self, num_logs):
        cmd = ['journalctl', f'-c {num_logs}' , '--output=json']
        output = subprocess.check_output(cmd, encoding='utf-8', errors='replace')
        logs = output.strip().split('\n')
        return logs[:num_logs]

    def run(self):
        while not self.stopped:
            if platform.system() == 'Windows':
                logs = self.get_windows_logs(self.num_logs)
            else:
                logs = self.get_linux_logs(self.num_logs)

            print(logs)
            self.logs_queue.put(logs)
            print(self.logs_queue)

            # Check the stopped flag before sleeping
            for i in range(10):
                if self.stopped:
                    break  # exit the thread
                time.sleep(1)

    def start(self):
        super().start()


class LogSender(threading.Thread):
    def __init__(self, logs_queue):
        super().__init__()
        self.stopped = False
        self.logs_queue = logs_queue

    def stop(self):
        self.stopped = True

    def send_logs(self, logs):
        headers = {'Content-type': 'application/json'}
        data = {'logs': logs}
        response = requests.post(self.url, headers=headers, data=json.dumps(data))
        if response.status_code != 200:
            print(f'Error sending logs: {response.status_code}')
        print("Sending logs:", logs)

    def run(self):

        while not self.stopped or not self.logs_queue.empty():
            try:
                logs_batch = []
                for i in range(5):
                    logs_batch.append(self.logs_queue.get(block=False))
            except queue.Empty:
                pass
            else:
                self.send_logs(logs_batch)

            time.sleep(1)

    def start(self):
        super().start()
