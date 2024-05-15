from config_stash.attribute_accessor import AttributeAccessor
from config_stash.config_merger import ConfigMerger
from config_stash.environment_handler import EnvironmentHandler
from config_stash.loader_manager import LoaderManager
from config_stash.source_tracker import SourceTracker
from config_stash.config_watcher import ConfigFileWatcher
from config_stash.config_reader import get_default_loaders, get_default_settings
from config_stash.config_loader import ConfigLoader
from config_stash.config_extender import ConfigExtender
from config_stash.hook_processor import HookProcessor
from config_stash.hooks.env_var_expander import EnvVarExpander
from config_stash.hooks.type_casting import TypeCasting
from config_stash.utils.lazy_loader import LazyLoader

class Config:
    def __init__(self, env=None, loaders=None, dynamic_reloading=None, use_env_expander=True, use_type_casting=True):
        defaults = get_default_settings()
        
        self.env = env or defaults["default_environment"]
        self.dynamic_reloading = dynamic_reloading if dynamic_reloading is not None else defaults["dynamic_reloading"]
        self.use_env_expander = use_env_expander
        self.use_type_casting = use_type_casting

        self.loader_manager = LoaderManager(loaders or self._load_default_files())
        self.config_loader = ConfigLoader(self.loader_manager.loaders)
        self.configs = self.config_loader.load_configs()
        self.merged_config = ConfigMerger.merge_configs(self.configs)
        self.env_config = EnvironmentHandler(self.env, self.merged_config).get_env_config()
        self.lazy_loader = LazyLoader(self.env_config)
        self.attribute_accessor = AttributeAccessor(self.lazy_loader)
        self.source_tracker = SourceTracker(self.loader_manager.loaders)
        self.hook_processor = HookProcessor()

        self._register_default_hooks()

        if self.dynamic_reloading:
            self.file_watcher = ConfigFileWatcher(self)
            self.file_watcher.start()

        self.config_extender = ConfigExtender(self)

    def _load_default_files(self):
        loaders = []
        default_files = get_default_settings()["default_files"]
        loader_classes = get_default_loaders()

        for file in default_files:
            ext = file.split('.')[-1]
            if ext in loader_classes:
                loaders.append(loader_classes[ext](file))
        loaders.append(loader_classes["env"](get_default_settings()["default_prefix"]))
        
        return loaders

    def _register_default_hooks(self):
        if self.use_env_expander:
            self.hook_processor.register_global_hook(EnvVarExpander.hook)
        if self.use_type_casting:
            self.hook_processor.register_global_hook(TypeCasting.hook)

    def __getattr__(self, item):
        value = getattr(self.attribute_accessor, item)
        return self.hook_processor.process_hooks(item, value)

    def get_source(self, key):
        return self.source_tracker.get_source(key)

    def reload(self):
        print("Reloading configuration...")
        self.configs = self.config_loader.load_configs()
        self.merged_config = ConfigMerger.merge_configs(self.configs)
        self.env_config = EnvironmentHandler(self.env, self.merged_config).get_env_config()
        self.lazy_loader = LazyLoader(self.env_config)
        self.attribute_accessor = AttributeAccessor(self.lazy_loader)

    def get_watched_files(self):
        files = []
        for loader in self.loader_manager.loaders:
            if hasattr(loader, 'source'):
                files.append(loader.source)
        return files

    def stop_watching(self):
        if self.dynamic_reloading:
            self.file_watcher.stop()

    def extend(self, loader):
        self.config_extender.extend_config(loader)

    def register_key_hook(self, key, hook):
        self.hook_processor.register_key_hook(key, hook)

    def register_value_hook(self, value, hook):
        self.hook_processor.register_value_hook(value, hook)

    def register_condition_hook(self, condition, hook):
        self.hook_processor.register_condition_hook(condition, hook)

    def register_global_hook(self, hook):
        self.hook_processor.register_global_hook(hook)