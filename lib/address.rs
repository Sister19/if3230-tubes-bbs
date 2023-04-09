pub struct Address {
    ip: String,
    port: u16,
}

impl Address {
    pub fn new(ip: String, port: u16) -> Address {
        Address { ip, port }
    }

    pub fn ip(&self) -> &String {
        &self.ip
    }

    pub fn port(&self) -> &u16 {
        &self.port
    }

    pub fn set_ip(&mut self, ip: String) {
        self.ip = ip;
    }

    pub fn set_port(&mut self, port: u16) {
        self.port = port;
    }

    pub fn to_string(&self) -> String {
        format!("{}:{}", self.ip, self.port)
    }

    pub fn from_string(address: String) -> Address {
        let mut parts = address.split(':');
        let ip = parts.next().unwrap().to_string();
        let port = parts.next().unwrap().parse::<u16>().unwrap();

        Address { ip, port }
    }
}

fn main() {
    let address = Address::from_string("127.0.0.1:8080".to_string());
    println!("{} {}", address.ip(), address.port());
}