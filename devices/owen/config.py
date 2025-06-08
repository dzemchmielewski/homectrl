from micropython import const
import logging

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))
# logging.getLogger('touch').setLevel(logging.INFO)
# logging.getLogger('thermometer').setLevel(logging.INFO)
# logging.getLogger('BuzzPlay').setLevel(logging.IFO)
# logging.getLogger('timer').setLevel(logging.INFO)
# logging.getLogger('display').setLevel(logging.INFO)
logging.getLogger('owen-ws').setLevel(logging.DEBUG)
logging.getLogger('mqtt').setLevel(logging.DEBUG)

SCREEN_DIM_TIME = const(3*60)
# SCREEN_DIM_TIME = const(15)
ALARM_TIMEOUT = const(5*60)
DEFAULT_TIMER_VALUE = (0, 5, 0)
SILENT_ALARM = False

def rgb888_to_rgb565(r, g, b):
    r5 = (r * 31) // 255
    g6 = (g * 63) // 255
    b5 = (b * 31) // 255
    return (r5 << 11) | (g6 << 5) | b5
# rgb565=rgb888_to_rgb565(0, 255, 0)
# print(f"RGB565: {rgb565:#06x}")

IMG_BACKGROUND = const('images/background.jpg')

CFG_IMAGE = const('image')
CFG_IMAGE_ACTIVE = const('image-active')
CFG_IMAGE_INACTIVE = const('image-inactive')
CFG_DEFAULT_LABEL = const('label')
CFG_NAME = const('name')
CFG_CLASS = const('class')
CFG_X = const('x')
CFG_Y = const('y')
CFG_WIDTH = const('width')
CFG_HEIGHT = const('height')
CFG_TOUCH_X = const('touch_x')
CFG_TOUCH_Y = const('touch_y')
CFG_TOUCH_WIDTH = const('touch_width')
CFG_TOUCH_HEIGHT = const('touch_height')
CFG_EVENT_RECIPIENT = const('event-recipient')

