import os
import re

class EnvVarExpander:
    env_var_pattern = re.compile(r'\$\{([^}^{]+)\}')

    @staticmethod
    def expand(value):
        if isinstance(value, str):
            return EnvVarExpander.env_var_pattern.sub(
                lambda match: os.environ.get(match.group(1), match.group(0)),
                value
            )
        return value

    @staticmethod
    def hook(value):
        return EnvVarExpander.expand(value)