#!/usr/bin/which python

import sys
import time

from peewee import SelectQuery
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io

from common.common import Common
from backend.storage import *

plt.style.use('dark_background')
pd.set_option('display.max_rows', None)


def polar_24hours(query: SelectQuery, end_date: datetime = None, headless=True):
    hours = 24
    if end_date is None:
        end_date = datetime.datetime.now()
    end_date = end_date.replace(microsecond=0)
    start_date = end_date - datetime.timedelta(hours=hours)

    df = pd.DataFrame(query.dicts())
    if not df.empty:
        # Drop milliseconds:
        df["datetime"] = pd.to_datetime(df["create_at"]).dt.floor("s")
        # Cast boolean to int:
        df["value"] = df["value"].astype(int)
        # Remove unnecessary columns:
        df.drop(columns=["id", "name", "create_at"], inplace=True)
        # Add border records:
        df = pd.concat([
            pd.DataFrame([[(df.iloc[0]["value"] + 1) % 2, start_date]], columns=df.columns),
            df,
            pd.DataFrame([[df.iloc[-1]["value"], end_date]], columns=df.columns)], ignore_index=True)
        # Remove records from the same second. Take '0's for such:
        df = df.sort_values("value", ascending=True).drop_duplicates("datetime").sort_index()
        # print(df)

        # Fill gaps for each second:
        df.set_index("datetime", inplace=True, verify_integrity=True)
        df = (df.resample(rule='s', origin=start_date)
              .ffill()
              .reset_index())

        # Trim seconds, so leave only minutes important:
        df["datetime"] = pd.to_datetime(df["datetime"]).dt.floor("min")
        # print(df)
        # Remove duplicates.
        df = df.sort_values("value", ascending=False).drop_duplicates("datetime").sort_index().reset_index()
        # print(df)

        # Make the oldest data 1/4 height and increase to 1 for end date
        df["value"] = df['value'] * (0.75 * (df.index / df.count()["value"]) + 0.25)

        # Translate timestamp seconds to radians:
        df["datetime"] = df["datetime"] - datetime.datetime.strptime('00:00:00', '%H:%M:%S')
        df["datetime"] = df["datetime"].dt.seconds / (hours * 60 * 60)
        df["datetime"] = df["datetime"] * 2 * np.pi

    # The same with end date
    chart_end_date = end_date - datetime.datetime.strptime('00:00:00', '%H:%M:%S')
    chart_end_date = chart_end_date.total_seconds() / (hours * 60 * 60)
    chart_end_date = chart_end_date * 2 * np.pi

    # Let's draw the plot
    fig = plt.figure(figsize=(8, 8), facecolor='#303030')
    ax2 = fig.subplots(1, 1, subplot_kw=dict(projection='polar'))
    ax2.set_facecolor("#303030")
    ax2.set_xticks(np.linspace(0, 2 * np.pi, hours, endpoint=False))
    ax2.set_xticklabels(range(hours))
    ax2.set_theta_direction(-1)
    ax2.set_theta_offset(np.pi / 2)

    # Negative size (radius - in practice)
    radius = -4

    ax2.tick_params(axis='x', which='major', pad=-114, labelsize=20)

    ax2.set_rlim(radius, 1.2)
    ax2.set_rgrids([0, 1])
    ax2.set_yticklabels([])
    ax2.set_rorigin(radius + 1)

    if not df.empty:
        ax2.bar(df["datetime"], df["value"], width=2 * np.pi / (hours * 30))
    ax2.bar([chart_end_date], [1], width=2 * np.pi / (hours * 30), color='r')
    ax2.plot()
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)



    # Save plot to BytesIO
    bio = io.BytesIO()
    plt.savefig(bio, format="png", facecolor=fig.get_facecolor(), edgecolor='none')

    if not headless:
        plt.show()

    # Cleanup plot
    fig.clear()
    plt.close()
    plt.cla()
    plt.clf()

    return bio


