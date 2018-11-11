import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from optparse import OptionParser
import math
import random
import itertools
import os
import output_scorer


class InputGenerator:

    def __init__(self, kids_count, bus_count, constraint_count):
        """
        Params are passed in from the options parser in main.
        """
        self.kids_count = kids_count
        self.bus_count = bus_count
        self.constraint_count = constraint_count
        self.bus_size = kids_count  # TBD, this should change during file generation.
        self.super_set = set()
        self.rowdy_groups = []
        self.solution = []
        self.G = nx.Graph()
        self.G.add_nodes_from((str(i) for i in range(kids_count)))
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
        for _ in range(self.kids_count//self.bus_count):  # More loops = More uneven group sizes.
            move_from = sol[random.randint(0, len(sol)-1)]
            move_to = sol[random.randint(0, len(sol)-1)]
            if len(move_from) > 3:  # This is an arbitrary min size check that can be changed.
                move_to.append(move_from.pop())
        self.solution = sol

    def generate_super_set(self):
        """
        Separate super set creator on its own so that we can change
        this in the future.
        """
        for group in self.solution:
            self.super_set.add(group[0])

    def generate_constraints(self):
        """
        Follow the API.

        Currently Implemented:
            - Created a basic super set, were each bus in the solution
              has 1 person in the super set.
            - Added the |Super Set| choose 2 constraints as discussed.
        """
        for tup in itertools.combinations(list(self.super_set), 2):
            self.rowdy_groups.append(list(tup))

        # TODO: Extra constraints.

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
            a = (3*len(bus_solo_vertices)) // 4
            b = len(bus_solo_vertices)
            to_bus_super_vertex = random.randint(a, b)

            other_super_vertices = self.super_set - (self.super_set & bus)
            a = len(other_super_vertices) // 2
            b = len(other_super_vertices)
            to_other_super_vertex = random.randint(a, b)

            bus_non_super_vertices = bus - self.super_set
            a = len(bus_non_super_vertices) // 2
            b = len(bus_non_super_vertices)
            to_inside_bus = random.randint(a, b)

            all_other_vertices = (set(self.G.nodes) - self.super_set) - bus
            a = len(all_other_vertices) // 4
            b = len(all_other_vertices) // 2
            to_spread = random.randint(a, b)

            lst = [to_bus_super_vertex, to_other_super_vertex, to_inside_bus, to_spread]
            bus_edge_budgets.append(lst)
        return bus_edge_budgets

    def generate_friends(self):
        """
        Main method for generating friend edges.

        Currently Implemented:
            - Made the vertices in the super set a clique.
            - Created super set common friends.
        """
        for tup in itertools.combinations(list(self.super_set), 2):
            self.G.add_edge(tup[0], tup[1])
        super_set_common_friend_lst = self._create_super_set_common_friends(percentage=0.15)

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
            self._assign_edges(U, V, prob=0.75)

            # Edge to other super vertices:
            U = random.sample(self.super_set - set(bus_super_vertices), budget_lst[1])
            V = random.sample(bus_vertices, budget_lst[1])
            self._assign_edges(U, V, prob=0.5)

            # Internal bus edges
            U = []
            V = []
            pool = list(bus_vertices - set(bus_super_vertices))
            for _ in range(budget_lst[2]):
                u = random.choice(pool)
                U.append(random.choice(pool))
                v = random.choice(pool)
                while v == u:
                    v = random.choice(pool)
                V.append(v)
            self._assign_edges(U, V, prob=0.7)

            # Spread edges
            U = np.random.choice(list(bus_vertices - self.super_set), size=budget_lst[3], replace=True)
            V = random.sample((set(self.G.nodes) - self.super_set) - bus_vertices, budget_lst[3])
            self._assign_edges(U, V, prob=0.2)

    def generate(self):
        """
        Method to simply generate the file.

        Order of generation can be changes if desired.
        """
        self.generate_solution()
        self.generate_super_set()
        self.generate_constraints()
        self.generate_friends()

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
        nx.write_gml(self.G, "{}{}.gml".format(directory, graph_file_name))
        with open("{}{}.txt".format(directory, param_file_name), 'w') as f:
            f.write("{}\n".format(self.bus_count))
            f.write("{}\n".format(self.bus_size))
            for group in self.rowdy_groups:
                f.write(str(group))
                f.write("\n")

    def score_graph(self):
        """
        Quick and dirty scorer for the graph.
        Note that there is a lot of file writing so that we could use
        the included output_scorer.

        :return: Score of the current solution on the current graph.
        """
        if not os.path.exists("temp"):
            os.makedirs("temp")
        self.write_solution("temp")
        self.write_input("graph", "parameters")
        score = output_scorer.score_output("temp", "temp/temp.out")
        return score[0]

    def draw_graph(self):
        """
        Simple method to draw the graph where super set vertices
        are spaced out evenly on a horizontal line.
        """
        fixed_pos = {x: (y, 0) for x, y in
                     zip(self.super_set, range(0, len(self.super_set)*2, 2))}
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
                    help='The number of buses. Default = 25')
    opts.add_option('-c', '--constraints', dest='constraint_size', type=int, default=2000,
                    help='Max number of constraints. Default = 2000')

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
    elif 25 <= options.kids_cnt <= 50 and options.constraint_size > 100 or \
            250 <= options.kids_cnt <= 500 and options.constraint_size > 1000 or \
            500 <= options.kids_cnt <= 1000 and options.constraint_size > 2000:
        raise ValueError("Constraint sizes {} for {} kids".format(options.constraints, options.kids_cnt))

    gen = InputGenerator(options.kids_cnt, options.bus_cnt, options.constraint_size)
    gen.generate()
    gen.write_solution(options.output_name, options.output_dir)
    gen.write_input(options.output_name, options.output_name, options.output_dir)
    print("Generated files in: {}".format(options.output_dir if options.output_dir else "same directory"))
    print("Score: {}".format(gen.score_graph()))
    print("Number of edges: {}".format(len(gen.G.edges)))
    print("Top 20 Degrees: key = (vertex, degree):\n {}".format(
        list(sorted(gen.G.degree, key=lambda x: x[1], reverse=True))[:20]))
    print("Super Set: {}".format(gen.super_set))
    gen.draw_graph()


if __name__ == "__main__":
    main()
