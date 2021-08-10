# Convert a Second Life snapshot's RGB 24bit depth map to a monochrome 16bit depth map
# Need to `pip install` pillow and numpy

# Copyright 2021 Salad Dais
# GPL v3

import argparse
import sys

from PIL import Image
import numpy as np


def u24_to_u16(val):
    val //= 256
    return min(65535, max(val, 0))


def convert_to_16bit_mono(img: Image.Image, range_lower: float, range_upper: float) -> Image.Image:
    # percent -> 24bit val
    lower_bound = int(0xFFffFF * range_lower)
    upper_bound = int(0xFFffFF * range_upper)
    # multiplier to saturate the full range
    multiplier = 0xFFffFF // (upper_bound - lower_bound)
    # Y, X, (R, G, B, A?)
    img_data = np.array(img.getdata()).reshape((img.size[1], img.size[0], len(img.getbands())))

    # Nothing seems to be able to open 32bit or 24bit monochrome so scale to 16bit mono range.
    # Make a new single-channel image of the same X & Y dimensions
    bw_data = np.zeros(img_data.shape[:2], dtype=np.int16)
    for y in range(img_data.shape[0]):
        for x in range(img_data.shape[1]):
            bands = img_data[y][x]
            # Each channel is one level of granularity for precision, merge them
            # all into one value, take a specific range and fit it into a 16bit int.
            mono = (bands[0] << 16) | (bands[1] << 8) | bands[2]
            bw_data[y][x] = u24_to_u16((mono - lower_bound) * multiplier)

    return Image.fromarray(bw_data, "I;16")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image_file')
    parser.add_argument('range_lower', type=float, help='0.0 - 1.0')
    parser.add_argument('range_upper', type=float, help='0.0 - 1.0')
    parser.add_argument('output_file', nargs='?')
    parser.add_argument("--show", help="show the image instead of printing it", action="store_true")
    args = parser.parse_args()

    img: Image.Image = Image.open(args.image_file)
    converted = convert_to_16bit_mono(img, args.range_lower, args.range_upper)
    if args.show:
        converted.show()
    elif args.output_file:
        converted.save(args.output_file)
    else:
        print("Must specify either --show or an output file", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
