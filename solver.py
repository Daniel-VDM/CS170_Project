import os
import copy
import bisect
import sys
import json
import time
import datetime
import math
import numpy as np
import networkx as nx
from shutil import copyfile
from collections import deque
import matplotlib.pyplot as plt

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
# Dictionary to track scores.
###########################################
score_path = f"{path_to_outputs}/scores.json"
SCORES = {}


class Solver:
    """
    Main solver object that has all of the common attributes and methods
    for using in the heuristic solver and optimizer.
    """

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

    def get_solution_vertices_by_importance(self, limit=None):
        """
        :param limit: (int) only calculate the first LIMIT el of the returned list.
            Defaults to all vertices in the solution.
        :return: A continuous list of (vertex, solution_bus_num) tuples of self.solution,
            ordered increasingly by their contribution to the score + its degree.
            So the first el of the returned list contributes the least to the score
            (after accounting for degree) and the last el contributes the most.
        """
        limit = limit if limit else len(self.graph.nodes)
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
                    bisect.insort(lst, (score_contribution + self.graph.degree[u], (u, i)))
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

        score, msg = self.set_score()
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
                print("[{}] New score for {} was <= to old score. DID NOT WRITE. (diff = {})\n".format(
                    str(datetime.datetime.utcnow())[11:], file_path, round(score - SCORES[file_path], 5)))
            return

        if verbose:
            print("[{}] New Score for {}:  {}  (diff = {})\n".format(str(datetime.datetime.utcnow())[11:],
                                                                     file_path, round(score, 5),
                                                                     round(score - SCORES[file_path], 5)))
        with open(file_path, 'w', encoding='utf8') as f:
            for lst in self.solution:
                f.write(str(lst))
                f.write("\n")

        SCORES[file_path] = score
        # Update jason file's scores.
        if os.path.isfile(score_path):
            copyfile(score_path, f"{score_path}.bak")  # Backup file
        with open(score_path, 'w') as f:
            json.dump(SCORES, f)

    def set_score(self):
        """
        Formulates and returns the score of the self.solution, where the score is a number
        between 0 and 1 which represents what fraction of friendships were broken.

        Sets self.score.

        Note that this is NON-DESTRUCTIVE to self.graph.

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
        invalid_vertices = set()
        # Check for invalid vertices formed by rowdy groups.
        for i in range(len(constraints)):
            buses = set()
            for student in constraints[i]:
                buses.add(bus_assignments[student])
            if len(buses) <= 1:
                for student in constraints[i]:
                    if student in graph:
                        invalid_vertices.add(student)  # NOTE: change from given scorer is here.

        # score output
        score = 0
        for edge in graph.edges():
            u, v = edge
            if u not in invalid_vertices and v not in invalid_vertices \
                    and bus_assignments[edge[0]] == bus_assignments[edge[1]]:
                score += 1
        self.score = score / total_edges
        return self.score, "Valid score of: {}".format(self.score)

    def draw(self):
        pass

    def solve(self):
        pass


####################
# Heuristic Solver #
####################


class HeuristicPriorityQueue:
    """
    Special (inefficient) 'priority queue' for the heuristic solver. Queue is used for
    processing the order in which students are added to buses.

    Its a queue to fit the class code/structure, but really this is more like a
    generator.
    """

    def __init__(self, solver, iterable=None, ranked="potential_friends"):
        self.solver = solver
        self.rank = ranked.upper()
        self.set = set(iterable) if iterable else set()
        self.nxt = None
        self._rank()

    def __repr__(self):
        return f"<HeuristicQueue> set: {self.set}"

    def __bool__(self):
        return bool(len(self.set) > 0 or self.nxt)

    def clear(self):
        self.set.clear()

    def append(self, x):
        self.appendleft(x)

    def appendleft(self, x):
        self.set.add(x)

    def remove(self, x):
        self.set.remove(x)

    def _rank(self):
        """ Private method to rank elements in the 'queue'

        POTENTIAL_FRIENDS:
            Ranks them from least to greatest according to the number of
            friends (edge) each student could possibly add to the score
            in 1 time step (disregarding rowdy groups for simplicity).
        """
        if self.rank == "POTENTIAL_FRIENDS":
            min_el = (math.inf, None)
            for u in self.set:
                u_friends = set(self.solver.graph.neighbors(u))
                weight = 0
                for bus in self.solver.solution:
                    friend_count = 0
                    for v in bus:
                        if v in u_friends:
                            friend_count += 1
                    weight = max(weight, friend_count)
                if weight < min_el[0]:
                    min_el = (weight, u)
            self.set.remove(min_el[1])
            self.nxt = min_el[1]
        else:
            raise ValueError(f"{self.rank} is unsupported rank scheme for {self}")

    def pop(self):
        to_be_returned = self.nxt
        if self.set:
            self._rank()
        else:
            self.nxt = None
        return to_be_returned

    def popleft(self):
        to_be_returned = self.nxt
        if self.set:
            self._rank()
        else:
            self.nxt = None
        return to_be_returned


class Heuristic(Solver):
    """
    Main heuristic solver class that contains all of the shared methods.
    """

    supported_process_order = [
        "LOW_DEGREE",
        "HIGH_DEGREE",
        "PRIO_QUEUE"
    ]

    def __init__(self, graph, num_buses, bus_size, constraints):
        Solver.__init__(self, graph, num_buses, bus_size, constraints)
        self.solution = [[] for _ in range(self.num_buses)]
        self.solution_set_rep = np.array([set() for _ in range(self.num_buses)])
        self.process_queue = deque()

    def set_process_queue(self, kind="LOW_DEGREE"):
        """
        Method to set the process set of heuristic solvers.

        :param kind: (str) of how we want to order the children.
            'LOW_DEGREE' = lowest to highest degree children / nodes.
        :return: A set (deque obj) of the order in which the
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
        elif kind == "PRIO_QUEUE":
            self.process_queue = HeuristicPriorityQueue(self, self.graph.nodes)
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

    # noinspection PyMethodMayBeStatic
    def heuristic_tie_breaker(self, target, candidates):
        """
        :param target: the person being processed.
        :param candidates: list of buses (ints) that have the same heuristic value.
        :return: a single random candidate.
        """
        return np.random.choice(candidates)

    def process_heuristic(self, target, possible_buses):
        """ Run the heuristic for TARGET on each POSSIBLE_BUSES and
        return the bus (in POSSIBLE_BUSES) that has the highest heuristic value.

        :param target: student being processes
        :param possible_buses: all buses to consider.
        :return: bus with the highest heuristic value.
        """
        candidate_buses = []
        highest_heuristic = -1
        for bus_num in possible_buses:
            heuristic = self.heuristic(bus_num, target)
            if heuristic > highest_heuristic:
                candidate_buses = [bus_num]
                highest_heuristic = heuristic
            elif heuristic == highest_heuristic:
                candidate_buses.append(bus_num)

        if len(candidate_buses) == 1:
            return candidate_buses[0]
        return self.heuristic_tie_breaker(target, candidate_buses)

    def move_student(self, v, from_bus_index, to_bus_index):
        """
        Move a student from one bus to another in self.solution

        :param v: student (vertex) being moves
        :param from_bus_index: remove from this bus (this is an index)
        :param to_bus_index: add to this bus (this is an index)
        """
        self.solution[from_bus_index].remove(v)
        self.solution_set_rep[from_bus_index].remove(v)
        self.solution[to_bus_index].append(v)
        self.solution_set_rep[to_bus_index].add(v)

    def check_and_correct_nonempty_buses(self):
        """
        Checks self.solution to make sure that all buses are non-empty.

        Greedily corrects (by vertex importance) self.solution if there are
        non-empty buses.

        :return: self.solution
        """
        empty_bus_list = [i for i in range(len(self.solution)) if not self.solution[i]]
        if not empty_bus_list:
            return self.solution

        swap_candidates = iter(self.get_solution_vertices_by_importance())
        for to_bus_index in empty_bus_list:
            v, from_bus_index = next(swap_candidates)
            while len(self.solution[from_bus_index]) == 1:
                try:  # Hacky but it works :D
                    v, from_bus_index = next(swap_candidates)
                except StopIteration:
                    swap_candidates = iter(self.get_solution_vertices_by_importance())
            self.move_student(v, from_bus_index, to_bus_index)

        return self.solution

    def solve(self, process_order=None):
        """
        The main/default heuristic solver method.

        :param process_order: The order in which the students gets added to buses.
        :return: self.solutions after a solution is found.
        """
        process_order = process_order if process_order else 'low_degree'
        self.set_process_queue(kind=process_order)

        # Add vertices to buses using heuristic following the process_queue's order.
        while self.process_queue:
            target = self.process_queue.popleft()

            dest_bus = self.process_heuristic(target, range(self.num_buses))

            self.solution[dest_bus].append(target)
            self.solution_set_rep[dest_bus].add(target)

        return self.check_and_correct_nonempty_buses()


