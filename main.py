import threading
import time
from log_workers import LogWorker, LogSender

logs_queue = LogWorker().logs_queue
log_worker = LogWorker()
log_sender = LogSender(logs_queue)


def stop_workers():
    log_worker.stop()
    log_sender.stop()

    log_worker.join()
    log_sender.join()


def main():
    log_worker.start()
    log_sender.start()

    input("Press Enter to stop workers...\n")

    stop_workers()


if __name__ == '__main__':
    main()
