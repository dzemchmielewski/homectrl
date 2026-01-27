#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/../env/bin/python" "$0" "$@"'
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete

import argparse
import asyncio
import socket
from collections import deque

import argcomplete
import colorsys
from argcomplete.completers import ChoicesCompleter
from ping3 import ping
from rich.columns import Columns
from rich.console import Console, Group, RenderResult, ConsoleOptions, Segment
from rich.live import Live
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from rich.color import Color

try:
    from configuration import Configuration
    boards = Configuration.MAP["board"]
    ids = list(Configuration.MAP["board"].keys())
except ImportError:
    boards, ids = {}, []

try:
    from devel.development import RawTextArgumentDefaultsHelpFormatter
except ImportError:
    class RawTextArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter):
        pass

RTT_HEIGHT = 6
RTT_WIDTH = 20
RTT_COLORS = [int((120 / (2*RTT_HEIGHT)) * i) / 360 for i in range(0, 2*RTT_HEIGHT + 1)]
RTT_COLORS.reverse()
COLOR_BLACK = Color.from_rgb(0, 0, 0)
STYLE_BLACK = Style(color= COLOR_BLACK, bgcolor= COLOR_BLACK)

class PPing:

    argparser = argparse.ArgumentParser(
        prog='pping',
        description='DZEM HomeCtrl Devel - PPing - Pretty Ping tool',
        add_help=True, formatter_class=RawTextArgumentDefaultsHelpFormatter)

    argparser.add_argument("--count", "-c", type=int, help="Stop after sending count ECHO_REQUEST packets")
    argparser.add_argument(
        "server_id",
        help="Available hosts",
        nargs='+'
    ).completer = ChoicesCompleter(ids)

    @classmethod
    def parse_args(cls, args=None):
        argcomplete.autocomplete(cls.argparser)
        return cls.argparser.parse_args(args)

    def __init__(self, parsed_args):
        self.tasks = None
        self.args = parsed_args
        self.data = {}
        self.console = Console()
        for id in self.args.server_id:
            host = boards.get(id)
            if host:
                host = host['host']
            else:
                host = id

            self.data[id] = {
                'host': host,
                'status': 'unknown',
                'ip': '?',
                'values': deque(maxlen=60)
            }

    @staticmethod
    def rtt_stats(values):
        valid = [v for v in values if isinstance(v, (int, float)) and v >= 0]
        avg = sum(valid) / len(valid) if valid else None

        last = None
        for v in reversed(values):
            if isinstance(v, (int, float)) and v >= 0:
                last = v
                break
        return avg, last

    @staticmethod
    def resolve_status(values):
        n = 0
        last_error_type = 2
        for v in reversed(values):
            if v is None or v is False:
                if last_error_type == 2:
                    last_error_type = v
                    n += 1
                else:
                    if v == last_error_type:
                        n += 1
                    else:
                        break
            else:
                break

        if not values:
            return "unknown", "dim", n

        last = values[-1]
        if last is None:
            return "timeout", "yellow", n
        elif last is False:
            return "error", "red", n
        return "up", "green", n

    @staticmethod
    def loss_pct(values):
        if not values:
            return 0.0
        lost = sum(1 for v in values if v is None)
        return 100.0 * lost / len(values)

    def render(self):
        panels = []
        for name, d in self.data.items():
            values = d["values"]
            status, style, streak = PPing.resolve_status(values)
            if status in ("timeout", "error") and streak > 0:
                status = f"{status}×{streak}" if streak < 60 else f"{status} ⤫"
            avg, last = PPing.rtt_stats(values)

            loss = PPing.loss_pct(values)
            loss_style = Style(color=RTTColorPlot.hue_to_color((100-loss)/360) if loss is not None else 'red')

            stat =  (f"{last:.0f}/{avg:.0f}" if last is not None else "—") + "_" +  f" {loss:.0f}%".rjust(4)
            stat = stat.replace("_", " " * (RTT_WIDTH - len(stat) + 1))
            panels.append(Panel.fit(
                Group(
                    RTTColorPlot(values),
                    Text(name, justify="center"),
                    Text(f"IP: {d['ip']}", style="dim", justify="center"),
                    Text(status, style=style, justify="center"),
                    Text("RTT last/avg" + (" " * (RTT_WIDTH - 16)) + "Loss", style="blue bold", justify="right"),
                    Text("─" * RTT_WIDTH, justify="center"),
                    Text( stat, style=loss_style),
                ),
                width=RTT_WIDTH + 4,  border_style=style))
        return Columns(
            panels,
            width=RTT_WIDTH + 5,
            equal=True,
            expand=False,
        )

    async def display(self):
        with Live(console=self.console, refresh_per_second=2) as live:
            while True:
                live.update(self.render())
                await asyncio.sleep(0.3)

    @staticmethod
    def ping_safe(host):
        """
           Returns:
           float | None | False: The delay in milliseconds, False on error and None on timeout.
        """
        try:
            return ping(host, timeout=1, unit="ms")
        except Exception:
            return None

    async def ping_loop(self, id):
        host = self.data[id]["host"]
        while True:
            delay = await asyncio.to_thread(PPing.ping_safe, host)
            self.data[id]["status"] = "error" if delay is None else ("timeout" if delay is False else "up")
            self.data[id]["values"].append(delay)
            await asyncio.sleep(1)

    async def getip(self, id):
        host = self.data[id]["host"]
        try:
            ip = await asyncio.to_thread(socket.gethostbyname, host)
        except Exception:
            ip = "-"
        self.data[id]["ip"] = ip


    async def main(self):
        self.tasks = [asyncio.create_task(self.ping_loop(id)) for id in self.data.keys()]
        self.tasks = [asyncio.create_task(self.getip(id)) for id in self.data.keys()]
        self.tasks.append(asyncio.create_task(self.display()))
        await asyncio.gather(*self.tasks)

    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            [task.cancel() for task in self.tasks]