class DiracDeltaHeuristicBase(Heuristic):
    """
    This is the basic Dirac Delta Heuristic solver.
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


class DDHeuristicTieBreakers(DiracDeltaHeuristicBase):
    """
    Same as DiracDeltaHeuristicBase, but has  deterministic tiebreakers
    instead of a random one.
    Note that we can still use the default random tie breaker if needed.
    """
    supported_tie_breaks = [
        "LEAST_FULL",
        "MOST_FULL",
        "MOST_FRIENDS",
        "HEURISTIC",
        "DEFAULT"
    ]

    def __init__(self, graph, num_buses, bus_size, constraints, tie_break="MOST_FRIENDS"):
        DiracDeltaHeuristicBase.__init__(self, graph, num_buses, bus_size, constraints)
        self.tie_break = tie_break.upper()

    def breaker_heuristic(self, bus_num, target):
        """
        Heuristic for the deterministic heuristic_tie_breaker of the solve method.

        Logic: N = friends of TARGET in bus number: BUS_NUM.
               D = Sum r_i; Let i = Constraint group index of TARGET
                            Have r_i = 1 if any member of constraint group
                            i is in the bus. r_i = 0 otherwise.
               Heuristic is then (N+1)/(D+1) (+1 for 0s error).

        :param bus_num: the bus number considered.
        :param target: the person being processed.
        :return: Heuristic value described above.
        """
        bus_members = set(self.solution[bus_num])
        numerator = self.people_on_bus_count(bus_num, self.graph.neighbors(target))

        rowdy_group_indices = self.node_to_rowdy_index_dict[target]
        denominator = 0
        for i in rowdy_group_indices:
            for v in self.constraints[i]:
                if v in bus_members:
                    denominator += 1
                    break

        return (numerator + 1) / (denominator + 1)

    def heuristic_tie_breaker(self, target, candidates, tie_break=None):
        """
        :param target: the person being processed.
        :param candidates: list of buses (ints) that have the same heuristic value.
        :param tie_break: tye_break type.
        :return: a single candidate.
        """
        tie_break = tie_break if tie_break else self.tie_break

        if tie_break == "LEAST_FULL":
            return min(candidates, key=lambda i: len(self.solution[i]))
        elif tie_break == "MOST_FULL":
            return max(candidates, key=lambda i: len(self.solution[i]))
        elif tie_break == "MOST_FRIENDS":
            target_friends = self.graph.neighbors(target)
            return max(candidates, key=lambda i: self.people_on_bus_count(i, target_friends))
        elif tie_break == "HEURISTIC":
            lst = []
            highest_heuristic = -1
            for bus_num in candidates:
                heuristic = self.breaker_heuristic(bus_num, target)
                if heuristic > highest_heuristic:
                    lst = [bus_num]
                    highest_heuristic = heuristic
                elif heuristic == highest_heuristic:
                    lst.append(bus_num)
            if len(lst) > 1:
                return self.heuristic_tie_breaker(target, lst, tie_break="LEAST_FULL")
            return lst[0]
        elif tie_break == "DEFAULT":
            return Heuristic.heuristic_tie_breaker(self, target, candidates)
        else:
            raise ValueError(f"{tie_break} is an invalid tie breaker.")


class DDHeuristicOversizeCorrection(DDHeuristicTieBreakers):
    """
    This solver allows buses to go over capacity initially, then it
    greedily corrects this using this classes heuristic.
    """

    def heuristic(self, bus_num, target):
        """
        The heuristic. (overrides inherited heuristic)
            This is H(.,.) in the design doc

        :param target: current node being processed
        :param bus_num: the heuristic for the current buss being processed
        :return: (float) heuristic value
        """
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

    def solve(self, process_order=None):
        """
        Slightly different solver for greedy bus oversize correction.

        :param process_order: The order in which the students gets added to buses.
        :return: self.solutions after a solution is found.
        """
        process_order = process_order if process_order else 'low_degree'
        self.set_process_queue(kind=process_order)

        # Add vertices to buses using heuristic following the process_queue's order.
        while self.process_queue:
            target = self.process_queue.popleft()

            dest_bus = self.process_heuristic(target, range(self.num_buses))

            self.solution[dest_bus].append(target)
            self.solution_set_rep[dest_bus].add(target)

        # Greedily correct for over-capacity buses using the class's heuristic. (Makes it slower)
        over_cap_buses = set(i for i in range(self.num_buses) if len(self.solution[i]) > self.bus_size)
        if over_cap_buses:
            invalid_buses = (i for i in range(self.num_buses) if len(self.solution[i]) >= self.bus_size)
            free_buses = set(range(self.num_buses)) - set(invalid_buses)
            to_be_removed = []
            for bus_num in over_cap_buses:
                invalid_students_count = len(self.solution[bus_num]) - self.bus_size
                invalid_students = sorted(self.solution[bus_num],
                                          key=lambda u: self.people_on_bus_count(bus_num, self.graph.neighbors(u)),
                                          reverse=True)[:invalid_students_count]
                to_be_removed.extend((u, bus_num) for u in invalid_students)
            for u, bus_num in to_be_removed:
                dest_bus = self.process_heuristic(u, free_buses)
                self.move_student(u, bus_num, dest_bus)
                if len(self.solution[dest_bus]) >= self.bus_size:
                    free_buses.remove(dest_bus)

        return self.check_and_correct_nonempty_buses()


#############
# Optimizer #
#############


class Optimizer(Solver):

    def __init__(self, graph, num_buses, bus_size, constraints, solution):
        Solver.__init__(self, graph, num_buses, bus_size, constraints, solution=solution)

    def solve(self):
        if not hasattr(self, "verbose") or not hasattr(self, 'optimize'):
            raise AttributeError(f"{self} obj doesn't have necessary instance attributes.")
        if self.num_buses == 1:
            if self.verbose:
                sys.stdout.write(f"\r\tDid NOT optimize {' ' * 30}")
                sys.stdout.flush()
                print("")
            return
        self.optimize()
        return self.solution

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
        counter = 0

        viable_buses = [i for i in range(self.num_buses) if len(self.solution[i]) > 1]
        if len(viable_buses) < 2:
            return None, None, None, None

        bus1, bus2 = np.random.choice(viable_buses, 2, replace=False)

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
    def __init__(self, graph, num_buses, bus_size, constraints, solution, sample_size=100, verbose=False, early_termination=True):
        Optimizer.__init__(self, graph, num_buses, bus_size, constraints, solution)
        self.sample_size = sample_size
        self.verbose = verbose
        self.early_termination = early_termination

    # Call this method to optimize the solution we are given for a specific score
    def optimize(self, max_iterations=1000):
        # Initialize the score
        score = self.set_score()[0]
        last_iter_score = score
        # If we don't have two buses no swapping will occur
        if self.num_buses < 2:
            sys.stdout.write(f"\r\tStopped BasicOptimizer on iteration {i} {' '*20}")
            sys.stdout.flush()
            print("")
            return
        # Each iteration we will discover one swap to make
        for i in range(max_iterations):
            last_iter_score = score
            # If we have monte_carlo set to true we will sample the optimization space
            for sample in range(self.sample_size):
                # Sample a number of vertex combinations to try swapping
                student_1, student_2, bus1, bus2 = self.sample_swap()
                if student_1 is None and student_2 is None and bus1 is None and bus2 is None:
                    break
                # Swap these two students
                score = self.swap(student_1, student_2, bus1, bus2, score)

            if self.verbose:
                sys.stdout.write(f"\r\tScore on iteration {i} of BasicOptimizer: "
                                 f"{round(score,5)} {' '*30}")
                sys.stdout.flush()
            if score == last_iter_score and self.early_termination:
                if self.verbose:
                    sys.stdout.write(f"\r\tStopped BasicOptimizer on iteration {i} {' '*30}")
                    sys.stdout.flush()
                break
        if self.verbose:
            print("")


# A fancier optimizer that will look more than one step ahead
class TreeSearchOptimizer(Optimizer):

    def __init__(self, graph, num_buses, bus_size, constraints, solution, sample_size=100, max_rollout=5,
                 verbose=False, early_termination=True):
        Solver.__init__(self, graph, num_buses, bus_size, constraints, solution)
        self.sample_size = sample_size
        self.max_rollout = max_rollout
        self.verbose = verbose
        self.early_termination = early_termination

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

            if student_1 is None and student_2 is None and bus1 is None and bus2 is None:
                break
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
                sys.stdout.write(f"\r\tScore on iteration {iteration} of TreeSearchOptimizer: "
                                 f"{round(score,5)} {' '*30}")
                sys.stdout.flush()
            if score == last_iter_score and self.early_termination:
                if self.verbose:
                    sys.stdout.write(f"\r\tStopped TreeSearchOptimizer on iteration {iteration} {' '*30}")
                    sys.stdout.flush()
                break
        if self.verbose:
            print("")


############################
# Main Execution Functions #
############################


def parse_input(folder_name):
    """
        Parses an input and returns the corresponding graph and parameters

        Inputs:
            folder_name - a string representing the path to the input folder

        Outputs:
            (graph, num_buses, bus_size, constraints)
            graph - the graph as a NetworkX object
            num_buses - an integer representing the number of buses you can allocate to
            bus_sizes - an integer representing the number of students that can fit on a bus
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


