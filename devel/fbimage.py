#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete

import argparse, argcomplete
import logging

from devel.development import RawTextArgumentDefaultsHelpFormatter

logger = logging.getLogger('fbimage')

from PIL import Image

# fb (Micropython framebuf)binary file format:
# byte 0: width
# byte 1: height
# byte 2: format (optional)
# byte 3: reserved
# byte 4..n: pixel data

class FBImage:
    FB_FORMATS = {
        'MONO_HMSB': 4,
        'MONO_HLSB': 3,
        'RGB565': 1,
        'MONO_VLSB': 0,
        'MVLSB': 0,
        'GS2_HMSB': 5,
        'GS8': 6,
        'GS4_HMSB': 2,
    }

    INPUT_FORMATS = ['RGBA']
    OUTPUT_FORMATS = ['GS2_HMSB']

    argparser = argparse.ArgumentParser(
        prog='fbimage',
        description='DZEM HomeCtrl Devel - Utility to convert image file, to micropython framebuf binary file.',
        add_help=True, formatter_class=RawTextArgumentDefaultsHelpFormatter)
    argparser.add_argument("input", type=str, help="Input file path")
    argparser.add_argument("output", type=str, help="Path and name of output file")
    argparser.add_argument("--in-format", "-if", help="Format of input file for PIL", type=str, default="RGBA", choices=INPUT_FORMATS)
    argparser.add_argument("--out-format", "-of", help="Format of output file", type=str, default="GS2_HMSB", choices=OUTPUT_FORMATS)

    def __init__(self, args):
        self.args = args

    @classmethod
    def parse_args(cls, args=None):
        argcomplete.autocomplete(cls.argparser)
        return cls.argparser.parse_args(args)

    def export(self, infile: str, outfile: str, input_format: str, output_format: int):
        if input_format not in self.INPUT_FORMATS:
            raise ValueError(f"Unsupported input format: {input_format}. Implemented formats: {self.INPUT_FORMATS}")

        img = Image.open(infile).convert(input_format)
        w, h = img.width, img.height
        logger.info("SIZE: %d x %d" % (w, h))

        px = img.load()
        out = bytearray()

        if output_format == 'GS2_HMSB':
            for y in range(h):
                for x in range(0, w, 4):
                    byte = 0
                    for i in range(4):
                        a = px[x+i, y][3]
                        if a < 8:
                            v = 3
                        else:
                            v = 3 - (a >> 6) # antialiasing comes from alpha
                        byte |= (v & 0x03) << (2*i)      # LSB-first ✔
                    out.append(byte)
        else:
            raise ValueError(f"Unsupported output format: {output_format}. Implemented formats: {self.OUTPUT_FORMATS}")

        out = bytearray([w, h, self.FB_FORMATS[output_format], 0]) + out
        with open(outfile, "wb") as f:
            f.write(out)


    def run(self):
        self.export(self.args.input, self.args.output, self.args.in_format, self.args.out_format)
        logger.info(f"'{self.args.input}' -> '{self.args.output}'")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))
    FBImage(FBImage.parse_args()).run()

