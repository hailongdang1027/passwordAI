import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rules.executor import RuleExecutor

from rules.rule_pipeline import RulePipeline

from rules.name_rule import NameRule

from rules.date_rule import DateRule

from rules.leet_rule import LeetRule from rules.executor import RuleExecutor

from rules.name_rule import NameRule

from rules.date_rule import DateRule

profile = {

    "fullname":"Dang Hai Long",

    "birthdate":"17072002"

}

pipe = RulePipeline()

pipe.add("NAME")

pipe.add("DATE",format="YEAR")

pipe.add("LEET",max_change=2)

executor = RuleExecutor()

executor.register(

    "NAME",

    NameRule

)

executor.register(

    "DATE",

    DateRule

)

executor.register(

    "LEET",

    LeetRule

)

passwords, statistics = executor.execute_pipeline(

    pipe,

    profile

)

print(len(passwords))

