class Loader:
    def __init__(self, source):
        self.source = source
        self.config = {}

    def load(self):
        raise NotImplementedError("Load method must be implemented by subclasses")

    def _read_file(self, source):
        with open(source, 'r') as file:
            return file.read()

    def _handle_error(self, error):
        raise RuntimeError(f"Error loading configuration from {self.source}: {error}")