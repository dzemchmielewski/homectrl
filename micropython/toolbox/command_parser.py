import json


class CommandParser:

    def __init__(self, commands: dict):
        self.commands = commands

    def parse(self, command: str, return_type=dict):
        (path, param, error) = self._parse(command)
        if return_type is dict:
            return {
                'command': path,
                'params': param,
                'error': error
            }
        else:
            return path, param, error

    def _parse(self, command: str) -> tuple:
        parts = command.split()
        current = self.commands
        path = []

        for part in parts:

            if current and isinstance(current, dict):
                if part in current:
                    path.append(part)
                    current = current[part]

                    if not current:
                        return ' '.join(path), None, None
                    else:
                        continue
                else:
                    return None, None,  f"Unknown command: {' '.join(path + [part])}"

            if current:
                if isinstance(current, list):
                    try:
                        params = json.loads(part)
                        if isinstance(params, list) and len(params) == len(current):
                            for i in range(len(params)):
                                if not isinstance(params[i], current[i]):
                                    return None, None, f"Invalid parameter: expected {current[i]} and position {i} but got {type(params[i])} ({params[i]})"
                            return ' '.join(path), params, None
                        else:
                            return None, None, f"Invalid parameter: expected array {current}"
                    except ValueError:
                        return None, None, "Invalid parameter format"

                else:  # not array - any other type - convert part to that type
                    try:
                        return ' '.join(path), current(part), None
                    except ValueError:
                        return None, None, "Invalid parameter format"

            else:
                return ' '.join(path), None, None

        if current:
            if isinstance(current, dict):
                return None, None, f"Subcommand required: {list(current.keys())}"
            else:
                return None, None, f"Parameter required: {current}"