def chart_1week(query: SelectQuery, headless=True):
    df = pd.DataFrame(query.dicts())

    fig = plt.figure(figsize=(8, 4), facecolor='#303030')
    ax2 = fig.subplots(1, 1)
    ax2.set_facecolor("#303030")
    ax2.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax2.xaxis.get_major_locator()))
    ax2.plot(df["create_at"], df["value"])

    # Save plot to BytesIO
    bio = io.BytesIO()
    plt.savefig(bio, format="png", facecolor=fig.get_facecolor(), edgecolor='none')

    if not headless:
        plt.show()

    # Cleanup plot
    fig.clear()
    plt.close()
    plt.cla()
    plt.clf()

    return bio


class ChartsGenerator(Common):

    def __init__(self):
        super().__init__("CHARTS_GENERATOR")
        self.charts = Configuration.get_charts_config()
        self.exit = False

    def start(self):
        minutes5 = datetime.timedelta(minutes=5)
        minutes15 = datetime.timedelta(minutes=15)
        week1 = datetime.timedelta(weeks=1)
        day1 = datetime.timedelta(days=1)

        while not self.exit:

            for model_str, names in self.charts["24hours"]["polar"].items():
                model = getattr(sys.modules['backend.storage'], model_str)
                for name in names:
                    now = datetime.datetime.now()
                    if (last := FigureCache.get_last(model.__name__, ChartPeriod.hours24, name)) is None or last.create_at + minutes5 < now:
                        self.log("Regenerating chart: {} {} ...".format(model.__name__, name))
                        bio = polar_24hours(model.get_lasts(name, now - day1))
                        if last is None:
                            last = FigureCache(model=model.__name__, name=name, period=ChartPeriod.hours24)
                        last.create_at = now
                        last.data = bio.getvalue()
                        last.save()
                        self.log("Regenerating chart: {} {} DONE".format(model.__name__, name))

            for model_str, names in self.charts["1week"]["default"].items():
                model = getattr(sys.modules['backend.storage'], model_str)
                for name in names:
                    now = datetime.datetime.now()
                    if (last := FigureCache.get_last(model.__name__, ChartPeriod.days7, name)) is None or last.create_at + minutes15 < now:
                        self.log("Regenerating chart: {} {} ...".format(model.__name__, name))
                        bio = chart_1week(model.get_lasts(name, now - week1))
                        if last is None:
                            last = FigureCache(model=model.__name__, name=name, period=ChartPeriod.days7)
                        last.create_at = now
                        last.data = bio.getvalue()
                        last.save()
                        self.log("Regenerating chart: {} {} DONE".format(model.__name__, name))

            time.sleep(10)


if __name__ == "__main__":
    # start_date = datetime.datetime.now() - datetime.timedelta(weeks=1)
    # # chart_1week(Temperature.get_lasts("kitchen", start_date), headless=False)
    # chart_1week(Voltage.get_lasts("kitchen", start_date), headless=False)


    try:
        ChartsGenerator().start()
    except KeyboardInterrupt:
        pass


    # start_date = datetime.datetime.fromisoformat("2024-08-28T14:00:00.000000")
    # end_date = datetime.datetime.fromisoformat("2024-08-29T14:00:00.000000")
    # polar24Hours(Darkness.get_lasts("kitchen", start_date, end_date), end_date)

    # polar_24hours(Darkness.get_lasts("kitchen", datetime.datetime.now() - datetime.timedelta(days=1)), headless=False)
    # bio = polar_24hours(Presence.get_lasts("kitchen", datetime.datetime.now() - datetime.timedelta(days=1)), headless=False)
    # polar_24hours(Light.get_lasts("pantry", datetime.datetime.now() - datetime.timedelta(days=1)), headless=False)

    # open("/tmp/d.png", 'wb').write(bio.getvalue())

    # charts = Charts()
    # charts.pie_chart24(Presence, "kitchen")
