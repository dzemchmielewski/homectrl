from toolbox.framebufext import FrameBufferExtension
import framebuf as _framebuf

def _rotate270_mono_hlsb(src, dst, invert=False):
    sw, sh = src.width, src.height          # e.g. 296, 128
    ss = sw >> 3                             # src stride in bytes = 37
    ds = sh >> 3                             # dst stride in bytes = 16

    for y in range(sh):
        mask  = 1 << (7 - (y & 7))
        clear = (~mask) & 0xFF
        dcb   = y >> 3
        roff  = y * ss

        for cx in range(ss):
            b = src.buffer[roff + cx]
            if invert:
                b = (~b) & 0xFF
            base = (sw - 1 - (cx << 3)) * ds + dcb   # dst offset for x = cx*8

            # 8 bits unrolled — no inner loop
            if b & 0x80: dst.buffer[base] |= mask
            else: dst.buffer[base] &= clear
            base -= ds
            if b & 0x40: dst.buffer[base] |= mask
            else: dst.buffer[base] &= clear
            base -= ds
            if b & 0x20: dst.buffer[base] |= mask
            else: dst.buffer[base] &= clear
            base -= ds
            if b & 0x10: dst.buffer[base] |= mask
            else: dst.buffer[base] &= clear
            base -= ds
            if b & 0x08: dst.buffer[base] |= mask
            else: dst.buffer[base] &= clear
            base -= ds
            if b & 0x04: dst.buffer[base] |= mask
            else: dst.buffer[base] &= clear
            base -= ds
            if b & 0x02: dst.buffer[base] |= mask
            else: dst.buffer[base] &= clear
            base -= ds
            if b & 0x01: dst.buffer[base] |= mask
            else: dst.buffer[base] &= clear

def rotate(angle: int, src: FrameBufferExtension, dest: FrameBufferExtension = None) -> FrameBufferExtension:
    if angle not in (90, 180, 270):
        raise ValueError("Angle must be one of [90, 180, 270]")
    if angle in (90, 270) and (dest is None or dest.width != src.height or dest.height != src.width):
        raise ValueError("Destination framebuffer must be provided and have dimensions swapped for 90 and 270 degree rotations")
    if angle == 180:
        if dest is None:
            if src.width != src.height:
                raise ValueError("Source framebuffer must be square for 180 degree rotation if destination is not provided")
        elif dest.width != src.width or dest.height != src.height:
            raise ValueError("Destination framebuffer must have the same dimensions for 180 degree rotation")

    if angle == 270 and src.mode == _framebuf.MONO_HLSB:
        dest.fill(0)         # clear first since we OR bits in
        _rotate270_mono_hlsb(src, dest)
        return dest

    if angle == 90:
        for x in range(src.width):
            for y in range(src.height):
                dest.pixel(dest.width - 1 - y, x, src.pixel(x, y))
    elif angle == 180:
        for x in range(src.width):
            for y in range(src.height):
                dest.pixel(dest.width - 1 - x, dest.height - 1 - y, src.pixel(x, y))
    elif angle == 270:
        for x in range(src.width):
            for y in range(src.height):
                dest.pixel(y, dest.height - 1 - x, src.pixel(x, y))
    else:
        raise ValueError("Angle must be one of [90, 180, 270]")
    return dest

def resize(src: FrameBufferExtension, dest: FrameBufferExtension) -> FrameBufferExtension:
    dest_width = min(src.width, dest.width)
    dest_height = min(src.height, dest.height)
    for x in range(dest_width):
        for y in range(dest_height):
            dest.pixel(x, y, src.pixel(x, y))
    return dest
