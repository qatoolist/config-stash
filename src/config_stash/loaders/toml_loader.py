import toml
from config_stash.loaders.loader import Loader

class TomlLoader(Loader):
    def load(self):
        try:
            content = self._read_file(self.source)
            self.config = toml.loads(content)
        except toml.TomlDecodeError as error:
            self._handle_error(error)
        return self.config