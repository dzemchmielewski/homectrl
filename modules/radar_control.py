from modules.ld2410 import LD2410
from board.command_parser import CommandParser

# Ranges:
# GATE: 0, 0.00m - 0.75m
# GATE: 1, 0.75m - 1.50m
# GATE: 2, 1.50m - 2.25m
# GATE: 3, 2.25m - 3.00m
# GATE: 4, 3.00m - 3.75m
# GATE: 5, 3.75m - 4.50m
# GATE: 6, 4.50m - 5.25m
# GATE: 7, 5.25m - 6.00m
#
# Read the currently configured parameters:
# radar.read_detection_params())
#
# returns 3 arrays:
#
# first array: [moving gate threshold, static gate threshold, empty timeout]
# second array: [moving gate sens 1.... moving gate sens 8]
# third array: [static gate sens 1.... static gate sens 8]

class RadarControl:

    def __init__(self, radar: LD2410):
        self.radar = radar
        self.cp = CommandParser({
            "help": None,
            "firmware": None,
            "read": None,
            "bt": {
                "on": None,
                "off": None,
                "mac": None
            },
            "config": {
                "help": None,
                "get": None,
                "set": {
                    "sensitivity": [int, int, int],
                    "threshold": [int, int, int]
                }
            },
            "restart": None,
            "factory_reset": None
        })
        self.help = f"radar {list(self.cp.commands.keys())}"

    def handle_help(self):
        return self.help

    def handle_message(self, msg):
        if msg == "temp":
            import sys
            sys.exit()

        command = self.cp.parse(msg)
        if (c := command['command']) is None:
            return f'{{"error": "{command["error"]}"}}'

        params = command["params"]

        if c == "help":
            return f'{{"message": "Available commands: {self.help}"}}'

        elif c == "firmware":
            return f'{{"firmware": "{self.radar.read_firmware_version()}"}}'

        elif c == "read":
            return f'{{"data": "{self.radar.get_radar_data()}"}}'

        elif c == "restart":
            self.radar.restart_module()
            return f'{{"message": "Command executed."}}'

        elif c == "factory_reset":
            self.radar.factory_reset()
            return f'{{"message": "Command executed."}}'

        elif c == "bt on":
            self.radar.bt_enable()
            return f'{{"message": "Command executed."}}'

        elif c == "bt off":
            self.radar.bt_disable()
            return f'{{"message": "Command executed."}}'

        elif c == "bt mac":
            return f'{{"mac": "{self.radar.bt_query_mac()}"}}'

        elif c == "config get":
            return f'{{"config": "{self.radar.read_detection_params()}"}}'

        elif c == "config help":
            return ("sensitivity: [gate(1-8), move sensitivity (0-100), static sensitivity (0-100)]  "
                    "threshold: [move max gate (1-8), static max gate (1-8), timeout]. "
                    "The presence of a target is determined when the detected target energy value (range 0 to 100) is greater"
                    " than the sensitivity value, otherwise it is ignored.")

        elif c == "config set sensitivity":
            if not (1 <= params[0] <= 8):
                return f'{{"error": "Parameter gate ({params[0]}) out of range: (1-8)"}}'
            for i in range(2):
                if not (0 <= params[i+1] <= 100):
                    return f'{{"error": "Parameter #{i+2} ({params[i+1]}) out of range: (0-100)"}}'
            self.radar.edit_gate_sensitivity(params[0] - 1, params[1], params[2])
            return f'{{"message": "Config sensitivity applied: {params}"}}'

        elif c == "config set threshold":
            for i in range(2):
                if not (1 <= params[i] <= 8):
                    return f'{{"error": "Parameter max gate #{i+1} ({params[i]}) out of range: (1-8)"}}'
            if params[2] < 0:
                return f'{{"error": "Parameter timeout ({params[2]}) out of range: (0-...)"}}'
            self.radar.edit_detection_params(params[0], params[1], params[2])
            return f'{{"message": "Config threshold applied: {params}"}}'

        else:
            return f'{{"error": "Unexpected error. Something is not implemented. Command: {command}"}}'

