import subprocess
import signal
import time

from typing import List
test: List[str] = []
print(test)

# generate 5 servers
server_scripts = [
    # leader
    {
        "py": "server.py",
        "args": ["localhost", "2401"],
    },
    # follower
    {
        "py": "server.py",
        "args": ["localhost", "2402", "localhost", "2401"],
    },
    # follower
    {
        "py": "server.py",
        "args": ["localhost", "2403", "localhost", "2401"],
    },
    # follower
    {
        "py": "server.py",
        "args": ["localhost", "2404", "localhost", "2401"],
    },
    # follower
    {
        "py": "server.py",
        "args": ["localhost", "2405", "localhost", "2401"],
    },
]

client_scripts = [
    # client to leader
    {
        "py": "client.py",
        "args": ["localhost", "2431", "localhost", "2401"],
    },
    # client to follower
    {
        "py": "client.py",
        "args": ["localhost", "2432", "localhost", "2402"],
    },
]

# start servers
for server in server_scripts:
    process = subprocess.Popen(["python", server["py"]] + server["args"])
    server["process"] = process
    time.sleep(1)

# start clients
for client in client_scripts:
    process = subprocess.Popen(["python", client["py"]] + client["args"])
    client["process"] = process
    time.sleep(1)

time.sleep(5)

# Kill a server and its clients
server_to_kill = server_scripts[0]
clients_to_kill = [client for client in client_scripts if client["args"][3] == server_to_kill["args"][1]]
for client in clients_to_kill:
    client["process"].send_signal(signal.SIGINT)
server_to_kill["process"].send_signal(signal.SIGINT)