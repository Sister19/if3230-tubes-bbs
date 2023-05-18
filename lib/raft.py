import asyncio
from threading import Thread
from xmlrpc.client import ServerProxy
from typing import Any, List
from enum import Enum
from lib.struct.address import Address
import json
import socket
import time
import random


class RaftNode:
    HEARTBEAT_INTERVAL = 2
    ELECTION_TIMEOUT_MIN = 5
    ELECTION_TIMEOUT_MAX = 8
    RPC_TIMEOUT = 2
    FOLLOWER_TIMEOUT = 10

    class AppResponse(Enum):
        SUCCESS = 1
        FAILURE = 0

    class NodeType(Enum):
        LEADER = 1
        CANDIDATE = 2
        FOLLOWER = 3

    def __init__(self, addr: Address, contact_addr: Address = None, passive: bool = False):
        socket.setdefaulttimeout(RaftNode.RPC_TIMEOUT)
        self.address:             Address = addr
        self.type:                RaftNode.NodeType = RaftNode.NodeType.FOLLOWER
        self.message_log:         List[str] = []
        self.term_log:            List[int] = []    
        self.committed_length:    int = 0
        self.election_term:       int = 0
        self.cluster_addr_list:   List[Address] = []
        self.cluster_leader_addr: Address = None
        self.heartbeat_timer:     int = 0
        self.vote_count:          int = 0
        self.voted_for:           Address = None
        self.current_timeout:     int = 0
        self.commit_index:        int = 0
        if passive:
            self.type = RaftNode.NodeType.FOLLOWER
            self.__print_log("Waiting for another node to contact...")
            return
        if contact_addr is None:
            self.cluster_addr_list.append(self.address)
            self.__initialize_as_leader()
        else:
            self.__try_to_apply_membership(contact_addr)
            self.__initialize_as_follower()
    
    #
    #   Internal Raft Node methods
    #
    def __get_random_timeout(self) -> int:
        return random.randint(RaftNode.ELECTION_TIMEOUT_MIN, RaftNode.ELECTION_TIMEOUT_MAX)

    def __print_log(self, text: str):
        print(f"[{self.address}] [{time.strftime('%H:%M:%S')}] {text}")

    def __initialize_as_leader(self):
        self.__print_log("Initialize as leader node...")
        self.cluster_leader_addr = self.address
        self.type = RaftNode.NodeType.LEADER
        request = {
            "cluster_leader_addr": self.address,
            "election_term":       self.election_term,
            "message_log":          self.message_log,
            "commit_index":        self.commit_index,
        }

        # Send request to all nodes in cluster
        for addr in self.cluster_addr_list:
            if addr != self.address:
                self.__send_request(request, "change_leader", addr)

        # self.heartbeat_thread.stop()
        self.heartbeat_thread = Thread(target=asyncio.run, args=[
                                       self.__leader_heartbeat()])
        self.heartbeat_thread.start()

    async def __leader_heartbeat(self):
        while True:
            self.__print_log("[Leader] Sending heartbeat...")
            self.__print_log(self.__log_repr())
            for addr in self.cluster_addr_list:
                if addr != self.address:
                    request = {
                        "cluster_addr_list": self.cluster_addr_list,
                    }
                    self.__send_request(request, "heartbeat", addr)
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
            "address": {
                "ip":   self.address.ip,
                "port": self.address.port,
            },
        }
        while response["status"] != "success":
            redirected_addr = Address(
                response["address"]["ip"], response["address"]["port"])
            response = self.__send_request(
                request, "apply_membership", redirected_addr)
            time.sleep(self.RPC_TIMEOUT)
        self.message_log = response["message_log"]
        self.cluster_addr_list = list(map(lambda addr: Address(addr["ip"], addr["port"]), response["cluster_addr_list"]))
        self.cluster_leader_addr = redirected_addr

    def __initialize_as_follower(self):
        self.__print_log("Initialize as follower node...")
        self.type = RaftNode.NodeType.FOLLOWER
        self.heartbeat_timer = 0
        # self.heartbeat_thread.stop()
        self.heartbeat_thread = Thread(target=asyncio.run, args=[
                                       self.__follower_heartbeat()])
        self.heartbeat_thread.start()

    async def __follower_heartbeat(self):
        self.current_timeout = self.__get_random_timeout()
        while True:
            self.heartbeat_timer += 1
            if self.heartbeat_timer >= self.current_timeout:
                self.__print_log("Election timeout")
                self.__initialize_as_candidate()
                return
            await asyncio.sleep(1)

    def __initialize_as_candidate(self):
        self.__print_log("Initialize as candidate node...")
        self.type = RaftNode.NodeType.CANDIDATE
        # self.heartbeat_thread.stop()
        self.heartbeat_thread = Thread(target=asyncio.run, args=[
                                        self.__candidate_hearbeat()])
        self.heartbeat_thread.start()


    async def __candidate_hearbeat(self):
        while self.type == RaftNode.NodeType.CANDIDATE:
            self.election_term += 1
            self.heartbeat_timer = 0
            self.voted_for = self.address
            self.vote_count = 1
            self.__send_vote_request()
            self.current_timeout = self.__get_random_timeout()
            await asyncio.sleep(self.current_timeout)

    def __send_vote_request(self):
        request = {
            "election_term": self.election_term,
            "candidate_addr": {
                "ip":   self.address.ip,
                "port": self.address.port,
            },
        }
        accepted_addr_list = []
        for addr in self.cluster_addr_list:
            if addr != self.address and addr not in accepted_addr_list:
                response = self.__send_request(request, "handle_vote_request", addr)
                if response["status"] == "success":
                    accepted_addr_list.append(addr)
                    self.vote_count += 1
                    if self.vote_count > len(self.cluster_addr_list) / 2:
                        self.__initialize_as_leader()
                        return
    
    #
    # External Log methods
    #

    def app_execute(self, json_request: json) -> "json":
        # print("Type??", type(json_request), "at", str(self.address))
        request = json.loads(json_request)
        match request["method"]:
            case "push":
                try:
                    # IF NOT LEADER DOES THINGS DIFFERENTLY YAH
                    if self.type != self.NodeType.LEADER:
                        # Does some preliminary checks
                        if self.election_term < request["curr_term"]:
                            self.election_term = request["curr_term"]
                        if request["curr_term"] == self.election_term:
                            self.type = self.NodeType.FOLLOWER
                        logOk: bool = (self.message_log.__len__() >= request["prefix_len"]) and (request["prefix_len"] == 0 or self.term_log[request["prefix_len"] - 1] == request["last_term"])
                        if self.election_term == request["curr_term"] and logOk:
                            # If the log history is the same as previously, pass on
                            # if not(request["params"]["messages"].__len__() == 0 and request["last_term"] == self.term_log[-1] and request["prefix_len"] == self.message_log.__len__()):
                            #     return {"ack": False, "prefix_len_restart_at": request["prefix_len"] - 1}
                            self.__push(request["messages"], request["terms"], int(request["prefix_len"]))
                            if request["leader_commit"] < self.committed_length:
                                self.commited_length = request["leader_commit"]
                            return json.dumps({"ack": True})
                        return json.dumps({"ack": False})
                    else:
                        self.__push(request["params"], [self.election_term], self.message_log.__len__())
                        return {"ack": True}
                except:
                    return {"ack": False}
    #
    #   Internal Log Methods
    #
    def __get_log(self) -> List[str]:
        return self.message_log
    
    def __push(self, messages: List[str], terms: List[int], prefix_len: int):
        while prefix_len < self.message_log.__len__():
            self.term_log.pop(0)
            self.message_log.pop(0)

        for i in range(len(messages)):
            self.message_log.append(messages[i])
            self.term_log.append(terms[i])

    def __pop(self) -> str:
        self.term_log.pop(0)
        return self.message_log.pop(0)
    
    def __log_repr(self) -> str:
        repr_output = "Representation: \n"
        repr_output += "Term log    : " + str(self.term_log) + "\n"
        repr_output += "Message log : " + str(self.message_log) + "\n"
        repr_output += "Curr term   : " + str(self.election_term)
        return repr_output 

    #
    #   RPC methods
    #
    def __send_request(self, request: Any, rpc_name: str, addr: Address) -> "json":
        # Warning : This method is blocking
        node = ServerProxy(f"http://{addr.ip}:{addr.port}")
        json_request = json.dumps(request)
        rpc_function = getattr(node, rpc_name)
        try:
            response = json.loads(rpc_function(json_request))
        except (ConnectionRefusedError, ConnectionResetError, ConnectionError, ConnectionAbortedError):
            self.__print_log(f"[{rpc_name}] Connection error")
            response = {
                "status": "failure",
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        except socket.timeout:
            self.__print_log(f"[{rpc_name}] Timeout")
            response = {
                "status": "failure",
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        except Exception as e:
            self.__print_log(f"[{rpc_name}] Unknown error : {e}", "at", str(addr))
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
        request = json.loads(json_request)
        self.cluster_addr_list = list(map(lambda addr: Address(addr["ip"], addr["port"]), request["cluster_addr_list"]))
        self.heartbeat_timer = 0
        self.__print_log(self.__log_repr())
        response = {
            "heartbeat_response": "ack",
        }
        return json.dumps(response)
    
    def apply_membership(self, json_request: str) -> "json":
        request = json.loads(json_request)
        if (self.type == RaftNode.NodeType.LEADER):
            new_addr = Address(request["address"]["ip"], request["address"]["port"])
            self.cluster_addr_list.append(new_addr)
            response = {
                "status": "success",
                "cluster_addr_list": self.cluster_addr_list,
                "message_log": self.message_log,
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
    
    def handle_vote_request(self, json_request: str) -> "json":
        request = json.loads(json_request)
        candidate_addr = Address(request["candidate_addr"]["ip"], request["candidate_addr"]["port"])
        response = {
            "status": "failure",
            "address": {
                "ip":   candidate_addr.ip,
                "port": candidate_addr.port,
            },
            "message": "Already voted for another candidate"
        }
        if self.election_term < request["election_term"]:
            self.election_term = request["election_term"]
            self.voted_for = candidate_addr
            self.heartbeat_timer = 0
            response = {
                "status": "success",
                "address": {
                    "ip":   candidate_addr.ip,
                    "port": candidate_addr.port,
                }
            }
        return json.dumps(response)
    
    def change_leader(self, json_request: str) -> "json":
        request = json.loads(json_request)
        self.cluster_leader_addr = Address(request["cluster_leader_addr"]["ip"], request["cluster_leader_addr"]["port"])
        self.election_term = request["election_term"]
        self.scommit_index = request["commit_index"]
        self.type = RaftNode.NodeType.FOLLOWER
        self.__initialize_as_follower()
        response = {"status": "success"}
        return json.dumps(response)

    # Client RPCs
    def execute(self, json_request: str) -> "json":
        response = {
            "status": self.AppResponse.FAILURE.value,
        }
        if self.type == RaftNode.NodeType.LEADER:
            acks: int = 0
            # If leader then add first to your own log
            response = self.app_execute(json_request)
            if response["ack"] == True:
                acks += 1
            # Then contact others to add them to their own
            for addr in self.cluster_addr_list:
                if addr != self.address:
                    specific_request = {
                        "method": "push",
                        "curr_term": self.election_term,
                        "prefix_len": len(self.message_log) - 1,
                        "last_term": self.term_log[len(self.message_log) - 2],
                        "messages": [self.message_log[len(self.message_log) - 1]],
                        "terms": [self.term_log[len(self.message_log) - 1]],
                        "leader_commit": self.committed_length
                    } 
                    response_follower = self.__send_request(specific_request, "app_execute", addr)
                    if response_follower["ack"] == True:
                        acks += 1
        else:
            response = self.__send_request(json.loads(json_request), "execute", self.cluster_leader_addr)
        return json.dumps(response)