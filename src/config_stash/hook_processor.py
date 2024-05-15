class HookProcessor:
    def __init__(self):
        self.hooks = {
            "key": {},
            "value": {},
            "condition": [],
            "global": []
        }

    def register_key_hook(self, key, hook):
        if key not in self.hooks["key"]:
            self.hooks["key"][key] = []
        self.hooks["key"][key].append(hook)

    def register_value_hook(self, value, hook):
        if value not in self.hooks["value"]:
            self.hooks["value"][value] = []
        self.hooks["value"][value].append(hook)

    def register_condition_hook(self, condition, hook):
        self.hooks["condition"].append((condition, hook))

    def register_global_hook(self, hook):
        self.hooks["global"].append(hook)

    def process_hooks(self, key, value):
        if key in self.hooks["key"]:
            for hook in self.hooks["key"][key]:
                value = hook(value)

        if value in self.hooks["value"]:
            for hook in self.hooks["value"][value]:
                value = hook(value)

        for condition, hook in self.hooks["condition"]:
            if condition(key, value):
                value = hook(value)

        for hook in self.hooks["global"]:
            value = hook(value)

        return value