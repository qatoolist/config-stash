import yaml
from config_stash.loaders.loader import Loader

class YamlLoader(Loader):
    def load(self):
        try:
            content = self._read_file(self.source)
            self.config = yaml.safe_load(content)
        except yaml.YAMLError as error:
            self._handle_error(error)
        return self.config