PARTS = [
    {
        CFG_CLASS: 'Clickable',
        CFG_NAME: const('btn-hour'),
        CFG_TOUCH_X: const(20),
        CFG_TOUCH_Y: const(172),
        CFG_TOUCH_WIDTH: const(32),
        CFG_TOUCH_HEIGHT: const(49),
        CFG_EVENT_RECIPIENT: 'timer'
    },
    {
        CFG_CLASS: 'Clickable',
        CFG_NAME: const('btn-min'),
        CFG_TOUCH_X: const(20+32),
        CFG_TOUCH_Y: const(172),
        CFG_TOUCH_WIDTH: const(32),
        CFG_TOUCH_HEIGHT: const(49),
        CFG_EVENT_RECIPIENT: 'timer'
    },
    {
        CFG_CLASS: 'Clickable',
        CFG_NAME: const('btn-sec'),
        CFG_TOUCH_X: const(20+2*32),
        CFG_TOUCH_Y: const(172),
        CFG_TOUCH_WIDTH: const(32),
        CFG_TOUCH_HEIGHT: const(49),
        CFG_EVENT_RECIPIENT: 'timer'
    },
    {
        CFG_CLASS: 'SetButtonDisplay',
        CFG_IMAGE: {
            'empty': const('images/slider-empty.jpg'),
            'hour': const('images/slider-left.jpg'),
            'min': const('images/slider-middle.jpg'),
            'sec': const('images/slider-right.jpg'),
        },
        CFG_DEFAULT_LABEL: const('empty'),
        CFG_NAME: const('dis-set'),
        CFG_X: const(20),
        CFG_Y: const(173),
        CFG_WIDTH: const(95),
        CFG_HEIGHT: const(48),
    },
    {
        CFG_CLASS: 'ModeButton',
        CFG_IMAGE: {
            'timer': const('images/slider-timer.jpg'),
            'stopwatch': const('images/slider-stopwatch.jpg'),
        },
        CFG_DEFAULT_LABEL: const('timer'),
        CFG_NAME: const('btn-mode'),
        CFG_X: const(33),
        CFG_Y: const(269),
        CFG_WIDTH: const(80),
        CFG_HEIGHT: const(25),
        CFG_EVENT_RECIPIENT: 'timer'
    },
    {
        CFG_CLASS: 'Button',
        CFG_IMAGE: {
            'default': [const('images/btn-down-active.jpg'), const('images/btn-down-inactive.jpg')]
        },
        CFG_DEFAULT_LABEL: const('default'),
        CFG_NAME: const('btn-down'),
        CFG_X: const(128),
        CFG_Y: const(228),
        CFG_WIDTH: const(31),
        CFG_HEIGHT: const(31),
        CFG_TOUCH_X: const(118),
        CFG_TOUCH_Y: const(218),
        CFG_TOUCH_WIDTH: const(50),
        CFG_TOUCH_HEIGHT: const(48),
        CFG_EVENT_RECIPIENT: 'timer'
    },
    {
        CFG_CLASS: 'Button',
        CFG_IMAGE: {
            'default': [const('images/btn-up-active.jpg'), const('images/btn-up-inactive.jpg')]
        },
        CFG_DEFAULT_LABEL: const('default'),
        CFG_NAME: const('btn-up'),
        CFG_X: const(177),
        CFG_Y: const(228),
        CFG_WIDTH: const(31),
        CFG_HEIGHT: const(31),
        CFG_TOUCH_X: const(168),
        CFG_TOUCH_Y: const(218),
        CFG_TOUCH_WIDTH: const(50),
        CFG_TOUCH_HEIGHT: const(48),
        CFG_EVENT_RECIPIENT: 'timer'
    },
    {
        CFG_CLASS: 'Button',
        CFG_IMAGE: {
            'default': [const('images/btn-reset-active.jpg'), const('images/btn-reset-inactive.jpg')]
        },
        CFG_DEFAULT_LABEL: const('default'),
        CFG_NAME: const('btn-reset'),
        CFG_X: const(146),
        CFG_Y: const(268),
        CFG_WIDTH: const(45),
        CFG_HEIGHT: const(29),
        CFG_TOUCH_X: const(137),
        CFG_TOUCH_Y: const(267),
        CFG_TOUCH_WIDTH: const(66),
        CFG_TOUCH_HEIGHT: const(32),
        CFG_EVENT_RECIPIENT: 'timer'
    },
    {
        CFG_CLASS: 'Button',
        CFG_IMAGE: {
            'start': [const('images/btn-start-active.jpg'), const('images/btn-start-inactive.jpg')],
            'stop': [const('images/btn-stop-active.jpg'), const('images/btn-stop-inactive.jpg')],
        },
        CFG_DEFAULT_LABEL: const('start'),
        CFG_NAME: const('btn-start'),
        CFG_X: const(120),
        CFG_Y: const(177),
        CFG_WIDTH: const(96),
        CFG_HEIGHT: const(35),
        CFG_TOUCH_X: const(119),
        CFG_TOUCH_Y: const(173),
        CFG_TOUCH_WIDTH: const(100),
        CFG_TOUCH_HEIGHT: const(45),
        CFG_EVENT_RECIPIENT: 'timer'
    },
    {
        CFG_CLASS: 'TemperatureDisplay',
        CFG_IMAGE: const('images/digits-big.jpg'),
        CFG_NAME: const('dis-temp'),
        CFG_X: const(69),
        CFG_Y: const(70),
        CFG_WIDTH: const(29),
        CFG_HEIGHT: const(42)
    },
    {
        CFG_CLASS: 'TimerDisplay',
        CFG_IMAGE: const('images/digits-small.jpg'),
        CFG_NAME: const('dis-timer'),
        CFG_X: const(32),
        CFG_Y: const(237),
        CFG_WIDTH: const(11),
        CFG_HEIGHT: const(16),
        'image-dots': const('images/digits-small-dots.jpg'),
    }
]


