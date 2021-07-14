import argparse

class CLICommand:
    """CLI command base class."""
    usage = None

    def __init__(self, name: str, **argument_parser_kwargs):
        # command name
        self.name = name
        self.parser = argparse.ArgumentParser(prog=self.format_name(),
                                              usage=self.usage,
                                              description=self.__doc__,
                                              **argument_parser_kwargs)

    def add_arguments(self):
        """Add arguments to class argument parser member."""
        raise NotImplementedError

    def format_name(self) -> str:
        return f"pybm {self.name}".strip()

    def run(self, *args, **kwargs) -> int:
        """Execute the logic behind a run CLI command."""
        raise NotImplementedError
