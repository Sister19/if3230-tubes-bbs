from enum import Enum

class MessageQueue:
    class Response(Enum):
        FAILURE = 0
        SUCCESS = 1

    def __init__(self) -> None:
        self.queue = []

    def push(self, message: str):
        self.queue.append(message)
        return {"status": self.Response.SUCCESS.value}

    def pop(self, _: any) -> str:
        return {"status": self.Response.SUCCESS.value, "result": self.queue.pop(0)}

    def is_empty(self) -> bool:
        return {"status": self.Response.SUCCESS.value, "result": len(self.queue) == 0}

    def __str__(self) -> str:
        return str(self.queue)

    def __repr__(self) -> str:
        return str(self.queue)
