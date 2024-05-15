import json
from config_stash.loaders.loader import Loader

class JsonLoader(Loader):
    def load(self):
        try:
            content = self._read_file(self.source)
            self.config = json.loads(content)
        except json.JSONDecodeError as error:
            self._handle_error(error)
        return self.config