TIE_BREAK_BREAKS = [
    "LEAST_FULL",
    "HEURISTIC",
    "MOST_FULL",
    "DEFAULT"
]

TIE_BREAK_PROCESS = [
    "PRIO_QUEUE",
    "HIGH_DEGREE",
    "LOW_DEGREE",
]

OVER_CORR_BREAKS = [
    "LEAST_FULL",
    "HEURISTIC"
]

OVER_CORR_PROCESS = [
    "PRIO_QUEUE",
]


def solve(graph, num_buses, bus_size, constraints, verbose=False):
    """
    Params are obvious, they are from the skeleton code.
    :return: The solver instance.

    Note: we might have this function branch off (by calling other functions)
    depending on some future solvers that we implement.
    """
    all_heuristics = []
    for tie_break in TIE_BREAK_BREAKS:
        for process_order in TIE_BREAK_PROCESS:
            if verbose:
                sys.stdout.write(f"\r\tSolving using DDHeuristicTieBreakers... "
                                 f"({tie_break}) ({process_order}) {' '* 10}")
                sys.stdout.flush()
            solver = DDHeuristicTieBreakers(graph, num_buses, bus_size, constraints, tie_break)
            solver.solve(process_order)
            all_heuristics.append((solver.set_score()[0], solver.solution))

    for tie_break in OVER_CORR_BREAKS:
        for process_order in OVER_CORR_PROCESS:
            if verbose:
                sys.stdout.write(f"\r\tSolving using DDHeuristicOversizeCorrection... "
                                 f"({tie_break}) ({process_order}) {' '* 10}")
                sys.stdout.flush()
            solver = DDHeuristicOversizeCorrection(graph, num_buses, bus_size, constraints, tie_break)
            solver.solve(process_order)
            all_heuristics.append((solver.set_score()[0], solver.solution))

    heuristic_sol = max(all_heuristics, key=lambda tup: tup[0])[1]

    if verbose:
        sys.stdout.write(f"\r\tOptimizing... {' '*100}")
        sys.stdout.flush()
    solver = TreeSearchOptimizer(graph, num_buses, bus_size, constraints, heuristic_sol,
                                 sample_size=300, max_rollout=max(20, num_buses), verbose=verbose)
    solver.solve()
    solver = BasicOptimizer(graph, num_buses, bus_size, constraints, solver.solution,
                            sample_size=300, verbose=verbose)
    solver.solve()

    return solver

