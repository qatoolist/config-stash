from config_stash.utils.lazy_loader import LazyLoader


class AttributeAccessor:
    def __init__(self, lazy_loader, hook_processor=None):
        self.lazy_loader = lazy_loader
        self.hook_processor = hook_processor

    def __getattr__(self, item):
        try:
            value = self.lazy_loader.get(item)
            if isinstance(value, dict):
                return AttributeAccessor(LazyLoader(value), self.hook_processor)
            # Apply hooks if hook_processor is available
            if self.hook_processor:
                value = self.hook_processor.process_hooks(item, value)
            return value
        except KeyError:
            raise AttributeError(f"'Config' object has no attribute '{item}'")
