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
    numargs.add_argument("-s", "--scale", type=float, default=1, nargs="+",
                         help="Scaling factors for the x (hor.) and y (vert.) "
                              "coordinates.")
    numargs.add_argument("-t", "--target", type=int, default=None, nargs=2,
                         help="Target mask shape (vertical, horizontal).")
    numargs.add_argument("-i", "--image", type=int, default=None, nargs=2,
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
