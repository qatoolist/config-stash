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
            # Only do deep merge if both values are dicts
            if deep_merge and isinstance(value, dict) and key in base and isinstance(base[key], dict):
                base[key] = ConfigMerger._merge_dicts(base[key], value, deep_merge)
            else:
                # Replace value (including type mismatches like list->dict or dict->string)
                base[key] = value
        return base
