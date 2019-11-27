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
import sys
from . import roi
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
    numargs.add_argument("--scale", metavar=("<x>", "<y>"), type=float,
                         default=[1, 1], nargs="+",
                         help="Scaling factors for the x (hor.) and y (vert.) "
                              "coordinates.")
    numargs.add_argument("--target", metavar=("<height>", "<width>"), type=int,
                         default=None, nargs=2,
                         help="Target mask shape (vertical, horizontal).")
    numargs.add_argument("--image", metavar=("<file>/\"auto\"/<x>", "<y>"),
                         default=None, nargs="+",
                         help="Original image shape (vertical, horizontal).")
    numargs.add_argument("--fill", metavar="<value>", type=int, default=255,
                         help="Mask fill value for the ROI. (Default: 255)")
    numargs.add_argument("--tile", type=int, nargs=4, default=None,
                         required=False, metavar=("<x>", "<y>", "<width>",
                                                  "<height>"),
                         help="Export mask for a specific (scaled) tile. "
                              "The --image option must also be specified.")

    boolargs = parser.add_argument_group("Boolean modulators")
    boolargs.add_argument("--display", action="store_true", default=False,
                          help="Display ROI and binary mask.")
    boolargs.add_argument("--nocsv", action="store_true", default=False,
                          help="Do not save vertex data in CSV format.")
    boolargs.add_argument("--nobin", action="store_true", default=False,
                          help="Do not save polygonal selection object.")
    boolargs.add_argument("--nomask", help="Do not save binary ROI mask.",
                          action="store_true", default=False)
    boolargs.add_argument("--verbose", metavar="<level>", default=40,
                          type=int, help="Verbosity level (0-40, default: 40).")

    strargs = parser.add_argument_group("String modulators")
    strargs.add_argument("--out", metavar="<outdir>", type=str, default=None,
                         required=False,
                         help="Alternative output directory " \
                              "(without filename!). Default: " \
                              "directory of the input file.")


def main(p):
    """ Main program code. """

    options = roi.DEFAULT_OPTIONS.copy()
    options.update({
        "original_shape": p.image,
        "scale": p.scale,
        "target_shape": p.target,
        "tile": None,
        "csv": not p.nocsv,
        "bin": not p.nobin,
        "mask": not p.nomask,
        "fill_value": p.fill,
        "display": p.display,
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
            dimlevel = 0 if p.tile else -1
            tshape = options["target_shape"] \
                     or slideobj.level_dimensions[dimlevel][::-1]
            options.update({
                "original_shape": slideobj.dimensions[::-1],
                "target_shape": tshape
            })
        elif imgarg.lower() == "auto":
            imgarg = os.path.splitext(p.xml_file)[0] + ".svs"
            import openslide
            slideobj = openslide.open_slide(imgarg)
            dimlevel = 0 if p.tile else -1
            tshape = options["target_shape"] \
                     or slideobj.level_dimensions[dimlevel][::-1]
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

    if p.tile:
        if p.image is None:
            raise AttributeError("The --image option must be specified if the "
                                 "--tile option is used.")
        options.update({"tile": tuple(int(val) for val in p.tile)})

    roi.process(p.xml_file, **options)
    if p.verbose > 0:
        print("Task complete. Check the output directory.")


def init():
    # Define argument parser
    parser = argparse.ArgumentParser(
        prog="xml2mask",
        description="Convert Aperio Image Analsys XML histology annotation "
                    "files to binary masks.")
    set_args(parser)

    # Start program or show help
    if len(sys.argv) > 1:
        main(parser.parse_args())
    else:
        parser.print_help()


if __name__ == "__main__":
    """ Program execution starts here. """
    init()

