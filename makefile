all: client server

client:
	CARGO_TARGET_DIR=target/client cargo build --bin client

server:
	CARGO_TARGET_DIR=target/server cargo build --bin server