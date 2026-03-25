from config_stash.utils.type_coercion import parse_scalar_value


class TypeCasting:
    @staticmethod
    def cast(value):
        if isinstance(value, str):
            return parse_scalar_value(value)
        return value

    @staticmethod
    def hook(value):
        return TypeCasting.cast(value)
