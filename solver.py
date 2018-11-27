import networkx as nx
import os
import numpy as np
import copy

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

    def __init__(self, graph, num_buses, bus_size, constraints):
        self.graph = graph
        self.num_buses = num_buses
        self.bus_size = bus_size
        self.constraints = constraints
        self.solution = []
        self.score = -1

    def solve(self):
        pass

    def score(self):
        pass

    def write(self, file_name, directory, verbose=False):
        """
        Writes our planted solution's .out file as specified in the
        project spec. Returns true if successful. Only writes if the solution
        has a valid score.

        :param file_name: clean filename string with no file extension.
        :param directory: directory string with slashes included.
        :param verbose: print message or not.
        :raises: ValueError if the score is not valid, with an accompanying message.
        """
        score, msg = self.set_score()
        if score < 0:
            raise ValueError("Solution object for {}{} has a negative score. "
                             "Scorer Message: {}".format(directory, file_name, msg))

        # TODO: only write the file if the score of the new solution is better than the old one.

        if verbose:
            print("Score for {}{}:  {}".format(directory, file_name, score))

        with open("{}{}.out".format(directory, file_name), 'w') as f:
            for lst in self.solution:
                f.write(str(lst))
                f.write("\n")

    def set_score(self):
        """
        Formulates and returns the score of the self.solution, where the score is a number
        between 0 and 1 which represents what fraction of friendships were broken.

        Sets self.score

        :return: Tuple where el 0 is the score and el 1 is the accompanying msg string.
        """
        graph = self.graph
        num_buses = self.num_buses
        bus_size = self.bus_size
        constraints = self.constraints
        assignments = self.solution

        if len(assignments) != num_buses:
            return -1, "Must assign students to exactly {} buses, found {} buses".format(num_buses, len(assignments))

        # make sure no bus is empty or above capacity
        for i in range(len(assignments)):
            if len(assignments[i]) > bus_size:
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
        self.score = score / total_edges
        return self.score, "Valid score of: {}".format(self.score)

    def draw(self):
        pass


class SolveHeuristic(Solver):
    pass


# noinspection PyMissingConstructor
class Optimizer(Solver):

    def __init__(self, graph, num_buses, bus_size, constraints, solution, method='basic'):
        if method == 'basic':
            self.optimizer = BasicOptimizer(graph, num_buses, bus_size, constraints, solution)

    def solve(self):
        self.optimizer.optimize()


