class TypeCasting:
    @staticmethod
    def cast(value):
        if isinstance(value, str):
            # Try to cast to int
            try:
                return int(value)
            except ValueError:
                pass

            # Try to cast to float
            try:
                return float(value)
            except ValueError:
                pass

            # Try to cast to boolean
            lower_value = value.lower()
            if lower_value in ['true', 'false']:
                return lower_value == 'true'

        return value

    @staticmethod
    def hook(value):
        return TypeCasting.cast(value)