import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class FakeTool:
    """Records tool calls; stands in for Toolbox in skill tests."""
    def __init__(self):
        self.calls = []
    def run(self, name, args):
        self.calls.append((name, args))
        return f"ran {name}"
