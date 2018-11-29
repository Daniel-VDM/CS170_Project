import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from optparse import OptionParser
import math
import random
import itertools
import os
import output_scorer
from math import ceil


class InputGenerator:

    def __init__(self, kids_count, bus_count, constraint_size):
        """
        Params are passed in from the options parser in main.
        """
        self.super_friend_count = bus_count
        self.kids_count = kids_count  # - self.super_friend_count - 1  # -1 for the Loner.
        self.bus_count = bus_count
        self.constraint_limit = constraint_size
        self.bus_size = kids_count  # TBD, this should change during file generation.
        self.super_set = set()
        self.rowdy_groups = []
        self.solution = []
        self.G = nx.Graph()
        self.G.add_nodes_from((str(i) for i in range(kids_count)))
        self.trouble_makers = []
        self.decoy = []
        self.G = self.G.to_undirected()  # Probably not needed

    def generate_solution(self):
        """
        Generates a planted solution by evenly (but randomly) distributing
        the kids among all the buses. Then it makes the buses uneven by
        randomly swapping kids around KIDS_COUNT//BUS_COUNT number of times.
        """
        lst = list(self.G.nodes)
        random.shuffle(lst)
        sol = [list(l) for l in np.array_split(lst, self.bus_count)]
        for _ in range(self.kids_count // self.bus_count):  # More loops = More uneven group sizes.
            move_from = sol[random.randint(0, len(sol) - 1)]
            move_to = sol[random.randint(0, len(sol) - 1)]
            if len(move_from) > 3:  # This is an arbitrary min size check that can be changed.
                move_to.append(move_from.pop())
        self.solution = sol

    def generate_super_set(self):
        """
        Separate super set creator on its own so that we can change
        this in the future.
        """
        # Loop through busses and choose a member that we will add to superset
        for bus in self.solution:
            # generate a random index that we will add to the super_set
            bus_population = len(bus)
            random_index = np.random.randint(0, bus_population)
            # add this randomly selected person to the superset
            self.super_set.add(bus[random_index])

    def generate_constraints(self):
        """
        Generates the constraints for the input. Depends on planted solution.
        """

        # helper method I defined here for correct scoping
        def random_choose_2_combinations(lst):
            """
            Returns list of choose 2 combinations but shuffled to avoid bias towards
            earlier busses in the case that we have to remove rowdy groups
            """
            combinations = list(itertools.combinations(lst, 2))
            np.random.shuffle(combinations)
            return combinations

        for tup in random_choose_2_combinations(list(self.super_set)):
            if len(self.rowdy_groups) < self.constraint_limit:
                # make sure we don't go over the number of constraints we have allocated
                self.rowdy_groups.append(list(tup))
            else:
                # if we do reach maximum number of constraints, terminate the function here
                return

        # first priority to add more constraints is to make busses almost complete rowdy groups
        # these two numbers form the interval on percentage of bus to make a rowdy group
        low, high = 0.85, 0.96  # set to 0.96 because numpy uniform produces values [low, high)
        for bus in self.solution:
            # once again, make sure we don't go over in constraint count
            if len(self.rowdy_groups) > self.constraint_limit:
                return
            # we randomly sample a group of 85-95% of the bus to make a rowdy group
            # randomly choose a percentage of the bus to sample (uniform over interval)
            percentage_of_bus = np.random.uniform(low, high)
            number_sampled = ceil(percentage_of_bus * len(bus))  # number of people we pull into rowdy group rounded up

            if number_sampled == len(bus):
                # make sure we don't create a rowdy group that contains the whole bus
                number_sampled -= 1

            rowdy_group = list(np.random.choice(bus, size=number_sampled, replace=False))
            # we now have to add a member or two from another bus so that we have rowdy groups all together
            # first, sample a random bus, we have to sample the index because numpy can't sample 2-D lists
            # we need the while loop to make sure we don't sample the bus we are currently on
            flag = True
            while flag:
                bus_index = np.random.randint(0, len(self.solution))
                random_bus = self.solution[bus_index]
                if random_bus != bus:
                    flag = False

            # sample a student from this bus
            students = list(np.random.choice(random_bus, size=np.random.choice([1, 2]), replace=False))
            # add this student to the rowdy group
            rowdy_group += students
            # add the new rowdy group
            self.rowdy_groups.append(rowdy_group)

    def _assign_edges(self, U, V, prob):
        """
        Private method to assign edges.

        :param U: A list(-ish) of nodes where element i is u_i in (u_i,v_i)
        :param V: A list(-ish) of nodes where element i is v_i in (u_i,v_i)
        :param prob: the probability of edge (u_i,v_i) being assigned.
        """
        for u, v in zip(U, V):
            if u == v:  # No self loops
                continue
            if np.random.uniform(0, 1) <= prob:
                self.G.add_edge(u, v)

    def _create_super_set_common_friends(self, percentage):
        """
        Private method that (randomly) creates the common friends group
        for the super set. And add the edges to self.G

        :param percentage: a float between 0 and 1. It is the percentage of
            people in a bus that are friends with everyone in the super set
        :return: List of lists that contain people that are friends with
            everyone in the super set.
            The list in indexed as follows:
                Element i is a list of people in the super set common
                friends group for bus i in self.solution.
        """
        lst = []
        for bus in self.solution:
            ppl = set(bus) - self.super_set
            num_of_ppl = max(1, math.ceil(len(ppl) * percentage))
            common_friends = random.sample(ppl, num_of_ppl)
            for u in common_friends:
                for v in self.super_set:
                    self.G.add_edge(u, v)
            lst.append(common_friends)
        return lst

    def _assign_bus_budgets(self, common_friends):
        """
        Private method to assign budgets for each bus.
            Each bus has 4 budgets. In order its:
                1) Number of edges to the super vertex of the bus.
                2) Number of edges to all other super vertices.
                3) Number of edges between vertices within the bus.
                4) Number of edges to all other edges not in the bus
                    and not in the super set.

        :param common_friends: The set of common friends for the super set
        :return: A list of lists of budgets. Element i is the budget list
            for bus i in self.solutions. The 4 elements of each budget list
            is documented above.
        """
        bus_edge_budgets = []
        for i in range(self.bus_count):
            bus = set(self.solution[i])

            # Tune these numbers/sets as needed.
            bus_solo_vertices = (bus - self.super_set) - set(common_friends[i])
            a = (3 * len(bus_solo_vertices)) // 4
            b = len(bus_solo_vertices)
            to_bus_super_vertex = max(2, random.randint(a, b))

            other_super_vertices = self.super_set - (self.super_set & bus)
            a = len(other_super_vertices) // 2
            b = len(other_super_vertices)
            to_other_super_vertex = max(1, random.randint(a, b))

            bus_non_super_vertices = bus - self.super_set
            a = len(bus_non_super_vertices) // 2
            b = len(bus_non_super_vertices)
            to_inside_bus = max(2, random.randint(a, b))

            all_other_vertices = (set(self.G.nodes) - self.super_set) - bus
            a = len(all_other_vertices) // 4
            b = len(all_other_vertices) // 2
            to_spread = max(3, random.randint(a, b))

            lst = [to_bus_super_vertex, to_other_super_vertex, to_inside_bus, to_spread]
            bus_edge_budgets.append(lst)
        return bus_edge_budgets

    def generate_friends(self):
        """
        Main method for generating friend edges.
        Depends on planted solution and super set.

        Currently Implemented:
            - Made the vertices in the super set a clique.
            - Created super set common friends.
        """
        for tup in itertools.combinations(list(self.super_set), 2):
            self.G.add_edge(tup[0], tup[1])
        super_set_common_friend_lst = self._create_super_set_common_friends(percentage=0.05)

        bus_edge_budgets = self._assign_bus_budgets(super_set_common_friend_lst)
        # Assign edges for each bus using the budgets
        for i in range(self.bus_count):
            budget_lst = bus_edge_budgets[i]
            bus_vertices = set(self.solution[i])

            # bus_super_vertices as is just in case we decide to change how the super_set is created.
            bus_super_vertices = list(bus_vertices & self.super_set)
            if not bus_super_vertices:
                continue

            # Edges to bus super vertex
            U = random.sample(bus_vertices - self.super_set, budget_lst[0])
            V = [random.choice(bus_super_vertices) for _ in range(budget_lst[0])]
            self._assign_edges(U, V, prob=0.7)

            # Edge to other super vertices:
            U = random.sample(self.super_set - set(bus_super_vertices), budget_lst[1])
            V = np.random.choice(list(bus_vertices), size=budget_lst[1], replace=True)
            self._assign_edges(U, V, prob=0.3)

            # Internal bus edges
            U = []
            V = []
            pool = list(bus_vertices - set(bus_super_vertices))
            for _ in range(budget_lst[2]):
                u = random.choice(pool)
                U.append(u)
                v = random.choice(pool)
                while v == u:
                    v = random.choice(pool)
                V.append(v)
            self._assign_edges(U, V, prob=0.7)

            # Spread edges
            U = np.random.choice(list(bus_vertices - self.super_set), size=budget_lst[3], replace=True)
            V = random.sample((set(self.G.nodes) - self.super_set) - bus_vertices, budget_lst[3])
            self._assign_edges(U, V, prob=0.6)

    def constrain_score_increasing_swaps(self, verbose=True):
        """
        Constrain the high degree vertices of each bus who's swap
        lead to an immediate score increase.

        Takes a while to compute.
        - Maybe over constraining?

        Aim is to stop branching algorithms before they get
        to the planted solution.
        """

        def swap(lst1, lst2, a, b):
            """
            Helper to mutate lst args via swapping a and b.
            Swap a from lst1 with b from lst2.
            """
            lst1.append(b)
            lst2.append(a)
            lst1.remove(a)
            lst2.remove(b)

        buses_done = 0
        if verbose:
            print("This might take a while...\nConstraining score increasing swaps...")
        for bus in self.solution:
            if set(bus) & self.super_set == set():
                continue
            super_vertex = random.choice(list(set(bus) & self.super_set))
            lst = [n for n in bus if n not in self.super_set]
            hi_deg_vertex = max(self.G.degree(lst), key=lambda x: x[1])[0]
            current_score = self.score_graph()

            # Find increasing swaps with current bus
            increasing_swaps = []
            for other_bus in self.solution:
                if hi_deg_vertex in other_bus:
                    continue
                lst = [n for n in other_bus if n not in self.super_set]
                other_hi_deg_vertex = max(self.G.degree(lst), key=lambda x: x[1])[0]
                swap(bus, other_bus, hi_deg_vertex, other_hi_deg_vertex)
                score = self.score_graph()
                swap(bus, other_bus, other_hi_deg_vertex, hi_deg_vertex)
                if current_score > score:
                    increasing_swaps.append(other_hi_deg_vertex)
                if len(increasing_swaps) > 10:
                    break

            # Constrain increasing swaps
            for v in increasing_swaps:
                if len(self.rowdy_groups) >= self.constraint_limit:
                    return
                self.rowdy_groups.append([v, super_vertex])

            buses_done += 1
            if verbose:
                print("Finished {}/{} buses...".format(buses_done, len(self.solution)))

    def generate_trouble_makers(self, count):
        """
        Trouble makes who create rowdy groups with all of their friends.
        All of their friends = all vertices in super set + some random people.
        """
        for _ in range(count):
            while True:
                pull_from = random.choice(self.solution)
                if len(pull_from) > 1:
                    break
            vertex = random.choice(list(set(pull_from) - self.super_set))

            # Create solo bus
            pull_from.remove(vertex)
            self.G.remove_node(vertex)
            self.G.add_node(vertex)
            self.solution.append([vertex])
            self.bus_count += 1
            self.trouble_makers.append(vertex)

            # Make vertex a trouble maker with super set vertices
            for u in self.super_set:
                self.G.add_edge(u, vertex)
                self.rowdy_groups.append([u, vertex])

            # Make it a trouble maker with high degree vertices
            lst = sorted(self.G.degree(list(set(self.G.nodes) - self.super_set)),
                         key=lambda x: x[1], reverse=True)
            for u in lst[:random.randint(0, self.bus_count // 2)]:
                self.G.add_edge(u[0], vertex)
                self.rowdy_groups.append([u[0], vertex])

    def generate_decoy(self):
        """
        Generates decoy vertices that have the same degree as vertices in
        the super set to obscure structure.
        """
        num_of_decoys = len(self.trouble_makers) + random.randint(0, len(self.super_set) // 2)
        vertices = [v[0] for v in sorted(self.G.degree(list(set(self.G.nodes) - self.super_set)),
                                         key=lambda x: x[1], reverse=True)][:num_of_decoys]
        target_degree = sorted(self.G.degree, key=lambda x: x[1], reverse=True)[3][1]
        try:
            for v in vertices:
                U = random.sample((set(self.G.nodes) - self.super_set) - set(v), target_degree - self.G.degree(v))
                V = [v for _ in range(len(U))]
                self._assign_edges(U, V, prob=1)
                for t in self.trouble_makers:
                    self.rowdy_groups.append([v, t])
            self.decoy = vertices
        except:  # Don't hate me.
            self.generate_decoy()
    def generate_loner(self):
        """
        Trouble makes who create rowdy groups with all of their friends.
        All of their friends = all vertices in super set + some random people.
        """
        for _ in range(count):
            while True:
                pull_from = random.choice(self.solution)
                if len(pull_from) > 1:
                    break

            self.G.add_node()
            self.solution.append([vertex])
            self.bus_count += 1
            self.trouble_makers.append(vertex)

    def generate_trouble_makers(self, count):
        """
        Trouble makes who create rowdy groups with all of their friends.
        All of their friends = all vertices in super set + some random people.
        """
        for _ in range(count):
            while True:
                pull_from = random.choice(self.solution)
                if len(pull_from) > 1:
                    break
            vertex = random.choice(list(set(pull_from) - self.super_set))

            # Create solo bus
            pull_from.remove(vertex)
            self.G.remove_node(vertex)
            self.G.add_node(vertex)
            self.solution.append([vertex])
            self.bus_count += 1
            self.trouble_makers.append(vertex)

            # Make vertex a trouble maker with super set vertices
            for u in self.super_set:
                self.G.add_edge(u, vertex)
                self.rowdy_groups.append([u, vertex])

            # Make it a trouble maker with high degree vertices
            lst = sorted(self.G.degree(list(set(self.G.nodes) - self.super_set)),
                         key=lambda x: x[1], reverse=True)
            for u in lst[:random.randint(0, self.bus_count // 2)]:
                self.G.add_edge(u[0], vertex)
                self.rowdy_groups.append([u[0], vertex])

    def set_bus_size(self):
        """
        Sets the size of the bus to be the size of the biggest
        bus in the planted solution.
        """
        self.bus_size = max([len(l) for l in self.solution])

    def generate(self):
        """
        Method to simply generate the file.

        Order of generation can be changed if desired.
        """
        self.generate_solution()
        self.generate_super_set()
        self.generate_constraints()
        self.generate_friends()
        self.generate_trouble_makers(random.randint(1, 3))
        self.generate_decoy()
        # self.constrain_score_increasing_swaps()  # Might not use this.
        self.set_bus_size()

    def write_solution(self, file_name, directory="temp/"):
        """
        Writes our planted solution's .out file as specified in the
        project spec.

        :param file_name: clean filename string with no file extension.
        :param directory: directory string with slashes included.
        """
        with open("{}{}.out".format(directory, file_name), 'w') as f:
            for lst in self.solution:
                f.write(str(lst))
                f.write("\n")

    def write_input(self, graph_file_name, param_file_name, directory="temp/"):
        """
        Writes the graph's (G) .gml file and parameters .txt file as
        specified in the project spec.

        :param graph_file_name: clean file name string with no file extension.
        :param param_file_name: "  "  "  "
        :param directory: directory string with slashes included.
        """
        if len(self.rowdy_groups) > self.constraint_limit:
            raise ValueError("Rowdy group size ({}) > constraint max count: {}".format(
                len(self.rowdy_groups), self.constraint_limit))
        nx.write_gml(self.G, "{}{}.gml".format(directory, graph_file_name))
        with open("{}{}.txt".format(directory, param_file_name), 'w') as f:
            f.write("{}\n".format(self.bus_count))
            f.write("{}\n".format(self.bus_size))
            for group in self.rowdy_groups:
                f.write(str(group))
                f.write("\n")

    def score_graph(self):
        """
        Quick and dirty set_score for the graph.
        Note that there is a lot of file writing so that we could use
        the included output_scorer.

        :return: Score of the current solution on the current graph.
        """
        if not os.path.exists("temp"):
            os.makedirs("temp")
        self.write_solution("temp")
        self.write_input("graph", "parameters")
        score = output_scorer.score_output("temp", "temp/temp.out")
        return score

    def draw_graph(self):
        """
        Simple method to draw the graph where super set vertices
        are spaced out evenly on a horizontal line.
        """
        fixed_pos = {x: (y, 0) for x, y in
                     zip(self.super_set, range(0, len(self.super_set) * 2, 2))}
        pos = nx.spring_layout(self.G, fixed=fixed_pos.keys(), pos=fixed_pos)
        nx.draw_networkx(self.G, pos=pos, edge_color='g')
        nx.draw_networkx_nodes(self.G, pos=pos, nodelist=self.super_set, node_color='b')
        plt.axis('off')
        plt.show()


def main():
    opts = OptionParser()
    opts.add_option('-d', '--directory', dest='output_dir', type=str, default='',
                    help="The desired directory of the output. Default = ''")
    opts.add_option('-n', '--name', dest='output_name', type=str, default='large-input.txt',
                    help="The desired file name of the output. Default = 'large-input'")
    opts.add_option('-k', '--kids', dest='kids_cnt', type=int, default=1000,
                    help='The number of kids. Default = 1000')
    opts.add_option('-b', '--buses', dest='bus_cnt', type=int, default=25,
                    help='The number of buses (base). This will be increased '
                         'by at most 3. Default = 25')
    opts.add_option('-c', '--constraints', dest='constraint_limit', type=int, default=2000,
                    help='Max number of constraints. Default = 2000')
    opts.add_option("-G", action="store_true", dest="graph",
                    help="Toggle graphing of input after generation")

    # Argument parsing / cleaning
    options, args = opts.parse_args()
    if options.output_name[-4:] == ".txt" or options.output_name[-4:] == ".out":
        options.output_name = options.output_name[:-4]
    if options.output_dir and options.output_dir[-1] != "/":
        options.output_dir = "{}/".format(options.output_dir)
    if options.output_dir and not os.path.exists(options.output_dir):
        os.makedirs(options.output_dir)
    if options.kids_cnt < 25:
        raise ValueError("Kids count below 25")
    elif 25 <= options.kids_cnt <= 50 and options.constraint_limit > 100 or \
            250 <= options.kids_cnt <= 500 and options.constraint_limit > 1000 or \
            500 <= options.kids_cnt <= 1000 and options.constraint_limit > 2000:
        raise ValueError("Constraint sizes {} for {} kids".format(options.constraint_limit, options.kids_cnt))

    gen = InputGenerator(options.kids_cnt, options.bus_cnt, options.constraint_limit)
    gen.generate()
    gen.write_solution(options.output_name, options.output_dir)
    gen.write_input(options.output_name, options.output_name, options.output_dir)
    print("Generated files in: {}".format(options.output_dir if options.output_dir else "same directory"))
    print("\nScore: {}".format(gen.score_graph()))
    print("Number of edges: {}".format(len(gen.G.edges)))
    print("Top 20 Degrees: key = (vertex, degree):\n {}".format(
        list(sorted(gen.G.degree, key=lambda x: x[1], reverse=True))[:20]))
    print("Super Set: {}".format(gen.super_set))
    print("Trouble Makers: {}".format(gen.trouble_makers))
    print("Decoy: {}".format(gen.decoy))

    # Willow's Tooling
    print("Constraints Remaining: {}".format(gen.constraint_limit - len(gen.rowdy_groups)))
    print("Number of Students: {}".format(gen.kids_count))


    if options.graph:
        gen.draw_graph()


if __name__ == "__main__":
    main()
