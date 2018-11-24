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
        self.score = -1

    def solve(self):
        pass

    def write(self):
        pass

    def score(self):
        pass

    def write(self, file_name, directory="temp/"):
        """
        Writes our planted solution's .out file as specified in the
        project spec. Returns true if successful. Only writes if the solution
        has a valid score.

        :param file_name: clean filename string with no file extension.
        :param directory: directory string with slashes included.
        """
        if self.score < 0:
            if self.scorer()[0] < 0:
                return False

        with open("{}{}.out".format(directory, file_name), 'w') as f:
            for lst in self.solution:
                f.write(str(lst))
                f.write("\n")

        return True

    def scorer(self):
        """
        Formulates and returns the score of the self.solution, where the score is a number
        between 0 and 1 which represents what fraction of friendships were broken.
        """
        graph = self.graph
        num_buses = self.num_buses
        size_bus = self.size_bus
        constraints = self.constraints
        assignments = self.solution

        if len(assignments) != num_buses:
            return -1, "Must assign students to exactly {} buses, found {} buses".format(num_buses, len(assignments))

        # make sure no bus is empty or above capacity
        for i in range(len(assignments)):
            if len(assignments[i]) > size_bus:
                return -1, "Bus {} is above capacity".format(i)
            if len(assignments[i]) <= 0:
                return -1, "Bus {} is empty".format(i)

        bus_assignments = {}

        # make sure each student is in exactly one bus
        attendance = {student: False for student in graph.nodes()}
        for i in range(len(assignments)):
            if not all([student in graph for student in assignments[i]]):
                return -1, "Bus {} references a non-existant student: {}".format(i, assignments[i])

            for student in assignments[i]:
                # if a student appears more than once
                if attendance[student]:
                    print(assignments[i])
                    return -1, "{0} appears more than once in the bus assignments".format(student)

                attendance[student] = True
                bus_assignments[student] = i

        # make sure each student is accounted for
        if not all(attendance.values()):
            return -1, "Not all students have been assigned a bus"

        total_edges = graph.number_of_edges()
        # Remove nodes for rowdy groups which were not broken up
        for i in range(len(constraints)):
            buses = set()
            for student in constraints[i]:
                buses.add(bus_assignments[student])
            if len(buses) <= 1:
                for student in constraints[i]:
                    if student in graph:
                        graph.remove_node(student)

        # score output
        score = 0
        for edge in graph.edges():
            if bus_assignments[edge[0]] == bus_assignments[edge[1]]:
                score += 1
        score = score / total_edges

        return score, "Valid output submitted with score: {}".format(score)

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
                vertex1 = None




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


