from pybm.specs import BenchmarkEnvironment


def format_environment(environment: BenchmarkEnvironment):
    name = environment.get_value("name")
    commit = environment.get_value("workspace.commit")