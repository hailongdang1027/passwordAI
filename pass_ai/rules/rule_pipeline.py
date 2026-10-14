import json
import uuid
from datetime import datetime


class RulePipeline:

    def __init__(self):

        self.pipeline = {

            "pipeline_id": str(uuid.uuid4()),

            "created_at": datetime.now().isoformat(),

            "steps": []

        }

    def add(self, rule_name, **params):

        self.pipeline["steps"].append({

            "id": len(self.pipeline["steps"]) + 1,

            "rule": rule_name,

            "params": params

        })

    def save(self, filename):

        with open(filename, "w", encoding="utf-8") as f:

            json.dump(

                self.pipeline,

                f,

                indent=4,

                ensure_ascii=False

            )

    @classmethod
    def load(cls, filename):

        pipe = cls()

        with open(filename, encoding="utf-8") as f:

            pipe.pipeline = json.load(f)

        return pipe

    def get_steps(self):

        return self.pipeline["steps"]