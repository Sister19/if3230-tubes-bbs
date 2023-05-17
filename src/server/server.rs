use std::net::SocketAddr;
use std::env;
use axum::{routing::post, Router};
use lib::{HelloRequest, HelloResponse};

async fn handle_request(request: axum::extract::Json<HelloRequest>) -> axum::response::Json<HelloResponse> {
    println!("{}", request.message);
    let response = HelloResponse {
        message: format!("Hello, {}!", request.message),
    };
    axum::response::Json(response)
}

#[tokio::main]
async fn main() {
    let args: Vec<String> = env::args().collect();

    let address = if args.len() > 2 {
        let ip: Vec<u8> = args[1].split('.').map(|x| x.parse::<u8>().unwrap()).collect();
        SocketAddr::from(([ip[0], ip[1], ip[2], ip[3]], args[2].parse::<u16>().unwrap()))
    } else {
        SocketAddr::from(([127, 0, 0, 1], 2434))
    };
    
    println!("server running on {}", address);
    let app = Router::new().route("/rpc", post(handle_request));
    axum::Server::bind(&address)
        .serve(app.into_make_service())
        .await
        .unwrap();
}