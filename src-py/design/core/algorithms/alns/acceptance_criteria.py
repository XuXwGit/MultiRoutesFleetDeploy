import random
import math

class SimulatedAnnealing:
    def __init__(self, initial_temperature, cooling_rate):
        self.temperature = initial_temperature
        self.cooling_rate = cooling_rate
    
    def accept(self, new_objective, best_objective):
        if new_objective > best_objective:
            return True
        else:
            probability = math.exp((new_objective - best_objective) / self.temperature)
            self.temperature *= self.cooling_rate
            return random.random() < probability