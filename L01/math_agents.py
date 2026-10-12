# Vieru Iosif
# 12.10.2026
#
# Model -> holds final data (total_sum, average, histogram of numbers)
#       -> shares work among every agent (splits the data array)
#       -> spawns agents
#
# Agent -> calculates sum, count, histogram, writes to model

import mesa
import random

DATA_SIZE = 10000
NO_AGENTS = 10
MAX_DATA_PER_AGENT = 10000 // NO_AGENTS
DATA = [random.randint(0, 10) for _ in range(0, DATA_SIZE)]

RAND_FAULTY_AGENT = random.randint(0, NO_AGENTS)

class MathAgent(mesa.Agent):
    def __init__(self, model: mesa.Model, data: list):
        super().__init__(model)
        self.data = data
        self.histogram = dict()

    def step(self):
        if self.unique_id == RAND_FAULTY_AGENT:
            rand_val = random.randint(0, 1000)
            print("I am faulty: ", self.unique_id, " adding ", rand_val, " to the total sum")
            self.model.total_sum += rand_val

        for i in self.data:
            self.model.count += 1
            self.model.total_sum += i

            if not self.histogram.get(i):
                self.histogram[i] = 1;
            else:
                self.histogram[i] += 1;

        for k in self.histogram:
            if not self.model.histogram.get(k):
                self.model.histogram[k] = self.histogram[k]
            else:
                self.model.histogram[k] += self.histogram[k]

class MathModel(mesa.Model):
    def __init__(self, num_agents):
        super().__init__()
        
        for i in range(num_agents):
            data = DATA[i * MAX_DATA_PER_AGENT: i * MAX_DATA_PER_AGENT + MAX_DATA_PER_AGENT]
            new_agent = MathAgent(self, data=data)
            self.agents.add(new_agent)

        self.total_sum = 0
        self.count = 0
        self.histogram = dict()

    def step(self):
        self.agents.do('step')

        print("[model] total sum: ", self.total_sum, " avg: ", self.total_sum / self.count)
        print("[model] histogram:", self.histogram)

if __name__ == "__main__":
    model = MathModel(NO_AGENTS)
    model.step()

    total_sum = sum(DATA)
    count = DATA_SIZE
    histogram = dict()

    for i in DATA:
        if not histogram.get(i):
            histogram[i] = 1
        else:
            histogram[i] += 1
    
    print("[python] total sum: ", total_sum, "avg: ", total_sum / count)
    print("[python] histogram: ", histogram)
