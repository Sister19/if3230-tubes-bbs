import asyncio
from threading import Thread
from xmlrpc.client import ServerProxy
from typing import Any, List
from enum import Enum
from lib.struct.address import Address
import json
import socket
import time


class RaftNode:
    HEARTBEAT_INTERVAL = 1
    ELECTION_TIMEOUT_MIN = 2
    ELECTION_TIMEOUT_MAX = 3
    RPC_TIMEOUT = 5

    class NodeType(Enum):
        LEADER = 1
        CANDIDATE = 2
        FOLLOWER = 3

    def __init__(self, application: Any, addr: Address, contact_addr: Address = None):
        socket.setdefaulttimeout(RaftNode.RPC_TIMEOUT)
        self.address:             Address = addr
        self.type:                RaftNode.NodeType = RaftNode.NodeType.FOLLOWER
        self.log:                 List[str, str] = []
        self.app:                 Any = application
        self.election_term:       int = 0
        self.cluster_addr_list:   List[Address] = []
        self.cluster_leader_addr: Address = None
        self.heartbeat_timer:     int = 0
        if contact_addr is None:
            self.cluster_addr_list.append(self.address)
            self.__initialize_as_leader()
        else:
            self.__try_to_apply_membership(contact_addr)

    # Internal Raft Node methods

    def __print_log(self, text: str):
        print(f"[{self.address}] [{time.strftime('%H:%M:%S')}] {text}")

    def __initialize_as_leader(self):
        self.__print_log("Initialize as leader node...")
        self.cluster_leader_addr = self.address
        self.type = RaftNode.NodeType.LEADER
        request = {
            "cluster_leader_addr": self.address,
            "election_term":       self.election_term,
            "log":                 self.log,
        }
        for addr in self.cluster_addr_list:
            if addr != self.address:
                self.__send_request(request, "change_leader", addr)
        self.heartbeat_thread = Thread(target=asyncio.run, args=[
                                       self.__leader_heartbeat()])
        self.heartbeat_thread.start()

    async def __leader_heartbeat(self):
        while True:
            self.__print_log("[Leader] Sending heartbeat...")
            for addr in self.cluster_addr_list:
                if addr != self.address:
                    self.__send_request(self.address, "heartbeat", addr)
            await asyncio.sleep(RaftNode.HEARTBEAT_INTERVAL)

    def __try_to_apply_membership(self, contact_addr: Address):
        redirected_addr = contact_addr
        response = {
            "status": "redirected",
            "address": {
                "ip":   contact_addr.ip,
                "port": contact_addr.port,
            }
        }
        request = {
            "address": self.address,
        }
        while response["status"] != "success":
            redirected_addr = Address(
                response["address"]["ip"], response["address"]["port"])
            response = self.__send_request(
                request, "apply_membership", redirected_addr)
        self.log = response["log"]
        self.cluster_addr_list = response["cluster_addr_list"]
        self.cluster_leader_addr = redirected_addr

    def __send_request(self, request: Any, rpc_name: str, addr: Address) -> "json":
        # Warning : This method is blocking
        node = ServerProxy(f"http://{addr.ip}:{addr.port}")
        json_request = json.dumps(request)
        print(request)
        print(rpc_name)
        rpc_function = getattr(node, rpc_name)
        try:
            response = json.loads(rpc_function(json_request))
        except socket.timeout:
            self.__print_log(f"[{rpc_name}] RPC Timeout")
            response = {
                "status": "failure",
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        self.__print_log(response)
        return response

    # Inter-node RPCs
    def heartbeat(self, json_request: str) -> "json":
        self.heartbeat_timer = 0
        response = {
            "heartbeat_response": "ack",
            "address":            self.address,
        }
        return json.dumps(response)
    
    def apply_membership(self, json_request: str) -> "json":
        request = json.loads(json_request)
        if (self.type == RaftNode.NodeType.LEADER):
            self.cluster_addr_list.append(Address(request["address"]["ip"], request["address"]["port"]))
            response = {
                "status": "success",
                "cluster_addr_list": self.cluster_addr_list,
                "log": self.log,
            }
        else:
            response = {
                "status": "redirected",
                "address": {
                    "ip":   self.cluster_leader_addr.ip,
                    "port": self.cluster_leader_addr.port,
                }
            }
        return json.dumps(response)
    
    def change_leader(self, json_request: str) -> "json":
        self.cluster_leader_addr = json_request["cluster_leader_addr"]
        self.type = RaftNode.NodeType.FOLLOWER
        return json.dumps({"status": "success"})

    # Client RPCs

    def execute(self, json_request: str) -> "json":
        request = json.loads(json_request)
        # TODO : Implement execute
        return json.dumps(request)

