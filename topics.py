import argcomplete

from configuration import Configuration

METEO_TOPICS = {
    "homectrl/onair/meteo/#": None,
    "homectrl/onair/meteo/current": {
        "homectrl/onair/meteo/current": None,
        "homectrl/onair/meteo/current/#": None,
    },
    "homectrl/onair/meteo/forecast/hourly": {
        "homectrl/onair/meteo/forecast/hourly": None,
        "homectrl/onair/meteo/forecast/hourly/#": None,
    },
    "homectrl/onair/meteo/past/hourly": {
        "homectrl/onair/meteo/past/hourly": None,
        "homectrl/onair/meteo/past/hourly/#": None,
    }
}

TOPICS = {
    "homectrl/" : {
        "homectrl/#" : None,
        "homectrl/device/": {
            "homectrl/device/#": None
        },
        "homectrl/onair/": {
            "homectrl/onair/#": None,
            "homectrl/onair/activity/": {
                "homectrl/onair/activity/#": None,
                "homectrl/onair/activity/laundry": None,
                "homectrl/onair/activity/astro": None,
                "homectrl/onair/activity/holidays": None,
            },
            "homectrl/onair/meteo/": METEO_TOPICS
        }
    }
}

def select_node_value(input: str, nodes: dict) -> None | dict:
    for key, value in nodes.items():
        if input == key:
            return value
        if key.startswith(input):
            return value
        elif input.startswith(key):
            # If input is longer, go deeper
            if isinstance(value, dict):
                return select_node_value(input, value)
    return None

# for test in ["homectrl/onair/activity/holidays", "homectrl/onair/activity/meteo", "homectrl/onair/activity/meteo/forecast/hourly"]:
#     print(f"{test} => {select_node_value(test, TOPICS)}")

class TopicCompleter(argcomplete.completers.BaseCompleter):

    def __init__(self, boards: list[str], meteo_providers: dict):
        super().__init__()
        self.boards = boards
        self.meteo_providers = meteo_providers

    def _add_meteo_providers(self, path: str, type: str):
        # Dynamically add boards to topics
        node = select_node_value(path, TOPICS)
        for p in self.meteo_providers[type]:
            node[f"{path}/{p}"] = None

    def _add_boards(self):
        # Dynamically add boards to topics
        device_topics = TOPICS["homectrl/"]["homectrl/device/"]
        for board in self.boards:
            device_topics[f"homectrl/device/{board}/#"] = None

    def getlist(self, input, topics: dict) -> list[str]:
        results: list[str] = []
        for key, value in topics.items():
            if key.startswith(input):
                # If input matches the key, and value is a dict, return its keys
                if isinstance(value, dict):
                    results.extend(value.keys())
                else:
                    results.append(key)
            elif input.startswith(key):
                # If input is longer, go deeper
                if isinstance(value, dict):
                    results.extend(self.getlist(input, value))
        return results

    def __call__(self, prefix, parsed_args, **kwargs):
        if prefix.startswith("homectrl/d"):
            self._add_boards()
        if prefix.startswith("homectrl/onair/meteo/c"):
            self._add_meteo_providers("homectrl/onair/meteo/current", 'current')
        if prefix.startswith("homectrl/onair/meteo/f"):
            self._add_meteo_providers("homectrl/onair/meteo/forecast/hourly", 'forecast/hourly')
        if prefix.startswith("homectrl/onair/meteo/p"):
            self._add_meteo_providers("homectrl/onair/meteo/past/hourly", 'past/hourly')
        return self.getlist(prefix, TOPICS)
