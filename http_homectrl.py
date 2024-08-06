import io
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.responses import Response
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.figure import Figure

from storage import Temperature

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

app = FastAPI()


def log(msg):
    print("--------> {}".format(msg))

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get(
    "/image",
    responses = {
        200: {
            "content": {"image/png": {}}
        }
    },
    response_class=Response)
def get_image():

    temps = Temperature.get_lasts("KITCHEN", datetime.now() - timedelta(days=7))

    timestamps = [t.create_at for t in temps]
    values = [t.value for t in temps]

    # timestamps = [1,2,3,4,5,6,7,8,9,10]
    # values = [1,2,3,3,3,2,2,1,0,4]



    try:
        # matplotlib.use('agg')

        ax: Axis
        fig, ax = plt.subplots()
        ax.plot(timestamps, values)

        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.title('Graph')

        ax.set_title('Time', loc='left', y=0.85, x=0.02, fontsize='medium')
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))

        ax.xaxis: Axis
        ax.yaxis: Axis

        log(ax.yaxis.get_minor_locator())

        for label in ax.get_xticklabels(which='major'):
            label.set(rotation=30, horizontalalignment='right')

        # Save plot to BytesIO
        bio = io.BytesIO()
        plt.savefig(bio, format="png")

        plt.show()

        # Cleanup plot
        plt.close(plt.gcf())
        plt.clf()

        return Response(content=bio.getvalue(), media_type="image/png")

    except BaseException as e:
        print(e)
        raise e


if __name__ == "__main__":
    # get_image()

    temps = Temperature.get_lasts("KITCHEN", datetime.now() - timedelta(days=1))

    timestamps = [t.create_at for t in temps]
    values = [t.value for t in temps]


    # matplotlib.use('agg')

    fig, ax = plt.subplots()

    #plt.xlabel('Time')
    #plt.ylabel('Value')
    #plt.title('Graph')
    #plt.grid(visible=True, linestyle='--')

    ax.set_title('Home Temperatures')

    #ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))

    ax: Axes

    for label in ax.get_xticklabels(which='major'):
        label.set(rotation=30, horizontalalignment='right')
    ax.xaxis.set_label("Time")
    ax.yaxis.set_label("Temperature")
    ax.grid(visible=True, linestyle='--')

    ax.plot(timestamps, values)

    fig:Figure
    fig.show()

    #plt.show()
