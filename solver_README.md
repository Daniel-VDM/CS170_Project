# Solver Readme

### Imports
We use a few extra libraries for this project so be sure to have access to numpy and networkx, among others.

### Global Variables
- path_to_inputs  -> Here's where to changed path to inputs.
- path_to_outputs -> Here's where to changed path to outputs.
- score_path      -> Path to the JSON file which stores the solution scores for iterative improvements. The code dumps a JSON file used for solution bookkeeping into our outputs folder as well as a backup (scores.json and scores.json.bak respectively). Remove both before submitting.

### Execution
Running the command `python solver.py` will run the solver. For more detail as the solver runs, you can set the `verbose` argument to be True in main which will provide progress information to the console buffer.

### Sample Execution: 
`python solver.py`

### Sample Output:
```
Score on iteration 999 of TreeSearchOptimizer: 0.2659
[03:25:35.284577] New score for ./outputs/medium/73.out was <= to old score. DID NOT WRITE. (diff = 0.0)

Time Elapsed: 0:04:04.919981 hrs
Average Score (on leaderboard): 0.47366395938104744
```
