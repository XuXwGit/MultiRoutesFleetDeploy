import numpy as np

class DualVarValues:
    def __init__(self):
        self.num_feasible_routes = 0
        self.value_u0 = 0
        self.value_u1 = []
        self.value_u2 = 0
        self.value_v = []
        self.value_w = []

    def initialize(self, num_ports, num_types, num_samples, num_feasible_routes):
        self.num_feasible_routes = num_feasible_routes
        self.value_u0 = 0
        self.value_u1 = np.zeros(num_ports)
        self.value_u2 = 0
        self.value_v = np.zeros([num_types, num_samples])
        self.value_w = np.zeros([num_feasible_routes, num_types, num_samples])

    def update_dual_var_values(self, u0, u1, u2, v, w):
        self.num_feasible_routes = len(w)
        self.value_u0 = u0
        self.value_u1 = u1
        self.value_u2 = u2
        self.value_v = v
        self.value_w = w