class RTTColorPlot:

    def __init__(self, values: list[float]) -> None:
        # The value > 200 is mapped to the highest row (2*RTT_HEIGHT - 1)
        # Te values between 0 and 200 are mapped linearly to range 0..(2*RTT_HEIGHT - 1)
        self.level = [RTTColorPlot.getlevel(x) for x in list(values)[ -RTT_WIDTH:]]

    @staticmethod
    def getlevel(x: float) -> int | None | bool:
        if x is not None and x is not False:
            return min(int((x / 200) * (2 * RTT_HEIGHT - 1)), 2 * RTT_HEIGHT - 1)
        return x

    @staticmethod
    def hue_to_color(hue: float) -> Color:
        r, g, b = colorsys.hls_to_rgb(hue, 0.4, 1) if hue is not None else (0, 0, 0)
        return Color.from_rgb(r * 255, g * 255, b * 255)

    def empty_segment(self, length: int = 1) -> RenderResult:
        return Segment("▄" * length, STYLE_BLACK)

    def __rich_console__(
            self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        pad = RTT_WIDTH - len(self.level)
        for y in range(RTT_HEIGHT -1, -1, -1):
            if pad > 0:
                yield self.empty_segment(pad)
            for x in range(len(self.level)):
                lvl = self.level[x]
                if lvl is None:
                    yield Segment("𜱀", Style(color='orange4', bgcolor=COLOR_BLACK))
                elif lvl is False:
                    if y == 0:
                        yield Segment("✘", Style(color='red', bgcolor=COLOR_BLACK))
                    else:
                        yield self.empty_segment()
                else:
                    if lvl >= 2 * y + 1:
                        fg, bg = RTT_COLORS[2*y], RTT_COLORS[2*y + 1]
                    elif lvl == 2 * y:
                        fg, bg = RTT_COLORS[2*y], None
                    else:
                        fg, bg = None, None

                    yield Segment("▄", Style(color=self.hue_to_color(fg), bgcolor=self.hue_to_color(bg)))
            yield Segment.line()


if __name__ == "__main__":
    PPing(PPing.parse_args()).run()
