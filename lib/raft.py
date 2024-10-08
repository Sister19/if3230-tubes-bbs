import asyncio
from threading import Thread
from xmlrpc.client import ServerProxy
from typing import Any, List, Dict
from enum import Enum
from lib.struct.address import Address
import json
import socket
import time
import random

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class RaftNode:
    HEARTBEAT_INTERVAL = 3
    ELECTION_TIMEOUT_MIN = 40
    ELECTION_TIMEOUT_MAX = 80    
    RPC_TIMEOUT = 5

    class AppResponse(Enum):
        SUCCESS = 1
        FAILURE = 0

    class NodeType(Enum):
        LEADER = 1
        CANDIDATE = 2
        FOLLOWER = 3

    def __init__(self, application: Any, addr: Address, contact_addr: Address = None, passive: bool = False):
        socket.setdefaulttimeout(RaftNode.RPC_TIMEOUT)
        self.app:                       Any = application
        self.address:                   Address = addr
        self.type:                      RaftNode.NodeType = None
        self.message_log:               List[str] = []
        self.term_log:                  List[int] = []    
        self.commit_index_log:          List[int] = []
        self.committed_length:          int = 0
        self.election_term:             int = 0
        self.cluster_addr_list:         List[Address] = []
        self.troubled_clusters:         Dict[str, Dict[str, Any]] = {}
        self.cluster_leader_addr:       Address = None
        self.heartbeat_timer:           int = 0
        self.vote_count:                int = 0
        self.voted_for:                 tuple[int, Address] = (0, None)
        self.accepted_addr_list:        List[int] = []
        self.current_timeout:           int = 0
        self.commit_index:              int = 0
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
        if self.type == RaftNode.NodeType.LEADER:
            print(f"{bcolors.OKGREEN}[{self.election_term}] [{self.address}] [{time.strftime('%H:%M:%S')}]{bcolors.ENDC} {text}")
        elif self.type == RaftNode.NodeType.CANDIDATE:
            print(f"{bcolors.WARNING}[{self.election_term}] [{self.address}] [{time.strftime('%H:%M:%S')}]{bcolors.ENDC} {text}")
        else:
            print(f"[{self.election_term}] [{self.address}] [{time.strftime('%H:%M:%S')}] {text}")

    def __initialize_as_leader(self):
        self.__print_log("Initialize as leader node...")
        self.cluster_leader_addr = self.address
        self.type = RaftNode.NodeType.LEADER
        request = {
            "cluster_addr_list": self.cluster_addr_list,
            "cluster_leader_addr": self.address,
            "election_term":       self.election_term,
            "message_log":          self.message_log,
            "commit_index":        self.commit_index,
            "method":              "sync"
        }

        # Send request to all nodes in cluster
        for addr in self.cluster_addr_list:
            if addr != self.address:
                self.__send_request(request, "heartbeat", addr)

        # self.heartbeat_thread.stop()
        self.heartbeat_thread = Thread(target=asyncio.run, args=[
                                       self.__leader_heartbeat()])
        self.heartbeat_thread.start()

    # async def __hearbeat_to_follower(self, follower_addr: Address, request: Dict[str, Any]):
    #     self.__print_log(f"[Leader] Sending heartbeat to {follower_addr}")
    #     self.__send_request(request, "heartbeat", follower_addr)

    async def __leader_heartbeat(self):
        while self.type == RaftNode.NodeType.LEADER:
            self.__print_log("[Leader] Sending heartbeat...")
            self.__print_log(self.__log_repr())
            tasks = []
            for addr in self.cluster_addr_list:
                if addr != self.address:
                    request = {
                        "cluster_addr_list": self.cluster_addr_list,
                        "method": "sync",
                        "curr_term": self.election_term,
                        "prefix_len": len(self.message_log) - len(self.commit_index_log) if len(self.message_log) > 0 else 0,
                        "last_term": self.term_log[len(self.message_log) - len(self.commit_index_log) - 1] if len(self.message_log) > 0 else self.election_term,
                        "messages": self.message_log[-(len(self.commit_index_log)):] if len(self.commit_index_log) > 0 else [],
                        "last_message": self.message_log[len(self.message_log) - len(self.commit_index_log) - 1] if len(self.message_log) > 0 else "",
                        "terms": self.term_log[-len(self.commit_index_log):] if len(self.commit_index_log ) > 0 else [],
                        "leader_commit": self.committed_length,
                        "cluster_leader_addr": {
                            "ip":   self.address.ip,
                            "port": self.address.port,
                        },
                        "election_term": self.election_term,
                    }

                    if str(addr) in self.troubled_clusters.keys():
                        response = self.troubled_clusters[str(addr)]
                        # When follower is zeroed (ex: cold restart)
                        if response["message_len"] == 0 and len(self.message_log) != 0:
                            request["prefix_len"] = 0
                            request["messages"] = self.message_log
                            request["terms"] = self.term_log
                        
                        # When follower is delayed (ex: network delay)
                        else:
                            for idx in range(len(self.message_log) - 1, -1, -1):
                                if self.message_log[idx] == response["last_message"] and self.term_log[idx] == response["last_term"]:
                                    # set the prefix_len, last_term, messages, last_message, terms
                                    request["prefix_len"] = len(self.message_log) - idx
                                    request["last_term"] = self.term_log[idx]
                                    request["last_message"] = self.message_log[idx]
                                    request["messages"] = self.message_log[idx:]
                                    request["terms"] = self.term_log[idx:]
                                    break
                            # Last message not found, send all messages
                            request["prefix_len"] = 0
                            request["messages"] = self.message_log
                            request["terms"] = self.term_log

                    # Add to tasks list
                    tasks.append(asyncio.create_task(self.__send_heartbeat(request, "heartbeat", addr)))

            responses = await asyncio.gather(*tasks)

            for response in responses:
                # Troubled cluster, no more
                if ("ack" in response.keys() and response["ack"] == True) and ("addr" in response.keys() and response["addr"] in self.troubled_clusters.keys()):
                    self.troubled_clusters.pop(response["addr"])

                # Follower acked the message, increment commit index
                if self.commit_index_log.__len__() > 0 and ("ack" in response.keys() and response["ack"] == True):
                    self.commit_index_log[-1] += 1

                # Troubled cluster, offer help (call 911)
                if ("ack" in response.keys() and response["ack"] == False) and ("status" in response.keys() and response["status"] != "failure"):
                    self.troubled_clusters[str(response["addr"])] = response


            if self.commit_index_log.__len__() > 0 and (self.commit_index_log[-1] >= (len(self.cluster_addr_list) // 2) + 1):
                for i in range(self.committed_length, self.committed_length + len(self.commit_index_log)):
                        if i > len(self.message_log) - 1:
                            break
                        method = self.message_log[i].split("(")[0]
                        parameter = self.message_log[i].split("(")[1].split(")")[0].replace('"', "")
                        self.__app_execute(method, parameter)
                self.committed_length += len(self.commit_index_log)
                self.commit_index_log = []
                
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
        self.term_log = response["term_log"]
        self.committed_length = response["leader_commit"]
        self.election_term = response["election_term"]
        self.cluster_addr_list = list(map(lambda addr: Address(addr["ip"], addr["port"]), response["cluster_addr_list"]))
        self.cluster_leader_addr = redirected_addr

    def __initialize_as_follower(self):
        self.__print_log("Initialize as follower node...")
        self.type = RaftNode.NodeType.FOLLOWER
        self.heartbeat_thread = Thread(target=asyncio.run, args=[
                                    self.__follower_heartbeat()])
        self.heartbeat_thread.start()

    async def __follower_heartbeat(self):
        self.heartbeat_timer = 0
        self.current_timeout = self.__get_random_timeout()
        current_term = self.election_term
        while self.type == RaftNode.NodeType.FOLLOWER and current_term == self.election_term:
            self.heartbeat_timer += 1
            print(bcolors.OKBLUE, "Timer:", self.heartbeat_timer, bcolors.ENDC)
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
                                        self.__candidate_heartbeat()])
        self.heartbeat_thread.start()


    async def __candidate_heartbeat(self):
        while self.type == RaftNode.NodeType.CANDIDATE:
            self.heartbeat_timer = 0
            self.current_timeout = self.__get_random_timeout()
            self.election_term += 1
            self.voted_for = (self.election_term, self.address)
            self.vote_count = 1
            prev_time = time.time()
            while self.heartbeat_timer < self.current_timeout and self.type == RaftNode.NodeType.CANDIDATE:
                print(bcolors.OKBLUE, "Timer:", self.heartbeat_timer, bcolors.ENDC)
                await self.__send_vote_request()
                curr_time = time.time()
                self.heartbeat_timer += curr_time - prev_time
                prev_time = curr_time
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)

    async def __send_vote_request(self):
        request = {
            "election_term": self.election_term,
            "candidate_addr": {
                "ip":   self.address.ip,
                "port": self.address.port,
            },
            "commit_index": self.commit_index,
        }
        tasks = []
        self.accepted_addr_list = []
        for addr in self.cluster_addr_list:
            if addr != self.address:
                tasks.append(asyncio.create_task(self.__send_heartbeat(request, "handle_vote_request", addr)))
        responses = await asyncio.gather(*tasks)
        for response in responses:
            resp_addr = Address(response["address"]["ip"], response["address"]["port"])
            if response["status"] == "success" and resp_addr not in self.accepted_addr_list :
                self.accepted_addr_list.append(resp_addr)
                self.vote_count += 1
        if self.vote_count > len(self.cluster_addr_list) / 2 and self.type == RaftNode.NodeType.CANDIDATE:
            self.__initialize_as_leader()
 
    
    def __change_leader(self, request: json):
        self.cluster_leader_addr = Address(request["cluster_leader_addr"]["ip"], request["cluster_leader_addr"]["port"])
        self.election_term = request["election_term"]
        self.voted_for = (self.election_term, self.cluster_leader_addr)
        self.commit_index = request["commit_index"]
        self.__initialize_as_follower()
        
    def __app_execute(self, method: str, params: Any):
        function = getattr(self.app, "push" if method == "enqueue" else "pop" if method == "dequeue" else None)
        return function(params)

    #
    # External Log methods
    #

    def app_execute(self, json_request: json) -> "json":
        # print("Type??", type(json_request), "at", str(self.address))
        request = json.loads(json_request)
        match request["method"]:
            case inp if inp in ["enqueue", "dequeue"]:
                try:
                    if request["method"] == "enqueue":
                        log_msg = 'enqueue("' + request["params"][0] + '")'
                    else:
                        log_msg = "dequeue()"
                    self.__push([log_msg], [self.election_term], self.message_log.__len__())
                    return {"status" : "success", "ack": True}
                except:
                    return {"status" : "success", "ack": False}
            case "sync":
                try:
                    # Does some preliminary checks
                    if self.election_term < request["curr_term"]:
                        self.election_term = request["curr_term"]
                    if request["curr_term"] == self.election_term:
                        self.type = self.NodeType.FOLLOWER
                    logOk: bool = (self.message_log.__len__() >= request["prefix_len"]) and (request["prefix_len"] == 0 or self.term_log[request["prefix_len"] - 1] == request["last_term"])
                    if self.election_term == request["curr_term"] and logOk:
                        self.__push(request["messages"], request["terms"], int(request["prefix_len"]))
                        if request["leader_commit"] > self.committed_length:
                            for i in range(self.committed_length, request["leader_commit"]):
                                method = self.message_log[i].split("(")[0]
                                parameter = self.message_log[i].split("(")[1].split(")")[0].replace('"', "")
                                self.__app_execute(method, parameter)
                            self.committed_length = request["leader_commit"]
                        return {"status" : "success", "ack": True}
                    return {
                        "status" : "success",
                        "ack": False, 
                        "addr": str(self.address),
                        "message_len": len(self.message_log), 
                        "last_message": self.message_log[-1] if len(self.message_log) > 0 else "", 
                        "last_term": self.term_log[-1] if len(self.term_log) > 0 else 0
                    }
                except:
                    return {
                        "status" : "success",
                        "ack": False, 
                        "message_len": len(self.message_log), 
                        "last_message": self.message_log[-1] if len(self.message_log) > 0 else "", 
                        "last_term": self.term_log[-1] if len(self.term_log) > 0 else 0
                    }
        
            
    #
    #   Internal Log Methods
    #
    def __get_log(self) -> List[str]:
        return self.message_log
    
    def __push(self, messages: List[str], terms: List[int], prefix_len: int):
        if (len(messages) == 0) and prefix_len == len(self.message_log):
            return

        while prefix_len < self.message_log.__len__():
            self.committed_length -= 1 if self.committed_length > 0 else 0
            self.term_log.pop(0)
            self.message_log.pop(0)

        for i in range(len(messages)):
            self.message_log.append(messages[i])
            self.term_log.append(terms[i])

    def __pop(self) -> str:
        if (self.committed_length == 0):
            return "err: you dum dum theres nothing on the list!" # yg ganti ini juga dum dum diam kamu
        self.committed_length -= 1
        self.term_log.pop(0)
        return self.message_log.pop(0)
    
    def __log_repr(self) -> str:
        repr_output = "Representation: \n"
        repr_output += "Term log    : " + str(self.term_log) + "\n"
        repr_output += "Message log : " + str(self.message_log) + "\n"
        repr_output += "Curr term   : " + str(self.election_term) + "\n"
        repr_output += "Committed   : " + str(self.committed_length) + "\n"
        # repr_output += "Queue       : " + str(self.app)
        # repr_output += "\nType        : " + str(self.type) + "\n"
        # repr_output += "Addr        : " + str(self.address) + "\n"
        # repr_output += "Leader Addr : " + str(self.cluster_leader_addr) + ""
        return repr_output 

    #
    #   RPC methods
    #
    def __send_request(self, request: Any, rpc_name: str, addr: Address) -> "json":
        # Warning : This method is blocking
        node = ServerProxy(f"http://{addr.ip}:{addr.port}")
        json_request = json.dumps(request)
        rpc_function = getattr(node, rpc_name)
        response = {
            "status": "failure",
            "address": {
                "ip":   addr.ip,
                "port": addr.port,
            }
        } 
        try:
            response = json.loads(rpc_function(json_request))
        except (ConnectionRefusedError, ConnectionResetError, ConnectionError, ConnectionAbortedError):
            self.__print_log(f"[{rpc_name}] Connection error")
            response = {
                "status": "failure",
                "ack": False,
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        except socket.timeout:
            self.__print_log(f"[{rpc_name}] Timeout")
            response = {
                "status": "failure",
                "ack": False,
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        except Exception as e:
            self.__print_log(f"[{rpc_name}] Unknown error : {e} at {str(addr)}")
            response = {
                "status": "failure",
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            } 
        print(f"{bcolors.OKBLUE} [<- {addr} ] {response} {bcolors.ENDC}")
        return response
    
    async def __send_heartbeat(self, request: Any, rpc_name: str, addr: Address) -> "json":
        node = ServerProxy(f"http://{addr.ip}:{addr.port}")
        json_request = json.dumps(request)
        rpc_function = getattr(node, rpc_name)
        try:
            response = json.loads(rpc_function(json_request))
        except (ConnectionRefusedError, ConnectionResetError, ConnectionError, ConnectionAbortedError):
            self.__print_log(f"[{rpc_name}] Heartbeat Connection error")
            response = {
                "status": "failure",
                "ack": False,
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        except socket.timeout:
            self.__print_log(f"[{rpc_name}] Heartbeat Timeout")
            response = {
                "status": "failure",
                "ack": False,
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            }
        except Exception as e:
            self.__print_log(f"[{rpc_name}] Unknown Heartbeat error : {e} at {str(addr)}")
            response = {
                "status": "failure",
                "address": {
                    "ip":   addr.ip,
                    "port": addr.port,
                }
            } 
        # self.__print_log(response)
        print(f"{bcolors.OKBLUE} [<- {addr} ] {response} {bcolors.ENDC}")
        return response

    #
    # Inter-node RPCs
    #
    def heartbeat(self, json_request: str) -> "json":
        request = json.loads(json_request)

        # Process the request if the term >= current term
        if request["election_term"] >= self.election_term:
            self.cluster_addr_list = list(map(lambda addr: Address(addr["ip"], addr["port"]), request["cluster_addr_list"]))
            self.heartbeat_timer = 0
            follower_resp = self.app_execute(json_request)

            # If the term is higher, change the leader to the sender
            if (request["election_term"] > self.election_term and request["election_term"] > self.voted_for[0]) or self.cluster_leader_addr is None:
                self.__change_leader(request)
                # self.election_term = request["election_term"]
                # self.voted_for = None
                # self.cluster_leader_addr = Address(request["cluster_leader_addr"]["ip"], request["cluster_leader_addr"]["port"])
            response = {
                "status": "success",
            }
            response.update(follower_resp)

        # If the term is lower, reject the request
        else:
            response = {
                "status": "failure",
            }
        self.__print_log(self.__log_repr())
        return json.dumps(response)
    
    def apply_membership(self, json_request: str) -> "json":
        request = json.loads(json_request)
        if (self.type == RaftNode.NodeType.LEADER):
            new_addr = Address(request["address"]["ip"], request["address"]["port"])
            if new_addr not in self.cluster_addr_list:
                self.__print_log(f"Add new node {new_addr}")
                self.cluster_addr_list.append(new_addr)
            response = {
                "status": "success",
                "cluster_addr_list": self.cluster_addr_list,
                "message_log": self.message_log,
                "term_log": self.term_log,
                "election_term": self.election_term,
                "leader_commit": self.committed_length,
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
        if self.election_term == request["election_term"] and self.voted_for[0] == request["election_term"] and self.voted_for[1] == candidate_addr:
            self.heartbeat_timer = 0
            response = {
                "status": "success",
                "address": {
                    "ip":   self.address.ip,
                    "port": self.address.port,
                }
            }
        elif self.election_term == request["election_term"] or request["election_term"] <= self.voted_for[0]:
            response = {
                "status": "failure",
                "message": "Already voted for another candidate",
                "address": {
                    "ip":   self.address.ip,
                    "port": self.address.port,
                }
            }
        elif self.election_term < request["election_term"]:
            self.cluster_leader_addr = candidate_addr
            self.election_term = request["election_term"]
            self.commit_index = request["commit_index"]
            self.voted_for = (self.election_term, candidate_addr)
            self.__initialize_as_follower()
            response = {
                "status": "success",
                "address": {
                    "ip":   self.address.ip,
                    "port": self.address.port,
                }
            }
            print(f"{bcolors.WARNING} Voted for {candidate_addr} {bcolors.ENDC}")
        else :
            response = {
            "status": "failure",
            "message": "Election term is lower than current term"
        }
        return json.dumps(response)
    
    def get_node_status(self, json_request: str) -> "json":
        request = json.loads(json_request)
        response = {
            "status": "success",
            "election_term": self.election_term,
            "cluster_leader_addr": {
                "ip":   self.cluster_leader_addr.ip,
                "port": self.cluster_leader_addr.port,
            },
            "cluster_addr_list": self.cluster_addr_list,
            "message_log": self.message_log,
            "term_log": self.term_log,
            "commit_index": self.commit_index,
            "leader_commit": self.committed_length,
            "type": self.type.value,
            "voted_for": {
                "election_term": self.voted_for[0],
                "candidate_addr": str(self.voted_for)
            },
            "commit_index": self.commit_index,
            "commit_index_log": self.commit_index_log,
            "committed_length": self.committed_length,
            "message_log": self.message_log,
            "term_log": self.term_log,
        }
        return json.dumps(response)
    
    # def change_leader(self, json_request: str) -> "json":
    #     request = json.loads(json_request)
    #     self.cluster_leader_addr = Address(request["cluster_leader_addr"]["ip"], request["cluster_leader_addr"]["port"])
    #     self.election_term = request["election_term"]
        # self.scommit_index = request["commit_index"]
    #     self.type = RaftNode.NodeType.FOLLOWER
    #     self.__initialize_as_follower()
    #     response = {"status": "success"}
    #     return json.dumps(response)

    # Client RPCs
    def request_log(self, _: any):
        if self.type == RaftNode.NodeType.LEADER:
            log = "[===]              ~Log~              [===]\n"
            for i in range(len(self.message_log)):
                log += "Term: " + str(self.term_log[i]) + " | Method: " + str(self.message_log[i]) + "\n"
            response = {"status": "success", "log": log}
        else:
            response =  {
                "status": "redirected",
                "address": {
                    "ip":   self.cluster_leader_addr.ip,
                    "port": self.cluster_leader_addr.port,
                }
            }
        return json.dumps(response)
    
    def execute(self, json_request: str) -> "json":
        response = {
            "status": self.AppResponse.FAILURE.value,
        }
        request = json.loads(json_request)
        if self.type == RaftNode.NodeType.LEADER:
            # If leader then add first to your own log
            response = {
                "status": "success",
                "ack": False
            }
            while response["ack"] == False:
                response = self.app_execute(json_request)
                time.sleep(0.05)
            if request["method"] in ["enqueue", "dequeue"]:
                self.commit_index_log.append(1)
        else:
            response = {
                "status": "redirected",
                "address": {
                    "ip":   self.cluster_leader_addr.ip,
                    "port": self.cluster_leader_addr.port,
                }
            }
        return json.dumps(response)