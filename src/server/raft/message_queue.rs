use lib::Response;

struct MessageQueue {
    queue: Vec<String>,
}

impl MessageQueue {
    fn new() -> Self {
        Self { queue: Vec::new() }
    }

    fn push(&mut self, message: String) -> Response {
        self.queue.push(message);
        Response::SUCCESS
    }

    fn pop(&mut self) -> Result<String, Response> {
        match self.queue.is_empty() {
            true => Err(Response::FAILURE),
            false => Ok(self.queue.remove(0)),
        }
    }

    fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }
}