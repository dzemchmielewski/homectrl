import sys
import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Workaround for matplotlib Path.__deepcopy__ infinite recursion on Python 3.14
import copy
import numpy as np
import matplotlib.path as _mpath

def _path_deepcopy_fix(self, memo):
    cls = self.__class__
    result = cls.__new__(cls)
    memo[id(self)] = result
    for k, v in self.__dict__.items():
        object.__setattr__(result, k, v.copy() if isinstance(v, np.ndarray) else copy.deepcopy(v, memo))
    return result

_mpath.Path.__deepcopy__ = _path_deepcopy_fix

import psycopg2
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from configuration import Configuration

db = Configuration.get_database_config()
conn = psycopg2.connect(
    dbname=db['db'], user=db['username'], password=db['password'],
    host=db['host'], port=db['port']
)

cur = conn.cursor()
cur.execute("""
    SELECT location, provider, datetime, value
    FROM meteocompare
    WHERE name = 'temperature'
    ORDER BY location, provider, datetime
""")
rows = cur.fetchall()
conn.close()

# Group by (location, provider)
data = defaultdict(lambda: ([], []))
for location, provider, dt, value in rows:
    data[(location, provider)][0].append(dt)
    data[(location, provider)][1].append(float(value))

locations = sorted({loc for loc, _ in data})

fig, axes = plt.subplots(len(locations), 1, figsize=(14, 5 * len(locations)), sharex=False)
if len(locations) == 1:
    axes = [axes]

for ax, location in zip(axes, locations):
    providers = sorted({prov for loc, prov in data if loc == location})
    legend_handles = []
    for provider in providers:
        times, values = data[(location, provider)]
        (line,) = ax.plot(times, values, linewidth=1)
        legend_handles.append(mpatches.Patch(color=line.get_color(), label=provider))

    ax.set_title(f"Temperature — {location}", fontsize=13)
    ax.set_ylabel("°C")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3)
    ax.legend(handles=legend_handles)

fig.tight_layout()
plt.show()