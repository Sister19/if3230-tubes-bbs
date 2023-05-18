use core::panic;
use std::net::SocketAddr;
use std::io::Write;
use std::env;
use xmlrpc::{Request, Value};
// use serde_json::json;
// use serde_json::Value;

struct RaftClient {
    rpc_timeout: u32,
    client_addr: SocketAddr,
    server_addr: SocketAddr,
}

impl RaftClient {
    const RPC_TIMEOUT: u32 = 2;

    fn new(client_addr: SocketAddr, server_addr: SocketAddr) -> Self {
        Self {
            rpc_timeout: Self::RPC_TIMEOUT,
            client_addr,
            server_addr,
        }
    }

    fn change_server(&mut self, server_addr: SocketAddr) {
        self.server_addr = server_addr;
    }

    fn send_request(&self, req: &Value, rpc_name: &str, address: &SocketAddr) -> Result<Value, String> {
        let rpc_request = Request::new(rpc_name)
            .arg(req.clone());
        let response = rpc_request.call_url(&format!("http://{}:{}", address.ip(), address.port() )).unwrap();
        match response {
            Value::Struct(mut map) => {
                if let Some(Value::String(status)) = map.remove("status") {
                    if status == "failure" {
                        return Err(format!("RPC call to {}:{} failed", address.ip(), address.port()));
                    }
                }
                Ok(Value::Struct(map))
            }
            _ => Err("Invalid response from server".to_string()),
        }
    }
    
    fn enqueue(&self, message: String) -> Result<Value, String> {
        let request = Value::Struct(vec![
            ("method".to_string(), Value::String("push".to_string())),
            ("params".to_string(), Value::String(message)),
        ]
        .into_iter()
        .collect());
        self.send_request(&request, "execute", &self.server_addr)
    }

    fn dequeue(&self) -> Result<Value, String> {
        let request = Value::Struct(vec![].into_iter().collect());
        self.send_request(&request, "dequeue", &self.server_addr)
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 5 {
        println!("Usage: client <client_ip> <client_port> <server_ip> <server_port>");
        panic!("Invalid number of arguments")
    } else {
        println!("You're running client on {}:{} and connecting to server on {}:{}", args[1], args[2], args[3], args[4]);
    };
    
    let mut ip: Vec<u8> = args[1].split('.').map(|x| x.parse::<u8>().unwrap()).collect();
    let client_address = SocketAddr::from(([ip[0], ip[1], ip[2], ip[3]], args[2].parse::<u16>().unwrap()));
    ip = args[3].split('.').map(|x| x.parse::<u8>().unwrap()).collect();
    let server_address = SocketAddr::from(([ip[0], ip[1], ip[2], ip[3]], args[4].parse::<u16>().unwrap()));

    let mut client = RaftClient::new(client_address, server_address);

    // while true loop
    loop {
        print!("> ");
        std::io::stdout().flush().unwrap();
        let mut input = String::new();
        std::io::stdin().read_line(&mut input).unwrap();
        // trim and split input by space
        let input: Vec<&str> = input.trim().split(' ').collect();
        
        // match first word of input
        match input[0] {
            "enqueue" => {
                let message = input[1..].join(" ");
                let response = client.enqueue(message);
                match response {
                    Ok(response) => {
                        println!("Response: {:?}", response);
                    }
                    Err(err) => {
                        println!("Error: {:?}", err);
                    }
                }
            }
            "dequeue" => {
                let response = client.dequeue();
                match response {
                    Ok(response) => {
                        println!("Response: {:?}", response);
                    }
                    Err(err) => {
                        println!("Error: {:?}", err);
                    }
                }
            }
            "node" => {
                if input.len() < 2 {
                    println!("Invalid command");
                    continue;
                }
                match input[1] {
                    "status" => {
                        println!("Server node at {}:{}", client.server_addr.ip(), client.server_addr.port());
                    }
                    "change" => {
                        ip = input[2].split('.').map(|x| x.parse::<u8>().unwrap()).collect();
                        let server_address = SocketAddr::from(([ip[0], ip[1], ip[2], ip[3]], input[3].parse::<u16>().unwrap()));
                        client.change_server(server_address);
                        println!("Server node changed to {}:{} ", client.server_addr.ip(), client.server_addr.port());
                    }
                    _ => {
                        println!("Invalid command");
                    }
                }
            }
            _ => {
                println!("Invalid command");
            }
        }
    }
}
