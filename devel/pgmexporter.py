import logging

import framebuf
from toolbox.framebufext import FrameBufferExtension

log = logging.getLogger(__name__)

class PGMExporter:
    def __init__(self, filename):
        self.filename = filename

    def export_fbext(self, fb: FrameBufferExtension):
        with open(self.filename, 'w') as f:
            if fb.mode == framebuf.MONO_HMSB:
                self.write_mono_hmsb(f, fb)
            elif fb.mode == framebuf.MONO_HLSB:
                self.write_mono_hlsb(f, fb)
            elif fb.mode == framebuf.MONO_VLSB:
                self.write_mono_vlsb(f, fb)
            elif fb.mode == framebuf.GS2_HMSB:
                self.write_gs2_hmsb(f, fb)
            else :
                raise ValueError(f"Unsupported framebuffer mode: {fb.mode}")
        log.info(f"Written PGM file: {self.filename}")

    def export_fb(self, fb: framebuf.FrameBuffer, width: int, height: int, mode: int):
        fbext = FrameBufferExtension(width, height, mode)
        fbext.blit(fb, 0, 0)
        self.export_fbext(fbext)

    @staticmethod
    def write_mono_hlsb(f, fb: "FrameBufferExtension"):
        """Save 1bpp MONO_HLSB framebuffer to PGM (P2, maxval=1)"""
        f.write(f"P2\n{fb.width} {fb.height}\n1\n")
        row_bytes = (fb.width + 7) // 8

        for y in range(fb.height):
            row = ""
            for x in range(fb.width):
                byte = fb.buffer[y * row_bytes + (x // 8)]
                # NOTE: MicroPython framebuf stores 1bpp HLSB with the leftmost pixel
                # in the **most significant bit** of the byte, despite the "HLSB" name.
                # This is opposite to the theoretical least-significant-bit-first layout.
                # To get correct left-to-right pixel order in the output PGM, we reverse
                # the bit index using (7 - (x % 8)).
                bit = 7 - (x % 8)
                pixel = "1" if (byte >> bit) & 1 else "0"
                row += pixel + " "
            f.write(row + "\n")


    @staticmethod
    def write_mono_hmsb(f, fb: "FrameBufferExtension"):
        """Save 1bpp MONO_HMSB framebuffer to PGM (P2, maxval=1)"""
        f.write(f"P2\n{fb.width} {fb.height}\n1\n")
        row_bytes = (fb.width + 7) // 8

        for y in range(fb.height):
            row = ""
            for x in range(fb.width):
                byte = fb.buffer[y * row_bytes + (x // 8)]
                # For HMSB, MicroPython actually stores pixels in MSB-first order, which
                # matches the theoretical expectation. We still reverse the bit index
                # the same way to ensure correct left-to-right output in PGM.
                bit = 7 - (x % 8)
                # Use LSB first, if image is 'mirrored':
                # bit = x % 8  # LSB first
                pixel = "1" if (byte >> bit) & 1 else "0"
                row += pixel + " "
            f.write(row + "\n")

    @staticmethod
    def write_mono_vlsb(f, fb: "FrameBufferExtension"):
        """Save 1bpp MONO_VLSB framebuffer to PGM (P2, maxval=1)

        MicroPython's MONO_VLSB packs pixels **vertically** in bytes:
          - Each byte covers 8 vertical pixels in a single column.
          - Bit 0 = topmost pixel, bit 7 = bottom pixel.
          - Columns are stored left-to-right, then next 8-pixel vertical block.

        This function converts that layout into a normal row-major PGM.
        """
        f.write(f"P2\n{fb.width} {fb.height}\n1\n")
        row_bytes = (fb.height + 7) // 8  # number of vertical 8-pixel blocks per column

        for y in range(fb.height):
            row = ""
            for x in range(fb.width):
                # Each byte contains 8 vertical pixels; determine which byte and bit
                byte_index = (x * row_bytes) + (y // 8)
                bit = y % 8  # LSB = top pixel
                byte = fb.buffer[byte_index]
                pixel = "1" if (byte >> bit) & 1 else "0"
                row += pixel + " "
            f.write(row + "\n")

    @staticmethod
    def write_gs2_hmsb(f, fb: FrameBufferExtension):
        f.write(f"P2\n{fb.width} {fb.height}\n3\n")
        row_bytes = (fb.width + 3) // 4

        for y in range(fb.height):
            row = ""
            for x in range(fb.width):
                byte = fb.buffer[y * row_bytes + (x // 4)]
                # NOTE: Although the mode is named GS2_HMSB, MicroPython's framebuf
                # stores 2-bit pixels LSB-first inside each byte (pixel 0 in bits 1–0).
                # Using the "theoretical" HMSB layout:
                #     (3 - (x % 4)) * 2
                # produces a mirrored image. The expression below matches the actual
                # in-memory layout used by framebuf.
                shift = (x % 4) * 2
                pixel_value = (byte >> shift) & 0x03
                row += str(pixel_value) + " "
            f.write(row + "\n")