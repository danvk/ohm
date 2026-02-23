#!/usr/bin/env python

import json
import sys

if __name__ == "__main__":
    (input_file,) = sys.argv[1:]
    fc = json.load(open(input_file))
    print(len(fc["features"]))
