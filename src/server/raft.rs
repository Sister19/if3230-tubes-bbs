mod message_queue;

use std::net::SocketAddr;
use std::time::SystemTime;
use axum::Json;
use lib::NodeType;

struct RaftNode {
    address: SocketAddr,
    node_type: NodeType,
    log: Vec<(String, String)>,
    election_term: u32,
    cluster_addr_list: Vec<SocketAddr>,
    cluster_leader_addr: Option<SocketAddr>,
    heartbeat_timer: u32,
    vote_count: u32,
    voted_for: Option<SocketAddr>,
    current_timeout: u32,
    commit_index: u32,
}

impl RaftNode {
    const HEARTBEAT_INTERVAL: u32 = 2;
    const ELECTION_TIMEOUT_MIN: u32 = 5;
    const ELECTION_TIMEOUT_MAX: u32 = 8;
    const RPC_TIMEOUT: u32 = 2;
    const FOLLOWER_TIMEOUT: u32 = 10;
    
    fn new(&mut self, addr: Option<SocketAddr>, contact_addr: Option<SocketAddr>, passive: bool) -> Self {
        let init_self = Self {
            address: addr.unwrap(),
            node_type: NodeType::FOLLOWER,
            log: Vec::new(),
            election_term: 0,
            cluster_addr_list: Vec::new(),
            cluster_leader_addr: None,
            heartbeat_timer: 0,
            vote_count: 0,
            voted_for: None,
            current_timeout: 0,
            commit_index: 0,
        };

        if passive {
            self.print_log(format!("Node {} is now a follower", self.address))
        } else {
            self.print_log(format!("Node {} inited", self.address))
        };
        
        if contact_addr.is_some() {
            self.try_apply_membership(contact_addr.unwrap());
            self.init_follower();
        } else {
            self.cluster_addr_list.push(self.address);
            self.init_leader();
        };

        init_self
    }

    // RaftNode methods
    fn print_log(&self, text: String) {
        println!("[{}] [{:?}]: {}", self.address, SystemTime::now(), text);
    }

    fn get_random_timeout(&self) -> u32 {
        // TODO
        0
    }

    fn init_leader(&self) {
        // TODO
    }

    async fn leader_heartbeat(&self) {
        // TODO
    }

    fn try_apply_membership(&self, addr: SocketAddr) {
        // TODO
    }

    fn init_follower(&self) {
        // TODO
    }

    async fn follower_heartbeat(&self) {
        // TODO
    }

    fn init_candidate(&self) {
        // TODO
    }

    async fn candidate_heartbeat(&self) {
        // TODO
    }

    fn send_vote_request(&self) {
        // TODO
    }

    fn send_request(&self, addr: SocketAddr, request: Json<lib::HelloRequest>) -> Json<lib::HelloResponse> {
        // TODO
        Json(lib::HelloResponse { message: "Send Request".to_string() })
    }

    // RPC Inter-node
    fn heartbeat(&self, json_request: String) -> Json<lib::HelloResponse> {
        // TODO
        Json(lib::HelloResponse { message: "Heartbeat".to_string() })
    }

    fn handle_vote_request(&self, json_request: String) -> Json<lib::HelloResponse> {
        // TODO
        Json(lib::HelloResponse { message: "Handling Vote Request".to_string() })
    }

    fn change_leader(&self, json_request: String) -> Json<lib::HelloResponse> {
        // TODO
        Json(lib::HelloResponse { message: "Change Leader".to_string() })
    }

    // Client RPC
    fn execute(&self, json_request: String) -> Json<lib::HelloResponse> {
        // TODO
        Json(lib::HelloResponse { message: "Executed".to_string() })
    }

}