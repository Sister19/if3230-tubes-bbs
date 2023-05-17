use std::net::SocketAddr;
use std::env;
use reqwest::Client;
use serde_json::json;
use serde_json::Value;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    println!("Hello, from Client!");

    let address = if args.len() > 2 {
        let ip: Vec<u8> = args[1].split('.').map(|x| x.parse::<u8>().unwrap()).collect();
        SocketAddr::from(([ip[0], ip[1], ip[2], ip[3]], args[2].parse::<u16>().unwrap()))
    } else {
        SocketAddr::from(([127, 0, 0, 1], 8080))
    };
    println!("{} {}", address.ip(), address.port());

    let message_string = if args.len() > 3 {
        args[3].clone()
    } else {
        "Hello, World!".to_string()
    };

    let address_string = format!("http://{}:{}/rpc", address.ip(), address.port());
    let client = Client::new();
    let response = client.post(&address_string)
        .json(&json!({
            "message" : message_string
        }))
        .send()
        .await?
        .json::<Value>()
        .await?;

    println!("{:#?}", response);

    Ok(())
}
