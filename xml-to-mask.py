#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# DESCRIPTION

"""
Author: Istvan N. Huszar, M.D. <istvan.huszar@dtc.ox.ac.uk>
Date: 9-June-2019

CLI interface script to convert XML annotations to binary image masks of a
given resolution.

"""


# DEPENDENCIES

import os
import roi
import sys
import argparse


# DEFINITIONS


# IMPLEMENTATION

def set_args(parser):
    """
    Sets up the argument dictionary for the program.

    :param parser: ArgumentParser object
    :type parser: argparse.ArgumentParser

    """
    # Compulsory arguments
    parser.add_argument("xml_file", type=str, help="Path to the XML file.")

    # Optional argument groups
    numargs = parser.add_argument_group("Numerical modulators")
    numargs.add_argument("-s", "--scale", type=float, default=[1, 1], nargs="+",
                         help="Scaling factors for the x (hor.) and y (vert.) "
                              "coordinates.")
    numargs.add_argument("-t", "--target", type=int, default=None, nargs=2,
                         help="Target mask shape (vertical, horizontal).")
    numargs.add_argument("-i", "--image", default=None, nargs="+",
                         help="Original image shape (vertical, horizontal).")
    numargs.add_argument("-c", "--fill", type=int, default=255,
                         help="Mask fill value for the ROI.")

    boolargs = parser.add_argument_group("Boolean modulators")
    boolargs.add_argument("--nodisplay", action="store_true", default=False,
                          help="Do not display ROI and binary mask.")
    boolargs.add_argument("--nocsv", action="store_true", default=False,
                          help="Do not save vertex data in CSV format.")
    boolargs.add_argument("--nobin", action="store_true", default=False,
                          help="Do not save polygonal selection object.")
    boolargs.add_argument("--nomask", help="Do not save binary ROI mask.",
                          action="store_true", default=False)
    boolargs.add_argument("-v", "--verbose", metavar="level", default=0,
                          type=int, help="Verbosity level (0-40).")

    strargs = parser.add_argument_group("String modulators")
    strargs.add_argument("--out", help="Output directory (without filename!).",
                         type=str, default=None, required=False)


def main(p):
    """ Main program code. """

    options = roi.DEFAULT_OPTIONS.copy()
    options.update({
        "original_shape": p.image,
        "scale": p.scale,
        "target_shape": p.target,
        "csv": not p.nocsv,
        "bin": not p.nobin,
        "mask": not p.nomask,
        "fill_value": p.fill,
        "display": not p.nodisplay,
        "verbose": p.verbose,
        "outdir": p.out
    })

    # Infer original image size by opening SVS file (if --image is auto or path)
    imgarg = [arg for arg in p.image if arg] if p.image else None
    if imgarg is None:
        options.update({"original_shape": None})
    elif len(imgarg) == 1:
        imgarg = str(imgarg[0])
        if os.path.isfile(imgarg):
            import openslide
            slideobj = openslide.open_slide(imgarg)
            tshape = options["target_shape"] \
                     or slideobj.level_dimensions[-1][::-1]
            options.update({
                "original_shape": slideobj.dimensions[::-1],
                "target_shape": tshape
            })
        elif imgarg.lower() == "auto":
            imgarg = os.path.splitext(p.xml_file)[0] + ".svs"
            import openslide
            slideobj = openslide.open_slide(imgarg)
            tshape = options["target_shape"] \
                     or slideobj.level_dimensions[-1][::-1]
            options.update({
                "original_shape": slideobj.dimensions[::-1],
                "target_shape": tshape
            })
        else:
            raise ValueError("Invalid string after --image flag. Expected "
                             "either 'auto' for automatic inference from "
                             "adjacent file, or the full path to the original "
                             "image file.")

    elif len(imgarg) == 2:
        options.update({"original_shape": [int(d) for d in imgarg]})
    else:
        raise ValueError("Invalid argument for original image size. Expected "
                         "two integers for (vertical, horizontal) shape "
                         "definition, or 'auto' for automatic inference from "
                         "adjacent SVS file, or path to the original image "
                         "file.")

    roi.process(p.xml_file, **options)


if __name__ == "__main__":
    """ Program execution starts here. """

    # Define argument parser
    parser = argparse.ArgumentParser(
        prog="generate_mask",
        description="Convert Aperio Image Analsys XML histology annotation "
                    "files to binary masks.")
    set_args(parser)

    # Start program or show help
    if len(sys.argv) > 1:
        main(parser.parse_args())
    else:
        parser.print_help()
