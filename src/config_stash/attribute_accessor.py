from config_stash.utils.lazy_loader import LazyLoader


class AttributeAccessor:
    def __init__(self, lazy_loader):
        self.lazy_loader = lazy_loader

    def __getattr__(self, item):
        try:
            value = self.lazy_loader.get(item)
            if isinstance(value, dict):
                return AttributeAccessor(LazyLoader(value))
            return value
        except KeyError:
            raise AttributeError(f"'Config' object has no attribute '{item}'")