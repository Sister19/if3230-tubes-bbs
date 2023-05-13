from lib.struct.address       import Address
from lib.raft          import RaftNode
from xmlrpc.server import SimpleXMLRPCServer
from lib.app           import MessageQueue
import sys
import socket


def start_serving(addr: Address, contact_node_addr: Address, passive: bool = False):
    print(f"Starting Raft Server at {addr.ip}:{addr.port}")
    with SimpleXMLRPCServer((addr.ip, addr.port)) as server:
        server.register_introspection_functions()
        server.register_instance(RaftNode(MessageQueue(), addr, contact_node_addr, passive))
        server.serve_forever()



if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("server.py <ip> <port> [<opt: contact ip> <opt: contact port> | <opt: -p>]")
        exit()

    contact_addr = None
    if len(sys.argv) == 5:
        contact_addr = Address(sys.argv[3], int(sys.argv[4]))
    server_addr = Address(sys.argv[1], int(sys.argv[2]))

    if len(sys.argv) == 4 and sys.argv[3] == "-p":
        start_serving(server_addr, contact_addr, True)
    else:
        start_serving(server_addr, contact_addr)
