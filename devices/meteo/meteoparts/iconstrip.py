import logging
from toolbox.framebufext import FrameBufferExtension, FrameBufferFont

logger = logging.getLogger(__name__)

class IconsStrip:

    def __init__(self, colors: Colors):
        self.colors = colors
        self.cache = {}

    def debug(self, align: int, message: str):
        logger.debug(f"{' '*2*align}{message}")
    def info(self, align: int, message: str):
        logger.info(f"{' '*2*align}{message}")

    def draw(self, fb: FrameBufferExtension, icons: list):
        logalign = 0
        self.debug(logalign, f"ICONS start drawing. Length: {len(icons)}")
        logalign += 1

        length = fb.width // len(icons)
        x0 = (length - 16) // 2
        self.debug(logalign, f"ICONS length: {length}, x0: {x0}")

        for i, icon in enumerate(icons):
            self.debug(logalign, f"ICONS {i}: {icon}")
            if icon is not None:
                if icon in self.cache.keys():
                    self.debug(logalign, f"ICONS {i}: from cache {self.cache[icon]}")
                    image = self.cache[icon]
                else:
                    image = FrameBufferExtension.fromfile(f"images/16x16/{icon}.fb")
                    self.cache[icon] = image
                    self.debug(logalign, f"ICONS {i}: new one {self.cache[icon]}")
                fb.blit(image, x0 + (i*length), 0, self.colors.WHITE)

        self.debug(logalign, f"ICONS completed.")

