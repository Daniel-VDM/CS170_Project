import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from optparse import OptionParser
import re
import random
import itertools


class InputGenerator:

    def __init__(self, kids_count, bus_count, constraint_count):
        """
        Params are passed in from the options parser in main.
        """
        self.kids_count = kids_count
        self.bus_count = bus_count
        self.constraint_count = constraint_count
        self.bus_size = None  # TBD when generating the input.
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
        sol = [list(l) for l in np.array_split(np.array(lst), self.bus_count)]
        for _ in range(self.kids_count//self.bus_count):  # More loops = More uneven group sizes.
            move_from = sol[random.randint(0, len(sol)-1)]
            move_to = sol[random.randint(0, len(sol)-1)]
            if len(move_from) > 3:  # This is an arbitrary min size check that can be changed.
                move_to.append(move_from.pop())
        self.solution = sol

    def generate_constraints(self):
        """
        Follow the API.

        Currently Implemented:
            - Created a basic super set, were each bus in the solution
              has 1 person in the super set.
            - Added the |Super Set| choose 2 constraints as discussed.
        """
        for group in self.solution:
            self.super_set.add(group[0])
        for tup in itertools.combinations(list(self.super_set), 2):
            self.rowdy_groups.append(list(tup))

        # TODO: Extra constraints.

    def generate_friends(self):
        """
        Follow the API.

        Currently Implemented:
            - Made the vertices in the super set a clique.
        """
        for tup in itertools.combinations(list(self.super_set), 2):
            self.G.add_edge(tup[0], tup[1])

        # TODO: Friend / Edge generation.

    def write_solution(self, filename, directory):
        """
        Writes our planted solution's .out file as specified in the
        project spec.

        :param filename: clean filename string with no file extension.
        :param directory: directory string with slashes included.
        """
        with open("{}/{}.out".format(directory, filename), 'w') as f:
            for lst in self.solution:
                f.write(str(lst))
                f.write("\n")

    def write_input(self, filename, directory):
        """
        Writes the graph's (G) .gml file and parameters .txt file as
        specified in the project spec.

        :param filename: clean filename string with no file extension.
        :param directory: directory string with slashes included.
        """
        nx.write_gml(self.G, "{}/{}.gml".format(directory, filename))
        with open("{}/{}.txt".format(directory, filename), 'w') as f:
            f.write("{}\n".format(self.bus_count))
            f.write("{}\n".format(self.bus_size))
            for group in self.rowdy_groups:
                f.write(str(group))
                f.write("\n")


def main():
    opts = OptionParser()
    opts.add_option('-o', '--output', dest='output_dir', type=str, default='',
                    help='The desired directory of the output.')
    opts.add_option('-n', '--name', dest='output_name', type=str, default='large-input',
                    help='The desired file name of the output.')
    opts.add_option('-k', '--kids', dest='kids_cnt', type=int, default=1000,
                    help='The number of kids. Default=1000')
    opts.add_option('-b', '--buses', dest='bus_cnt', type=int, default=25,
                    help='The number of buses. Default=25')
    opts.add_option('-c', '--constraints', dest='constraint_size', type=int, default=2000,
                    help='Max number of constraints. Default=2000')
    options, args = opts.parse_args()

    # Argument parsing / cleaning
    if re.compile(".*.txt").match(options.output_name) is not None or \
            re.compile(".*.out").match(options.output_name) is not None:
        options.output_name = options.output_name[:-4]
    if re.compile("input_gen-output/.*.").match(options.output_dir) is None:
        options.output_dir = "input_gen-output/{}".format(options.output_dir)
    if options.kids_cnt < 25:
        raise IOError("Kids count below 25")
    elif 25 <= options.kids_cnt <= 50 and options.constraint_size > 100 or \
            250 <= options.kids_cnt <= 500 and options.constraint_size > 1000 or \
            500 <= options.kids_cnt <= 1000 and options.constraint_size > 2000:
        raise IOError("Constraint sizes {} for {} kids".format(options.constraints, options.kids_cnt))

    gen = InputGenerator(options.kids_cnt, options.bus_cnt, options.constraint_size)

    # TODO: File Generation
    gen.generate_solution()
    gen.generate_constraints()
    gen.generate_friends()

    gen.write_solution(options.output_name, options.output_dir)
    gen.write_input(options.output_name, options.output_dir)


if __name__ == "__main__":
    main()
