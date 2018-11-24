import networkx as nx
import os
import numpy as np

###########################################
# Change this variable to the path to 
# the folder containing all three input
# size category folders
###########################################
path_to_inputs = "./all_inputs"

###########################################
# Change this variable if you want
# your outputs to be put in a 
# different folder
###########################################
path_to_outputs = "./outputs"


class Solver:

    def __init__(self, graph, num_buses, size_bus, constraints):
        self.graph = graph
        self.num_buses = num_buses
        self.size_bus = size_bus
        self.constraints = constraints
        self.solution = []

    def solve(self):
        pass

    def write(self):
        pass

    def score(self):
        pass

    def draw(self):
        pass


class SolveHeuristic(Solver):
    pass


class Optimizer(Solver):

    def __init__(self, graph, num_buses, size_bus, constraints, solution, method='basic'):

        if method == 'basic':
            self.optimizer = BasicOptimizer(graph, num_buses, size_bus, constraints, solution)

    def solve(self):
        self.optimizer.optimize()

class BasicOptimizer(Optimizer):

    def __init__(self, graph, num_buses, size_bus, constraints, solution, sample_size=100):
        super(self).__init__(graph, num_buses, size_bus, constraints, solution)
        self.sample_size = sample_size

    # Call this method to optimize the solution we are given for a specific score
    def optimize(self, max_iterations=1000):
        # If we don't have two buses no swapping will occur

        if self.num_buses < 2:
            return self.solution
        # Each iteration we will discover one swap to make
        for i in range(max_iterations):
            # If we have monte_carlo set to true we will sample the optimization space
            for sample in range(self.sample_size):
                # Sample a number of vertex combinations to try swapping
                # Pick two random buses and one random vertex from each bus to swap
                bus1, bus2 = np.random.choice(list(range(self.num_buses)), 2, replace=False)
                # Sample a vertex from each bus
                vertex1 = 




def parse_input(folder_name):
    '''
        Parses an input and returns the corresponding graph and parameters

        Inputs:
            folder_name - a string representing the path to the input folder

        Outputs:
            (graph, num_buses, size_bus, constraints)
            graph - the graph as a NetworkX object
            num_buses - an integer representing the number of buses you can allocate to
            size_buses - an integer representing the number of students that can fit on a bus
            constraints - a list where each element is a list vertices which represents a single rowdy group
    '''
    graph = nx.read_gml(folder_name + "/graph.gml")
    parameters = open(folder_name + "/parameters.txt")
    num_buses = int(parameters.readline())
    size_bus = int(parameters.readline())
    constraints = []
    
    for line in parameters:
        line = line[1: -2]
        curr_constraint = [num.replace("'", "") for num in line.split(", ")]
        constraints.append(curr_constraint)

    return graph, num_buses, size_bus, constraints

def solve(graph, num_buses, size_bus, constraints):
    #TODO: Write this method as you like. We'd recommend changing the arguments here as well
    pass

def main():
    '''
        Main method which iterates over all inputs and calls `solve` on each.
        The student should modify `solve` to return their solution and modify
        the portion which writes it to a file to make sure their output is
        formatted correctly.
    '''
    size_categories = ["small", "medium", "large"]
    if not os.path.isdir(path_to_outputs):
        os.mkdir(path_to_outputs)

    for size in size_categories:
        category_path = path_to_inputs + "/" + size
        output_category_path = path_to_outputs + "/" + size
        category_dir = os.fsencode(category_path)
        
        if not os.path.isdir(output_category_path):
            os.mkdir(output_category_path)

        for input_folder in os.listdir(category_dir):
            input_name = os.fsdecode(input_folder) 
            graph, num_buses, size_bus, constraints = parse_input(category_path + "/" + input_name)
            solution = solve(graph, num_buses, size_bus, constraints)
            output_file = open(output_category_path + "/" + input_name + ".out", "w")

            #TODO: modify this to write your solution to your 
            #      file properly as it might not be correct to 
            #      just write the variable solution to a file
            output_file.write(solution)

            output_file.close()

if __name__ == '__main__':
    main()


