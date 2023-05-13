class MessageQueue:
    def __init__(self) -> None:
        self.queue = []

    def push(self, message: str):
        self.queue.append(message)

    def pop(self) -> str:
        return self.queue.pop(0)

    def is_empty(self) -> bool:
        return len(self.queue) == 0

    def __str__(self) -> str:
        return str(self.queue)

    def __repr__(self) -> str:
        return str(self.queue)
