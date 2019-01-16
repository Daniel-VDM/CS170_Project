import sys
import random


def main():
    in_file = sys.argv[1]
    out_file = sys.argv[2]

    folder_name = "input_gen-output/"

    with open(folder_name + in_file, 'r') as i:
        lines = i.readlines()

    # Store the number of busses and capacity for later.
    busses = lines.pop(0)
    capacity = lines.pop(0)

    # Shuffle the lines to be random.
    random.shuffle(lines)

    # Reinsert the number of busses and bus capacity.
    lines.insert(0, capacity)
    lines.insert(0, busses)

    # Write the newly shuffled lines back out.
    with open(folder_name + out_file, 'w') as o:
        for line in lines:
            o.write(line)

    return


if __name__ == "__main__":
    main()
