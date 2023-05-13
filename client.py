from lib.struct.address       import Address
from xmlrpc.client import ServerProxy
from lib.app           import MessageQueue
import sys
import socket
from typing import Any, List
import json
import time

class Client:
    RPC_TIMEOUT = 2

    def __init__(self, addr: Address, server_addr = Address):
        self.addr: Address = addr
        self.server_addr: Address = server_addr
        self.cluster_addr_list: List[Address] = []
        self.__contact_leader()

    # Internal client methods
    def __contact_leader(self):
        response = {
            "status": "redirected",
            "address": {
                "ip":   self.server_addr.ip,
                "port": self.server_addr.port,
            }
        }
        request = {}

        tries = 0
        while response["status"] != "success":
            if tries > 10:
                print("[ERROR] Leader cannot found")
                exit()
            redirected_addr = Address(
                response["address"]["ip"], response["address"]["port"])
            response = self.__send_request(request, "client_handshake", redirected_addr)
            time.sleep(self.RPC_TIMEOUT)
            tries += 1
            if response["status"] != "success":
                print(f"[INFO] Leader not found, retrying..{tries}/10")
        
        self.cluster_addr_list = list(map(lambda addr: Address(addr["ip"], addr["port"]), response["cluster_addr_list"]))
        print("[INFO] Leader node found")
        self.server_addr = redirected_addr


    # RPC Methods
    def __send_request(self, request: Any, rpc_name: str, addr: Address) -> "json":
        # Warning : This method is blocking
        node = ServerProxy(f"http://{addr.ip}:{addr.port}")
        json_request = json.dumps(request)
        rpc_function = getattr(node, rpc_name)
        try:
            response = json.loads(rpc_function(json_request))
        except (ConnectionRefusedError, ConnectionResetError, ConnectionError, ConnectionAbortedError):
            # self.__print_log(f"[{rpc_name}] Connection error")
            response = {
                "status": "failure",
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        except socket.timeout:
            # self.__print_log(f"[{rpc_name}] Timeout")
            response = {
                "status": "failure",
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        # self.__print_log(response)
        return response

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("server.py <client_ip> <client_port> <server_ip> <server_port>")
        exit()

    client_addr = Address(sys.argv[1], int(sys.argv[2]))
    server_addr = Address(sys.argv[3], int(sys.argv[4]))
    client = Client(client_addr, server_addr)
    while True:
        user_input = input("> ")
        
        match user_input.split(" ")[0]:
            case "exit": 
                print("goodbye")
                break
            case "enqueue":
                message = user_input.split(" ", 1)[1]
                print("queueing message:", message)
                # send message
            case "dequeue":
                print("receiving message")
                # receive message
            case _:
                print("unknown command")
