import platform
import subprocess
import json
import re
from datetime import datetime

def extract_fields(log_parts):
    """
    Extracts the common log fields from the log parts and returns them as a dictionary.
    """
    field = 5
    source_parts = []
    while field < len(log_parts) and not log_parts[field].isnumeric():
        source_parts.append(log_parts[field])
        field += 1
    source = ' '.join(source_parts)

    instance_id = log_parts[field]

    field += 1
    message_parts = []
    while field < len(log_parts):
        message_parts.append(log_parts[field])
        field += 1
    message = ' '.join(message_parts)

    return {
        'timestamp': log_parts[1] + ' ' + log_parts[2] + ' ' + log_parts[3],
        'hostname': platform.node(),
        'log_level': log_parts[4],
        'source': source,
        'instance_id': instance_id,
        'message': message
    }

def get_common_logs(num_logs):
    # Check which operating system we are running on
    system = platform.system()

    if system == 'Windows':
        # Get Windows system logs
        output = subprocess.check_output(['powershell', f'Get-EventLog System -Newest {num_logs}'])
        logs = output.decode('utf-8', 'ignore').split('\n')
        # Filter out Windows-specific data
        logs = [log for log in logs if not log.startswith('EventCode')]

    elif system == 'Linux':
        # Get Linux system logs
        try:
            output = subprocess.check_output(['journalctl', f'-a --lines {num_logs}'])
            logs = output.decode('utf-8', 'ignore').split('\n')
            # Filter out Linux-specific data
            logs = [log for log in logs if not log.startswith('--')]
        except:
            # If journalctl fails, try using dmesg
            output = subprocess.check_output(['dmesg', f'--level=err,warn', f'--count={num_logs}'])
            logs = output.decode('utf-8', 'ignore').split('\n')

    # Create a list of dictionaries containing the filtered logs
    log_list = []

    for log in logs:
        log_parts = log.split()
        if len(log_parts) >= 7:
            log_dict = extract_fields(log_parts)
            log_list.append(log_dict)

    # Convert the list of dictionaries to JSON format
    json_logs = json.dumps(log_list)

    return json_logs

# how many logs they want to retrieve
num_logs = 50
# Call the function to get the filtered logs and print them to the console
filtered_logs = get_common_logs(num_logs)
print(filtered_logs)
