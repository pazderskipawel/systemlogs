from flask import Flask, request

app = Flask(__name__)

@app.route('/logs', methods=['POST'])
def receive_logs():
    logs = request.get_json()
    for log in logs:
        print(log)
    return 'Received logs'

if __name__ == '__main__':
    app.run(port=5000)