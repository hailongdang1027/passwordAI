import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rules.rule_pipeline import RulePipeline


pipe = RulePipeline()

pipe.add("NAME")

pipe.add("DATE", format="YEAR")

pipe.add("SUFFIX", char="@")

pipe.add("LEET", max_change=2)

pipe.save("pipeline.json")


pipe2 = RulePipeline.load("pipeline.json")

print(pipe2.pipeline)