CLIENT_IP = 127.0.0.1
CLIENT_PORT = 2441
SERVER_IP = 127.0.0.1
SERVER_PORT = 2431

run_client_default_args: client
	@cd target/client/debug && ./client $(CLIENT_IP) $(CLIENT_PORT) $(SERVER_IP) $(SERVER_PORT)

all: client server

client:
	CARGO_TARGET_DIR=target/client cargo build --bin client

server:
	CARGO_TARGET_DIR=target/server cargo build --bin server