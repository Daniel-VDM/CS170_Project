# Input Generator Readme

**This generator requires that the given `output_scorer.py` script be included in the same directory.**

All avaliable options for the input generator can be found with the help option, i.e: `python input_gen.py --help`

Below is a copy of the help message for reference:
```
Options:
  -h, --help            show this help message and exit
  -d OUTPUT_DIR, --directory=OUTPUT_DIR
                        The desired directory of the output. Default = ''
  -n OUTPUT_NAME, --name=OUTPUT_NAME
                        The desired file name of the output. Default = 'large-input'
  -k KIDS_CNT, --kids=KIDS_CNT
                        The number of kids. Default = 1000
  -b BUS_CNT, --buses=BUS_CNT
                        The number of buses (base). This will be increased by
                        at most 3. Default = 25
  -c CONSTRAINT_LIMIT, --constraints=CONSTRAINT_LIMIT
                        Max number of constraints. Default = 2000
  -G                    Toggle graphing of input after generation
```

Sample execution: `python input_gen.py -d "input_gen-output/" -n "large-input" -k 1000 -b 25 -c 2000 -G`

Note that the size of the buses (`s` in the spec) is set internally by the script and it is not something that can be set as an option.