use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct HelloRequest {
    pub message: String,
}

#[derive(Debug, Serialize)]
pub struct HelloResponse {
    pub message: String,
}