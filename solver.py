import networkx as nx
import os
import numpy as np
import copy
import matplotlib.pyplot as plt
import bisect
import datetime
import sys
import json
from collections import deque
import time

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

###########################################
# Dictionary to track scores. Actually a
# dictionary of the three sized dictionaries
# which store each input_name to a score.
###########################################
score_path = f"{path_to_outputs}/scores.json"
SCORES = {}


class Solver:

    def __init__(self, graph, num_buses, bus_size, constraints, solution=None):
        self.graph = graph
        self.num_buses = num_buses
        self.bus_size = bus_size
        self.constraints = constraints
        self.solution = solution if solution else []
        self.score = -1
        self.node_to_rowdy_index_dict = {}
        for node in self.graph.nodes():
            lst = []
            for i in range(len(self.constraints)):
                if node in self.constraints[i]:
                    lst.append(i)
            self.node_to_rowdy_index_dict[node] = lst[:]

    def get_solution_vertices_by_score(self, limit=None):
        """
        :param limit: (int) only calculate the first LIMIT el of the returned list.
            Defaults to all vertices in the solution.
        :return: A continuous list of (vertex, solution_bus_num) tuples of self.solution,
            ordered increasingly by their contribution to the score. So the first el
            of the returned list contributes the least to the score and the last el
            contributes the most.
        """
        limit = limit if limit else sum(len(l) for l in self.solution)
        lst = []
        for i in range(len(self.solution)):
            bus_set = set(self.solution[i])
            for u in self.solution[i]:
                # Terminate early if possible
                if len(lst) == limit:
                    return [l[1] for l in lst]

                # Filter out vertices that form rowdy groups first
                forms_rowdy = False
                for rowdy_group_index in self.node_to_rowdy_index_dict[u]:
                    if all(map(lambda v: v in bus_set, self.constraints[rowdy_group_index])):
                        bisect.insort(lst, (-1, (u, i)))
                        forms_rowdy = True
                        break

                # If vertex doesn't form a rowdy group, consider its score contribution
                if not forms_rowdy:
                    score_contribution = 0
                    for neighbor in self.graph.neighbors(u):
                        if neighbor in bus_set:
                            score_contribution += 1
                    bisect.insort(lst, (score_contribution, (u, i)))
        return [l[1] for l in lst]

    def write(self, file_name, file_directory, verbose=False):
        """
        Writes our planted solution's .out file as specified in the
        project spec. Returns true if successful. Only writes if the solution
        has a valid score.

        :param file_name: clean filename string with no file extension.
        :param file_directory: the directory for where the file will be written to.
        :param verbose: print message or not.
        :raises: ValueError if the score is not valid, with an accompanying message.
        """
        global SCORES

        score, msg = self.official_scorer()
        file_path = f"{file_directory}/{file_name}.out"
        if score < 0:
            raise ValueError("Solution object for {}/{} has a negative score. "
                             "Scorer Message: {}".format(file_directory, file_name, msg))

        # Only write solutions that have betters scores than previous solutions.
        prev_score = SCORES.get(file_path, None)
        if prev_score is None:
            SCORES[file_path] = score
        elif SCORES[file_path] >= score:
            if verbose:
                print("[{}] Score for {} was lower (or equal), did not write. (diff = {})".format(
                    str(datetime.datetime.utcnow())[11:], file_path, SCORES[file_path] - score))
            return

        if verbose:
            print("[{}] Score for {}:  {}".format(str(datetime.datetime.utcnow())[11:],
                                                  file_path, score))
        with open(file_path, 'w', encoding='utf8') as f:
            for lst in self.solution:
                f.write(str(lst))
                f.write("\n")

        # Update jason file's scores.
        with open(score_path, 'w') as f:
            json.dump(SCORES, f)

    def official_scorer(self):
        """
        Formulates and returns the score of the self.solution, where the score is a number
        between 0 and 1 which represents what fraction of friendships were broken.

        This is what is used to score our solutions by the staff.
        Note that it is destructive to self.graph and copying isn't too efficient.

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

    def set_score(self):
        """

        TODO: Efficient scorer

        Formulates and returns the score of the self.solution, where the score is a number
        between 0 and 1 which represents what fraction of friendships were broken.

        Sets self.score

        :return: Tuple where el 0 is the score and el 1 is the accompanying msg string.
        """
        graph = self.graph.copy()
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

    def solve(self):
        pass


class Heuristic(Solver):

    def __init__(self, graph, num_buses, bus_size, constraints):
        Solver.__init__(self, graph, num_buses, bus_size, constraints)
        self.solution = [[] for _ in range(self.num_buses)]
        self.solution_set_rep = np.array([set() for _ in range(self.num_buses)])
        self.process_queue = deque()

    def set_process_queue(self, kind="LOW_DEGREE"):
        """
        Method to set the process queue of heuristic solvers.

        :param kind: (str) of how we want to order the children.
            'LOW_DEGREE' = lowest to highest degree children / nodes.
        :return: A queue (deque obj) of the order in which the
            heuristic will be processed. So the order of how the
            children get added to the solution.
        """
        kind = kind.upper()
        self.process_queue.clear()
        if kind == "LOW_DEGREE":
            for node in sorted(self.graph.degree, key=lambda x: x[1]):
                self.process_queue.append(node[0])
        elif kind == "HIGH_DEGREE":
            for node in sorted(self.graph.degree, key=lambda x: x[1], reverse=True):
                self.process_queue.append(node[0])
        return self.process_queue

    def heuristic(self, bus_num, target):
        """
        This 'heuristic' should NOT be use.
        This is only used for development reasons.

        Heuristic is number of friends (of target) in bus number: BUS_NUM

        :param target: current node being processed
        :param bus_num: the heuristic for the current buss being processed
        :return: (float) heuristic value
        """
        bus_set_rep = self.solution_set_rep[bus_num]

        if len(bus_set_rep) == self.bus_size:
            return -1

        count = 0
        for v in self.graph.neighbors(target):
            if v in bus_set_rep:
                count += 1
        return count

    def solve(self):
        """
        The main/default heuristic solver method.
        :return: self.solutions after a solution is found.
        """
        self.set_process_queue(kind='low_degree')
        # Add vertices to buses using heuristic following the process_queue's order.
        while self.process_queue:
            target = self.process_queue.popleft()  # queue popping b/c we might use prio-queue

            dest_bus_candidates = [(-1, -1)]  # tuple format for each el: (heuristic_val, bus_number)
            for bus_num in range(self.num_buses):
                heuristic = self.heuristic(bus_num, target)
                if heuristic > dest_bus_candidates[0][0]:
                    dest_bus_candidates = [(heuristic, bus_num)]
                elif heuristic == dest_bus_candidates[0][0]:
                    dest_bus_candidates.append((heuristic, bus_num))

            # TODO: Think abt this randomness. I don't like it, its too inconsistent.
            dest_bus_index = 0 if len(dest_bus_candidates) == 1 else np.random.choice(len(dest_bus_candidates))
            dest_bus = dest_bus_candidates[dest_bus_index][1]

            self.solution[dest_bus].append(target)
            self.solution_set_rep[dest_bus].add(target)

        # Takes least significant vertices and fill out empty buses
        empty_bus_list = [i for i in range(len(self.solution)) if not self.solution[i]]
        swapped_vertices = iter(self.get_solution_vertices_by_score())
        for to_bus_index in empty_bus_list:
            v, from_bus_index = next(swapped_vertices)
            while len(self.solution[from_bus_index]) == 1:
                v, from_bus_index = next(swapped_vertices)
            self.solution[from_bus_index].remove(v)
            self.solution_set_rep[from_bus_index].remove(v)
            self.solution[to_bus_index].append(v)
            self.solution_set_rep[to_bus_index].add(v)

        # TODO: some sort of greedy correction possibly using the same heuristic...
        # So, Take lowest degree vertices of oversize buses and add them to non-full buses using heuristic.
        # Keep doing until no oversize buses.
        # Maybe add a full bus check to this part's heuristic.
        #       - Maybe make full bus checking similar to a temperature check / probability thing?
        #         This allows you to hop around?

        # TODO: local search (starting at preliminary solution from above) for a satisfying solution.

        return self.solution


class DiracDeltaHeuristicBase(Heuristic):
    """ This is the basic Dirac Delta Heuristic solver.
    All other variations are based off of this.
    """

    sig = 0.1

    def __init__(self, graph, num_buses, bus_size, constraints):
        Heuristic.__init__(self, graph, num_buses, bus_size, constraints)
        self.phi_constant = 1e6

    @staticmethod
    def phi(x, rowdy_size, c=1.0):
        """
        Static Method for the Dirac Delta function (approximation).
            This is the nonlinear function: phi(.) in the design doc.
        :param x: number of people on the bus that is in the given rowdy group.
            this is the result of r(i,b,g) in the design doc.
        :param rowdy_size: Number of people in the given rowdy group.
            this is |g| in the design doc.
        :param c: multiple the result of the dirac delta by a constant to
            'inflate' the peak. When C = 1, peak is at ~1.5 (really close).
        :return: (float)
        """
        numerator = np.exp(-((x - rowdy_size) ** 2) / (2 * DiracDeltaHeuristicBase.sig))
        denominator = DiracDeltaHeuristicBase.sig * np.sqrt(2 * np.pi)
        return (numerator / denominator) * c

    def people_on_bus_count(self, bus_num, group):
        """
        Counts the number of people of GROUP that are in bus number: BUS_NUM
        :param bus_num: (int) the bus number in self.solution
            this is b in the design doc.
        :param group: (iterable) the group being counted
            this is g or i's neighbors
        :return: (int) the count.
        """
        bus_set_rep = self.solution_set_rep[bus_num]
        if bus_set_rep == set():
            return 0

        count = 0
        for v in group:
            if v in bus_set_rep:
                count += 1
        return count

    def heuristic(self, bus_num, target):
        """
        The heuristic. (overrides inherited heuristic)
            This is H(.,.) in the design doc

        NOTE: This heuristic returns -1 if bus number: BUS_NUM is full.

        :param target: current node being processed
        :param bus_num: the heuristic for the current buss being processed
        :return: (float) heuristic value
        """
        if len(self.solution[bus_num]) == self.bus_size:
            return -1

        # numerator calculation
        numerator = self.people_on_bus_count(bus_num, self.graph.neighbors(target)) + 1

        # denominator calculation
        max_val = 0
        target_rowdy_groups = (self.constraints[i] for i in self.node_to_rowdy_index_dict[target])
        for grp in target_rowdy_groups:
            r = self.people_on_bus_count(bus_num, grp)
            phi = DiracDeltaHeuristicBase.phi(r, len(grp) - 1, self.phi_constant)
            max_val = max(max_val, phi)
        denominator = max_val + 1
        return numerator / denominator


# noinspection PyMissingConstructor
class Optimizer(Solver):

    def __init__(self, graph, num_buses, bus_size, constraints, solution):
        Solver.__init__(self, graph, num_buses, bus_size, constraints, solution=solution)

    def solve(self):
        if self.num_buses == 1:
            return
        self.optimize()

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
        if vertex_2 is not None:
            self.solution[bus1] += [vertex_2]
        if vertex_1 is not None:
            self.solution[bus2] += [vertex_1]
        # Recompute the score
        new_score = self.set_score()[0]
        # return the new score if it is larger and update the solution
        if new_score >= score:
            return new_score  # We have already updated the solution by removing the vertices
        else:
            self.solution = holder_solution
            return score

    def sample_swap(self):
        # Pick two random buses and one random vertex from each bus to swap
        while True:
            bus1, bus2 = np.random.choice(list(range(self.num_buses)), 2, replace=False)

            # Make sure that we don't swap the last member out of a bus
            if len(self.solution[bus1]) > 1 and len(self.solution[bus2]) > 1:
                break

        # Sample a vertex from each bus
        open_seats1 = self.bus_size - len(self.solution[bus1])
        # Determine if we select an empty seat or not
        choose_empty_seat = np.random.binomial(1, open_seats1 / self.bus_size)

        # Choose the first student, possibly an empty seat that we swap the second student to
        if choose_empty_seat:
            student_1 = None
        else:
            student_1 = np.random.choice(self.solution[bus1])

        # Choose a second student with the requirement that we not try to swap two empty seats
        if student_1 is None:
            # student_2 cannot be none
            student_2 = np.random.choice(self.solution[bus2])
        else:
            open_seats2 = self.bus_size - len(self.solution[bus2])
            choose_empty_seat = np.random.binomial(1, open_seats2 / self.bus_size)

            student_2 = None if choose_empty_seat else np.random.choice(self.solution[bus2])

        return student_1, student_2, bus1, bus2


class BasicOptimizer(Optimizer):
    def __init__(self, graph, num_buses, bus_size, constraints, solution, sample_size=100, verbose=False):
        Optimizer.__init__(self, graph, num_buses, bus_size, constraints, solution)
        self.sample_size = sample_size
        self.verbose = verbose
        # To keep track of the score as we make optimizer steps
        # Setup instance variables
        # self.bus_mapping = None
        # self.is_invalid = None
        # Setup methods for quick access
        # self.set_bus_map()
        # self.set_invalid_vertices()

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

    # Call this method to optimize the solution we are given for a specific score
    def optimize(self, max_iterations=1000):
        # Initialize the score
        score = self.set_score()[0]
        last_iter_score = score
        # If we don't have two buses no swapping will occur
        if self.num_buses < 2:
            print("")
            return self.solution
        # Each iteration we will discover one swap to make
        for i in range(max_iterations):
            last_iter_score = score
            # If we have monte_carlo set to true we will sample the optimization space
            for sample in range(self.sample_size):
                # Sample a number of vertex combinations to try swapping
                student_1, student_2, bus1, bus2 = self.sample_swap()

                # Swap these two students
                score = self.swap(student_1, student_2, bus1, bus2, score)

            if self.verbose:
                sys.stdout.write(f"\rScore on iteration {i}: {score}")
                sys.stdout.flush()
            if score == last_iter_score:
                if self.verbose:
                    sys.stdout.write(f"\rStopped BasicOptimizer on iteration "
                                     f"{i}, with score: {score}")
                    sys.stdout.flush()
                break
        print("")


# A fancier optimizer that will look more than one step ahead
class TreeSearchOptimizer(Optimizer):

    def __init__(self, graph, num_buses, bus_size, constraints, solution, sample_size=500, max_rollout=20, verbose=False):
        Solver.__init__(self, graph, num_buses, bus_size, constraints, solution)
        self.sample_size = sample_size
        self.max_rollout = max_rollout
        self.verbose = verbose

    # Override swap because we don't want to copy or cancel out inferior solutions until rollout is complete
    def swap(self, vertex_1, vertex_2, bus1, bus2):
        # to hold the place of the old solution before swapping
        # Swap the vertices in the new solution
        # First remove the vertices from their buses
        self.remove_vertex(vertex_1, bus1)
        self.remove_vertex(vertex_2, bus2)
        # Add the vertices to the opposite bus
        if vertex_2 is not None:
            self.solution[bus1] += [vertex_2]
        if vertex_1 is not None:
            self.solution[bus2] += [vertex_1]

    def rollout(self, init_score):

        solution_holder = copy.deepcopy(self.solution)

        for step in range(self.max_rollout):
            # At each step we sample a swap
            # First sample two busses
            student_1, student_2, bus1, bus2 = self.sample_swap()

            # swap these students and get a new temporary solution
            self.swap(student_1, student_2, bus1, bus2)

        # Score this rollout
        new_score = self.set_score()[0]

        if new_score >= init_score:
            return new_score
        else:
            self.solution = solution_holder
            return init_score

    def optimize(self, max_iterations=1000):
        score = self.set_score()[0]

        # Optimize the solution
        for iteration in range(max_iterations):
            last_iter_score = score
            for sample in range(self.sample_size):
                # For every time we expand with the rollout policy we call the method rollout to sample
                score = self.rollout(score)

            if self.verbose:
                sys.stdout.write(f"\rScore on iteration {iteration}: {score}")
                sys.stdout.flush()
            if score == last_iter_score:
                if self.verbose:
                    sys.stdout.write(f"\rStopped TreeSearchOptimizer on iteration "
                                     f"{iteration}, with score: {score}")
                    sys.stdout.flush()
                break
        print("")


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


def solve(graph, num_buses, bus_size, constraints, verbose=False):
    """
    Params are obvious, they are from the skeleton code.
    :return: The solver instance.

    Note: we might have this function branch off (by calling other functions)
    depending on some future solvers that we implement.
    """
    if verbose:
        sys.stdout.write("\rSolving using DiracDeltaHeuristicBase...")
        sys.stdout.flush()
    solver = DiracDeltaHeuristicBase(graph, num_buses, bus_size, constraints)
    solver.solve()

    if verbose:
        sys.stdout.write("\rOptimizing using BasicOptimizer...")
        sys.stdout.flush()
    # optimizer = BasicOptimizer(graph, num_buses, bus_size, constraints, solver.solution, verbose=verbose)
    optimizer = TreeSearchOptimizer(graph, num_buses, bus_size, constraints, solver.solution, verbose=True)
    optimizer.solve()

    return optimizer


def main():
    """
        Main method which iterates over all inputs and calls `solve` on each.
        The student should modify `solve` to return their solution and modify
        the portion which writes it to a file to make sure their output is
        formatted correctly.
    """
    global SCORES

    size_categories = ["small", "medium", "large"]
    size_categories = ["small"]
    if not os.path.isdir(path_to_outputs):
        os.mkdir(path_to_outputs)

    # Load previous scores from file if such file exists.
    if os.path.isfile(score_path):
        print("!!~~ LOADED PREVIOUS SCORES ~~!!")
        with open(score_path, 'r+') as f:
            SCORES = json.loads(f.read())

    for size in size_categories:
        category_path = path_to_inputs + "/" + size
        output_category_path = path_to_outputs + "/" + size
        category_dir = os.fsencode(category_path)

        if not os.path.isdir(output_category_path):
            os.mkdir(output_category_path)

        for input_folder in os.listdir(category_dir):
            input_name = os.fsdecode(input_folder)
            graph, num_buses, bus_size, constraints = parse_input(category_path + "/" + input_name)
            solver_instance = solve(graph, num_buses, bus_size, constraints, True)
            solver_instance.write(input_name, output_category_path, verbose=False)


if __name__ == '__main__':
    main()
