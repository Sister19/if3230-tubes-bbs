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

    def __init__(self, addr: Address, server_addr: Address):
        self.addr: Address = addr
        self.server_addr: Address = server_addr

    def change_server(self, addr: Address):
        self.server_addr = addr

    def __str__(self) -> str:
        return f"{self.server_addr.ip}:{self.server_addr.port}"

    # RPC Methods
    def __send_request(self, request: Any, rpc_name: str, addr: Address) -> "json":
        # Warning : This method is blocking
        node = ServerProxy(f"http://{addr.ip}:{addr.port}")
        json_request = json.dumps(request)
        rpc_function = getattr(node, rpc_name)
        response = {
            "status": "redirected",
            "address": {
                "ip":   addr.ip,
                "port": addr.port,
            }
        }
        try:
            while response["status"] == "redirected":
                response = json.loads(rpc_function(json_request))
                print(response)
                if response["status"] == "redirected":
                    addr = Address(response["address"]["ip"], response["address"]["port"])
                    rpc_function = getattr(ServerProxy(f"http://{addr.ip}:{addr.port}"), rpc_name)
        except Exception as e:
            print("Error :", e)
            response = {
                "status": "failure",
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
            print(response)
        return response
    
    #
    #   Client - Server RPC
    #
    def enqueue(self, message: str) -> "json":
        request = {
            "method": "enqueue",
            "params": [message],
        }
        response = self.__send_request(request, "execute", self.server_addr)
        return response

    def dequeue(self) -> "json":
        request = {
            "method": "dequeue",
        }
        response = self.__send_request(request, "execute", self.server_addr)
        return response

    def request_log(self) -> "json":
        response = self.__send_request(None, "request_log", self.server_addr)
        return response
    
    def status(self) -> "json":
        request = {
            "method": "status",
        }
        response = self.__send_request(request, "get_node_status", self.server_addr)
        return response

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("client.py <client_ip> <client_port> <server_ip> <server_port>")
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
            case c if c in ["enqueue", "enq"]:
                message = user_input.split(" ", 1)[1]
                print("queueing message:", message)
                # send message
                client.enqueue(message)

            case c if c in ["dequeue", "deq"]:
                # receive message
                print("Dequeing message")
                client.dequeue()

            case c if c in ["log", "request_log"]:
                print("requesting log..")
                response = client.request_log()
                if response["status"] == "success":
                    print(response["log"])
                else:
                    print("request log failed")

            case "node":
                if user_input.split(" ")[1] == "status":
                    print("Server node at", str(client))
                    print(client.status())
                elif user_input.split(" ")[1] == "change":
                    temp_addr = Address(user_input.split(" ")[2], int(user_input.split(" ")[3]))
                    client.change_server(temp_addr)
                    print("Server node changed to", str(client))
                else:
                    print("unknown command")
            case "help":
                print('enqueue <message>        :           enqueue a message')
                print('dequeue                  :           dequeue a message')
                print('node status              :           show current server node status')
                print('node change <ip> <port>  :           change server node')
                print('request_log              :           request log')
                print('exit                     :           exit the program')
            case _:
                print("unknown command")