def optimize_ours(graph, num_buses, bus_size, constraints, solution, sample_size, max_rollout, verbose=False):
    # Optimizes our own solutions
    solver = TreeSearchOptimizer(graph, num_buses, bus_size, constraints, solution, sample_size=sample_size, max_rollout=max_rollout, verbose=False, early_termination=False)
    solver.solve()
    return solver

def main():
    """
        Main method which iterates over all inputs and calls `solve` on each.
        The student should modify `solve` to return their solution and modify
        the portion which writes it to a file to make sure their output is
        formatted correctly.
    """
    global SCORES

    size_categories = ["small", "medium", "large"]
    if not os.path.isdir(path_to_outputs):
        os.mkdir(path_to_outputs)

    # Load previous scores from file if such file exists.
    if os.path.isfile(score_path):
        with open(score_path, 'r+') as f:
            lines = f.read()
            if lines:
                print("!!~~ LOADED PREVIOUS SCORES ~~!!\n")
                SCORES = json.loads(lines)

    t_start = time.time()
    for size in size_categories:
        category_path = path_to_inputs + "/" + size
        output_category_path = path_to_outputs + "/" + size
        category_dir = os.fsencode(category_path)

        if not os.path.isdir(output_category_path):
            os.mkdir(output_category_path)

        for input_folder in os.listdir(category_dir):
            input_name = os.fsdecode(input_folder)
            graph, num_buses, bus_size, constraints = parse_input(category_path + "/" + input_name)
            solver_instance = solve(graph, num_buses, bus_size, constraints, verbose=True)
            solver_instance.write(input_name, output_category_path, verbose=True)

    time_elapsed = datetime.timedelta(seconds=(time.time() - t_start))
    print(f"Time Elapsed: {time_elapsed} hrs")
    all_scores = list(SCORES.values())
    print(f"Average Score (on leaderboard): {sum(all_scores)/len(all_scores)}")


if __name__ == '__main__':
    for _ in range(1):
        main()