# noinspection PyMissingConstructor
class BasicOptimizer(Optimizer):

    def __init__(self, graph, num_buses, bus_size, constraints, solution, sample_size=100):
        super(self).__init__(graph, num_buses, bus_size, constraints, solution)
        self.sample_size = sample_size
        # To keep track of the score as we make optimizer steps
        self.curr_score = self.score()
        # Setup instance variables
        # self.bus_mapping = None
        #self.is_invalid = None
        # Setup methods for quick access
        #self.set_bus_map()
        #self.set_invalid_vertices()

    """
    def set_bus_map(self):
        # Sets up a mapping from vertex to bus
        mapping = {}

        for index, bus in enumerate(self.solution):
            for member in bus:
                mapping[member] = index

        self.bus_mapping = mapping

    def set_invalid_vertices(self):
        # Sets up a dictionary of vertices from vertex to truth value that tells us whether this vertex is invalid
        # This dictionary will change throughout the optimization process
        truth_dict = {}
        # Set this truth dict to an initial value

        for rowdy_group in self.constraints:
            all_in_bus = True
            bus_index = self.bus_mapping[rowdy_group[0]]

            for member in rowdy_group:
                # Check to see if they're all in the bus above
                if self.bus_mapping[member] != bus_index:
                    all_in_bus = False
                    break

            # After checking a rowdy group if our flag is not false we invalidate these edges
            if all_in_bus:
                for member in rowdy_group:
                    truth_dict[member] = True

        # Set the truth array to be an instance variable
        self.is_invalid = truth_dict
        
        self.curr_score = self.set_score()

    def count_friends_in_bus(self, vertex, bus):
        # loop through bus list and see if each element is a friend
        count = 0

        for student in self.solution[bus]:
            if len(self.graph.edges[vertex, student]) != 0:
                count += 1

        return count

    def rowdy_groups_with_vertex(self, vertex, bus):
        # Returns the COMPLETE rowdy groups in the input bus that the input vertex is part of
        # Loop through the constraint groups
        # This list will keep track of which rowdy groups are complete
        truth_list = [True] * len(self.constraints)

        for index, rowdy_group in enumerate(self.constraints):
            # First check if the vertex in question is even a part of this rowdy group
            if vertex in rowdy_group:
                # Check to see if the rest of the rowdy group is in the bus
                for member in rowdy_group:
                    if member not in self.solution[bus] and member is not vertex:
                        # This rowdy group is not complete in the bus, so we flip the truth value
                        truth_list[index] = False

        return [self.constraints[i] for i in range(len(self.constraints)) if truth_list[i]]
        """
    def remove_vertex(self, vertex, bus):
        # get the bus
        temp_list = self.solution[bus]
        left_hand_list = []
        right_hand_list = []
        seen_element = False

        for element in temp_list:
            if element == vertex:
                continue
            elif seen_element:
                right_hand_list += [element]
            else:
                left_hand_list += [element]
        self.solution[bus] = left_hand_list + right_hand_list


    def swap(self, vertex_1, vertex_2, bus1, bus2, score):
        # Swaps the two vertices and returns a tuple with the new solution and a score
        # NOTE: The new solution is only swapped if the new score is better
        # Count the number of friends lost in each bus by the swap
        # TODO: Finish implementing if calling score is too slow
        """
        original_friends_vertex_1 = self.count_friends_in_bus(vertex_1, bus1) if vertex_1 is not None else 0
        original_friends_vertex_2 = self.count_friends_in_bus(vertex_2, bus2) if vertex_2 is not None else 0
        new_friends_vertex_1 = self.count_friends_in_bus(vertex_1, bus2) if vertex_1 is not None else 0
        new_friends_vertex_2 = self.count_friends_in_bus(vertex_2, bus2) if vertex_2 is not None else 0

        new_score = self.curr_score - (original_friends_vertex_1 + original_friends_vertex_2) + (
                    new_friends_vertex_1 + new_friends_vertex_2)

        # Check differences caused by forming/breaking up rowdy groups
        original_rowdy_groups_vertex_1 = self.rowdy_groups_with_vertex(vertex_1, bus1) if vertex_1 is not None else 0
        original_rowdy_groups_vertex_2 = self.rowdy_groups_with_vertex(vertex_2, bus2) if vertex_2 is not None else 0
        new_rowdy_groups_vertex_1 = self.rowdy_groups_with_vertex(vertex_1, bus2) if vertex_1 is not None else 0
        new_rowdy_groups_vertex_2 = self.rowdy_groups_with_vertex(vertex_2, bus1) if vertex_2 is not None else 0
        """

        # to hold the place of the old solution before swapping
        holder_solution = copy.deepcopy(self.solution)

        # Swap the vertices in the new solution
        # First remove the vertices from their buses
        self.remove_vertex(vertex_1, bus1)
        self.remove_vertex(vertex_2, bus2)
        # Add the vertices to the opposite bus
        self.solution[bus1] += [vertex_2]
        self.solution[bus2] += [vertex_1]
        # Recompute the score
        new_score = self.scorer()[0]
        # return the new score if it is larger and update the solution
        if new_score >= score:
            return new_score # We have already updated the solution by removing the vertices
        else:
            self.solution = holder_solution
            return score

    # Call this method to optimize the solution we are given for a specific score
    def optimize(self, max_iterations=1000):
        score = self.scorer()

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
                open_seats1 = self.bus_size - len(self.solution[bus1])
                # Determine if we select an empty seat or not
                choose_empty_seat = np.random.binomial(1, open_seats1 / self.bus_size)

                # Choose the first student, possibly an empty seat that we swap the second student to
                if choose_empty_seat:
                    student_1 = None
                else:
                    student_1 = np.random.choice(self.solution)

                # Choose a second student with the requirement that we not try to swap two empty seats
                if student_1 is None:
                    # student_2 cannot be none
                    student_2 = np.random.choice(self.solution[bus2])
                else:
                    open_seats2 = self.bus_size - len(self.solution[bus2])
                    choose_empty_seat = np.random.binomial(1, open_seats2 / self.bus_size)

                    student_2 = None if choose_empty_seat else np.random.choice(self.solution[bus2])

                # Swap these two students

                score = self.swap(student_1, student_2, bus1, bus2, score)


def parse_input(folder_name):
    """
        Parses an input and returns the corresponding graph and parameters

        Inputs:
            folder_name - a string representing the path to the input folder

        Outputs:
            (graph, num_buses, bus_size, constraints)
            graph - the graph as a NetworkX object
            num_buses - an integer representing the number of buses you can allocate to
            bus_sizees - an integer representing the number of students that can fit on a bus
            constraints - a list where each element is a list vertices which represents a single rowdy group
    """
    graph = nx.read_gml(folder_name + "/graph.gml")
    parameters = open(folder_name + "/parameters.txt")
    num_buses = int(parameters.readline())
    bus_size = int(parameters.readline())
    constraints = []

    for line in parameters:
        line = line[1: -2]
        curr_constraint = [num.replace("'", "") for num in line.split(", ")]
        constraints.append(curr_constraint)

    return graph, num_buses, bus_size, constraints


def solve(graph, num_buses, bus_size, constraints):
    """
    Params are obvious, they are from the skeleton code.
    :return: The solver instance.

    Note: we might have this function branch off (by calling other functions)
    depending on some future solvers that we implement.
    """
    # TODO: Real solver logic.
    # Currently it is some temp test code.
    solver = Solver(graph, num_buses, bus_size, constraints)
    solver.solve()
    return solver

    pass


def main():
    """
        Main method which iterates over all inputs and calls `solve` on each.
        The student should modify `solve` to return their solution and modify
        the portion which writes it to a file to make sure their output is
        formatted correctly.
    """
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
            graph, num_buses, bus_size, constraints = parse_input(category_path + "/" + input_name)
            solver_instance = solve(graph, num_buses, bus_size, constraints)
            solver_instance.write(input_name, "{}/".format(category_path), True)


if __name__ == '__main__':
    main()
