from typing import Dict, List, Any, Text, Union

Environment = Dict[Text, Any]


class EnvironmentStore:
    """Environment database keeping track of the present benchmarking
    environments."""

    def __init__(self):
        self.environments: List[Environment] = []

    def add(self, environment: Environment):
        self.environments.append(environment)

    def get(self, attr: str, value: str) -> Union[Environment, None]:
        try:
            env = next(e for e in self.environments if e[attr] == value)
        except StopIteration:
            env = None
        return env

    def delete(self, env: Environment):
        self.environments.remove(env)

    def delete_by_attr(self, attr: str, value: str):
        env = self.get(attr, value)
        if env is not None:
            self.delete(env)

    def update(self, attr: str, old: str, new: str):
        env = self.get(attr, old)
        env[attr] = new


EnvDB = EnvironmentStore()
