import copy
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import sys

# Workaround: matplotlib Path.__deepcopy__ recurses infinitely on Python 3.14
# because copy.deepcopy(super(), memo) changed behaviour. Replace with a
# direct copy that reconstructs the object from its own attributes.
def _path_deepcopy(self, memo=None):
    cls = type(self)
    p = cls.__new__(cls)
    memo = memo or {}
    memo[id(self)] = p
    p.__dict__.update({k: copy.deepcopy(v, memo) for k, v in self.__dict__.items()})
    return p

mpath.Path.__deepcopy__ = _path_deepcopy

csv_file = sys.argv[1] if len(sys.argv) > 1 else 'devices/coffee/shaker.csv'

df = pd.read_csv(csv_file)
df['interval_ms'] = df['ticks_ms'].diff()

fig, axes = plt.subplots(3, 1, figsize=(14, 10), constrained_layout=True)
fig.suptitle(f'Shaker intervals — {csv_file}')

# Raw signal
axes[0].step(df['ticks_ms'], df['value'], where='post', linewidth=0.8)
axes[0].set_ylabel('Pin value')
axes[0].set_xlabel('ticks_ms')
axes[0].set_title('Raw signal')

# Interval between consecutive transitions
intervals = df['interval_ms'].dropna()
axes[1].plot(df['ticks_ms'].iloc[1:], intervals, marker='.', markersize=3, linewidth=0.6)
axes[1].set_ylabel('Interval (ms)')
axes[1].set_xlabel('ticks_ms')
axes[1].set_title('Interval between consecutive transitions')

# Histogram of intervals (log-scaled y to see both short bounces and long gaps)
axes[2].hist(intervals, bins=100, log=True)
axes[2].set_xlabel('Interval (ms)')
axes[2].set_ylabel('Count (log)')
axes[2].set_title('Interval histogram')

plt.show()