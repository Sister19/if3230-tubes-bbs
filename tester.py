import subprocess
import signal
import time
import os

# from typing import List
# test: List[str] = []
# print(test)

# Define the command to open a new terminal window
if os.name == 'nt':  # for Windows
    CMD_NEW_TERMINAL = 'start cmd /k'
else:  # for Linux and macOS
    CMD_NEW_TERMINAL = 'x-terminal-emulator -e'

# generate 5 servers
server_scripts = [
    # leader
    {
        "py": "server.py",
        "args": ["localhost", "2401"],
    },
    # # follower
    # {
    #     "py": "server.py",
    #     "args": ["localhost", "2402", "localhost", "2401"],
    # },
    # # follower
    # {
    #     "py": "server.py",
    #     "args": ["localhost", "2403", "localhost", "2401"],
    # },
    # # follower
    # {
    #     "py": "server.py",
    #     "args": ["localhost", "2404", "localhost", "2401"],
    # },
    # # follower
    # {
    #     "py": "server.py",
    #     "args": ["localhost", "2405", "localhost", "2401"],
    # },
]

client_scripts = [
    # # client to leader
    # {
    #     "py": "client.py",
    #     "args": ["localhost", "2431", "localhost", "2401"],
    # },
    # # client to follower
    # {
    #     "py": "client.py",
    #     "args": ["localhost", "2432", "localhost", "2402"],
    # },
]

# start servers
server_processes = []
for server in server_scripts:
    cmd = CMD_NEW_TERMINAL + f' python {server["py"]} ' + ' '.join(server["args"])
    server_processes.append(subprocess.Popen(cmd, shell=True))
    time.sleep(1)

# start clients
client_processes = []
for client in client_scripts:
    cmd = CMD_NEW_TERMINAL + f' python {client["py"]} ' + ' '.join(client["args"])
    client_processes.append(subprocess.Popen(cmd, shell=True))
    time.sleep(1)