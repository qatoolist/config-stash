class ConfigMerger:
    @staticmethod
    def merge_configs(configs, deep_merge=False):
        merged_config = {}
        for config, _ in configs:
            merged_config = ConfigMerger._merge_dicts(merged_config, config, deep_merge)
        return merged_config

    @staticmethod
    def _merge_dicts(base, new, deep_merge):
        for key, value in new.items():
            if deep_merge and isinstance(value, dict) and key in base:
                base[key] = ConfigMerger._merge_dicts(base[key], value, deep_merge)
            else:
                base[key] = value
        return base