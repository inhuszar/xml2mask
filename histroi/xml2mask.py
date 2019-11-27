#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# DESCRIPTION

"""
Author: Istvan N. Huszar, M.D. <istvan.huszar@dtc.ox.ac.uk>
Date: 9-June-2019
Last update: 27-November-2019

CLI interface script to convert XML annotations to binary image masks of a
given resolution.

"""


# DEPENDENCIES

import os
import sys
import argparse
import numpy as np
from histroi import roi


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
    numargs.add_argument("--target", metavar=("<width>", "<height>"), type=int,
                         default=None, nargs=2,
                         help="Target mask shape (width, height).")
    numargs.add_argument("--image", metavar="<file>", type=str,
                         default="auto", help="Original image.")
    numargs.add_argument("--resolution", metavar="<level>", type=str,
                         default="low", help="Histology resolution "
                         "level (\"high\", \"low\" or a number)")
    numargs.add_argument("--fill", metavar="<value>", type=int, default=255,
                         help="Mask fill value for the ROI. (Default: 255)")
    numargs.add_argument("--tile", type=int, nargs=4, default=None,
                         required=False,
                         metavar=("<x>", "<y>", "<width>", "<height>"),
                         help="Export mask for a specific tile. "
                              "(The coordinates and dimensions of the tile "
                              "should be given w.r.t. the output shape.")

    boolargs = parser.add_argument_group("Boolean modulators")
    boolargs.add_argument("--display", action="store_true", default=False,
                          help="Display ROI and binary mask.")
    boolargs.add_argument("--nocsv", action="store_true", default=False,
                          help="Do not save vertex data in CSV format.")
    boolargs.add_argument("--nobin", action="store_true", default=False,
                          help="Do not save polygonal selection object.")
    boolargs.add_argument("--nomask", help="Do not save binary ROI mask.",
                          action="store_true", default=False)
    boolargs.add_argument("--histo", action="store_true", default=False,
                          help="Export the histological image or part of it "
                               "that corresponds to the generated binary mask.")
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
        "image": p.image,
        "dimlevel": 0,
        "dimscale_x": 1,
        "dimscale_y": 1,
        "original_shape": None,
        "scale": p.scale,
        "target_shape": p.target,
        "tile": None,
        "csv": not p.nocsv,
        "bin": not p.nobin,
        "mask": not p.nomask,
        "histo": p.histo,
        "fill_value": p.fill,
        "display": p.display,
        "verbose": p.verbose,
        "outdir": p.out
    })

    # Determine resolution level
    if p.resolution.lower() == "high":
        dimlevel = 0
    elif p.resolution.lower() == "low":
        dimlevel = -1
    else:
        try:
            dimlevel = int(p.resolution)
        except ValueError:
            raise ValueError("Invalid input for --resolution: {}"
                             .format(p.resolution))
    options.update({"dimlevel": dimlevel})

    # Infer original image size by opening SVS file (if --image is auto or path)
    if os.path.isfile(p.image):
        import openslide
        slideobj = openslide.open_slide(p.image)
        tshape = options["target_shape"]
        options.update({
            "original_shape": slideobj.level_dimensions[dimlevel][::-1],
            "target_shape": tshape
        })
    elif p.image.lower() == "auto":
        imgarg = os.path.splitext(p.xml_file)[0] + ".svs"
        import openslide
        slideobj = openslide.open_slide(imgarg)
        tshape = options["target_shape"]
        options.update({
            "original_shape": slideobj.level_dimensions[dimlevel][::-1],
            "target_shape": tshape
        })
    else:
        raise ValueError("Invalid string after --image flag. Expected "
                         "either 'auto' for automatic inference from "
                         "adjacent file, or the full path to the original "
                         "image file.")

    # Set resolution level scale
    dimscale_x, dimscale_y = np.divide(slideobj.level_dimensions[dimlevel],
                                       slideobj.level_dimensions[0])
    options.update({"dimscale_x": dimscale_x,
                    "dimscale_y": dimscale_y})

    # Raise error if the --tile option is specified without the --image option.
    if p.tile:
        if p.image is None:
            raise AttributeError("The --image option must be specified if the "
                                 "--tile option is used.")
        options.update({"tile": tuple(int(val) for val in p.tile)})

    # Raise error if the --histo argument was specified without the
    # --image argument.
    if p.histo:
        if p.image is None:
            raise AttributeError("The --image option must be specified if the "
                                 "--histo option is used.")

    # Obtain path to the image file
    if p.image.lower() != "auto":
        if not os.path.isfile(p.image):
            raise FileNotFoundError("Input image was not found at: {}"
                                    .format(p.image))
        else:
            options.update({"image": p.image})
    else:
        imfile = p.xml_file[:p.xml_file.lower().index(".xml")] + ".svs"
        options.update({"image": imfile})

    roi.process(p.xml_file, **options)
    if p.verbose > 0:
        print("Task complete. Check the output directory.")


def init():
    # Define argument parser
    parser = argparse.ArgumentParser(
        prog="xml2mask",
        description="Convert Aperio Image Analysis XML histology annotation "
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

