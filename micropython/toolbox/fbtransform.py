from toolbox.framebufext import FrameBufferExtension


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
