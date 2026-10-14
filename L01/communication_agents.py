# Vieru Iosif
# 12.10.2026
#
# Agents exchange messages
#   
#   There must be those states:
#       an agent does not answer;
#       a message is delayed;
#       an agent sends incorrect information;
#       two agents simultaneously request information from the same agent.

import mesa
from datetime import datetime, timezone
from enum import Enum

NO_AGENTS = 5

class MessageType(Enum):
    HEALTHY = 0
    DELAYED = 1
    CORRUPT = 2

class Message:
    def __init__(self, sender: int, receiver: int, messageType: MessageType, content: str):
        self.sender = sender
        self.receiver = receiver
        self.messageType = messageType
        self.content = content
        self.timestamp = datetime.now(timezone.utc)
        self.retries = 0
        self.consumed = False
        self.marked_for_deletion = False

class CommAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        self.inbox = list()

    def step(self):
        print(f"agent with id: {self.unique_id} -> I have {len(self.inbox)} messages in my inbox.")
        for i in self.inbox:
            self.consume_message(i)
            
        # keep only messages that are not marked for deletion
        self.inbox = [x for x in self.inbox if x.marked_for_deletion == False]
        self.create_message()

    def create_message(self):
        sender = self.unique_id
        others = self.model.agents.select(lambda a : a is not self)
        receiver = self.model.random.choice(others).unique_id
        messageType = self.model.random.choice(list(MessageType))
        content = f"agent [{sender}] says hello"

        self.model.messages.append(Message(sender, receiver, messageType, content))

    def consume_message(self, message: Message):
        if message.messageType == MessageType.HEALTHY:
            message.consumed = True

        if message.messageType == MessageType.CORRUPT:
            print(f"message is corrupt (type: {message.messageType}), cannot consume it, retries: {message.retries}")
            if message.retries == 5:
                print(f"message is being deleted after 5 retries.")
                message.marked_for_deletion = True

        if message.messageType == MessageType.DELAYED:
            print(f"message is delayed (type: {message.messageType}), cannot consume it, retries: {message.retries}")

            # at 3 retires it will get marked as consumed
            if message.retries == 3:
                message.consumed = True

        if message.consumed == True:
            print(f"consumed: {message.consumed}, sender: {message.sender}, receiver: {message.receiver}, type: {message.messageType}, content: {message.content}, timestamp: {message.timestamp}, retries: {message.retries}")
            message.marked_for_deletion = True

        message.retries += 1

class CommModel(mesa.Model):
    def __init__(self, num_agents):
        super().__init__(seed=42)

        self.messages = list()

        for _ in range(num_agents):
            new_agent = CommAgent(self)
            self.agents.add(new_agent)

    def step(self):
        for i in self.messages:
            agent = self.agents.select(lambda a : a.unique_id == i.receiver)[0]
            agent.inbox.append(i)
        self.messages.clear()

        self.agents.shuffle_do('step')

if __name__ == "__main__":
    model = CommModel(NO_AGENTS)

    for _ in range(0, 6):
        model.step()
