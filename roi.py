#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# DESCRIPTION

"""

Author: Istvan N. Huszar, M.D. <istvan.huszar@dtc.ox.ac.uk>
Date: 9-June-2019

This module implements allows the extraction of histology slide annotations
from XML files generated by the proprietary Aperio Image Analysis program.

In brief, the following functions are provided by the module:

    get_resolution      |   returns the um/px resolution of the histology image
    parse_xml           |   creates relational database of annotations
    load_tables         |   loads the tables of the relational database
    create_poygons      |   converts annotations to Polygon objects
    create_selection    |   creates selection by adding and subtracting polygons
    create_mask         |   creates binary mask from polygonal selection

"""


# DEPENDENCIES

import matplotlib
matplotlib.use("tkagg")
import matplotlib.pyplot as plt

import os
import sys
import dill
import shutil
import logging
import tempfile
import numpy as np
import pandas as pd
from PIL import Image
from functools import reduce
from attrdict import AttrMap
from collections import namedtuple
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon
from shapely.ops import cascaded_union
from skimage.draw import polygon as draw_polygon


# DEFINITIONS

# Object-like equivalent of the XML Annotation group
Annotation = namedtuple(
    "Annotation", ["Id", "Name", "ReadOnly", "NameReadOnly",
                   "LineColorReadOnly", "Incremental", "Type", "LineColor",
                   "Visible", "Selected", "MarkupImagePath", "MacroName"])

# Object-like equivalent of the XML Region group
Region = namedtuple(
    "Region", ["Id", "Type", "Zoom", "Selected", "ImageLocation", "ImageFocus",
               "Length", "Area", "LengthMicrons", "AreaMicrons", "Text",
               "NegativeROA", "InputRegionId", "Analyze", "DisplayId"])

# Default options for main program and binary mask creation
DEFAULT_OPTIONS = {
    "original_shape": None,
    "scale": 0.15,
    "target_shape": None,
    "csv": False,
    "bin": True,
    "mask": True,
    "fill_value": 255,
    "display": True,
    "verbose": 0,
    "outdir": None
}


# IMPLEMENTATION

def process(xmlfile, *xmlfiles, **options):
    """
    Main program code.

        1. Load XML file.
        2. Export structured annotation data from XML to relational database.
        3. Save database tables as CSV files.
        4. Create polygons from the annotations.
        5. Create polygonal selection by adding and subtracting polygons.
        6. Save polygonal selection as a binary object.
        7. Create binary mask at the specified resolution with the specified
           field-of-view (FOV) from the polygonal selection.
        8. Export binary mask (values: 0-255) to an 8-bit TIFF file.
        +1 (optional): display polygonal selection and binary mask.

    """
    p = AttrMap(options)

    # Start logging
    global logger
    temp_logfile = tempfile.mkstemp()
    logging.basicConfig(format='[%(asctime)s] %(message)s',
                        datefmt='%d-%m-%Y %H:%M:%S',
                        filename=temp_logfile[1],
                        filemode="w")
    logger = logging.getLogger("roi")
    logger.setLevel(max(50 - p.verbose, 1))
    logger.critical("The program started with the command: {}"
                .format(" ".join(sys.argv)))

    xmlfiles = (xmlfile,) + xmlfiles
    err = 0
    for f in xmlfiles:
        try:
            # Parse data in XML file and create data tables
            logger.info("{}".format(f))
            if not str(f).lower().endswith(".xml"):
                logger.warning("Input does not appear to be an XML file.")
            points, regions, annotations = parse_xml(f)

            # Create output base name
            p.basename = os.path.splitext(os.path.split(f)[-1])[0]
            if p.outdir:
                if not os.path.isdir(p.outdir):
                    os.makedirs(p.outdir)
                p.outbase = os.path.join(p.outdir, p.basename)
            else:
                p.outbase = os.path.splitext(f)[0]

            # Save the tables of the relational database
            if p.csv:
                points.to_csv(p.outbase + "_points.csv")
                regions.to_csv(p.outbase + "_regions.csv")
                annotations.to_csv(p.outbase + "_annotations.csv")

            # Retrieve polygons
            polygons = create_polygons(points)

            # Treat annotation layers separately
            for layer in annotations.index.unique():
                layerdir = p.outdir or os.path.split(f)[0]
                layerdir = os.path.join(
                    layerdir, "AnnotationLayer_{0:02d}".format(layer))
                if not os.path.isdir(layerdir):
                    os.makedirs(layerdir)
                layerbase = os.path.join(layerdir, p.basename)

                # Set algebra
                selection = create_selection(polygons, regions, layer=layer)
                if selection is None:
                    logger.warning("Annotation layer {} does not have any "
                                   "polygonal selections.".format(layer))
                    continue

                # Display selection
                if p.display:
                    visualise_polygon(selection, show=True, save=False)

                # Export the polygonal selection object to a binary file
                if p.bin:
                    with open(layerbase + "_selection.obj", "wb") as fp:
                        dill.dump(selection, fp)

                # Generate binary mask
                if p.mask:
                    if len(p.scale) == 1:
                        scale_x, scale_y = p.scale * 2  # p.scale is a tuple!
                    elif len(p.scale) == 2:
                        scale_x, scale_y = p.scale  # p.scale is a tuple!
                    else:
                        raise ValueError(
                            "The number of scaling factors must be 2.")
                    mask = create_mask(
                        selection, original_shape=p.original_shape,
                        target_shape=p.target_shape, scale_x=scale_x,
                        scale_y=scale_y, fill_value=p.fill_value)
                    # Display binary mask
                    if p.display:
                        plt.imshow(mask, cmap="gray", aspect="equal")
                        plt.show()
                    # Save binary mask
                    Image.fromarray(mask).save(
                        os.path.join(layerbase + "_mask.tif"))
        except Exception as exc:
            logger.critical("FAILURE: {}. Exception: {}".format(f, exc.args[0]))
            err += 1
            continue

    # Conclude run
    if err == 0:
        logger.critical("All tasks were successfully completed.")
    else:
        logger.critical("Tasks were completed with {} error(s).".format(err))

    # Save logs
    try:
        shutil.copy(temp_logfile[1], p.outbase + ".log")
    except PermissionError:
        pass


def get_resolution(xmlfile):
    """
    Returns the um/px resolution of the annotated histology image.

    :param xmlfile: path to the annotation file (.xml)
    :type xmlfile: str

    :returns: isotropic resolution of the histology image (um/px)
    :rtype: float

    """
    tree = ET.parse(xmlfile)
    root = tree.getroot()
    return float(root.get("MicronsPerPixel"))


def parse_xml(xmlfile):
    """
    Converts the hierarchical Vertex, Region, and Annotation tags of the XML
    file to a relational database. The database comprises three tables. The
    Points table links the X and Y coordinates of the vertices to the
    corresponding region and annotation tags using their IDs as shared keys.
    The properties of the Regions and Annotations are stored in their
    respective tables. Each Region is linked to an Annotation using the
    Annotation_ID as a shared key. The tables are Pandas DataFrames.

    :param xmlfile: path to the annotation file (.xml)
    :type xmlfile: str

    :returns:
        The Points, Regions, and Annotations tables of the relational database.
    :rtype: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]

    """
    tree = ET.parse(xmlfile)
    points = pd.DataFrame(columns=["Annotation", "Region", "X", "Y", "Z"])
    annotations = pd.DataFrame(columns=Annotation._fields)
    regions = pd.DataFrame(columns=["Annotation", *Region._fields])

    for a_no, annotation in enumerate(tree.getiterator("Annotation")):
        logger.info("\tAnnotation {}".format(a_no))
        annotations = annotations.append(
            dict(annotation.items()), ignore_index=True)
        for r_no, region in enumerate(annotation.getiterator("Region")):
            props = dict(region.items())
            props.update({"Annotation": a_no})
            regions = regions.append(props, ignore_index=True)
            vertices = []
            for vertex in region.getiterator("Vertex"):
                v = dict(vertex.items())
                v.update({"Annotation": a_no, "Region": r_no})
                vertices.append(v)
            points = points.append(vertices, ignore_index=True)
            logger.debug("\t\tRegion {} has {} vertices."
                         .format(r_no, len(vertices)))

    points.index.rename("Point_ID", inplace=True)
    annotations.index.rename("Annotation_ID", inplace=True)
    regions.index.rename("Region_ID", inplace=True)

    return points, regions, annotations


def load_tables(table_points, table_regions, table_annotations):
    """
    Imports the Points, Regions and Annotations tables from preivously saved
    CSV files. The function

    :param table_points: path to the the Points table file (.csv)
    :type table_points: str
    :param table_regions: path to the the Regions table file (.csv)
    :type table_regions: str
    :param table_annotations: path to the the Annotations table file (.csv)
    :type table_annotations: str

    :returns: the Points, Regions, and Annotations DataFrames
    :rtype: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]

    """
    points = pd.read_csv(table_points, header=0).astype(np.int)
    regions = pd.read_csv(table_regions, header=0)
    annotations = pd.read_csv(table_annotations, header=0)
    return points, regions, annotations


def create_polygons(points):
    """
    Groups the points by annotation and region to create distinct Polygon
    objects (from the shapely library).

    :param points: the Points DataFrame
    :type points: pd.DataFrame

    :returns:
        Indexed table of Polygon objects for each region with at least
        3 vertices.
    :rtype: pd.DataFrame

    """
    table = points.copy()
    table = table.loc[:, "Annotation":"Z"]
    polygons = []
    counter = -1
    for a, df_a in table.groupby("Annotation"):
        for r, df_r in df_a.groupby("Region"):
            counter += 1
            if df_r.shape[0] < 3:
                logger.warning("Region {} in Annotation {} was omitted for "
                               "having fewer than 3 points.".format(r, a))
                continue
            x = np.asarray(df_r.X, dtype=np.float).astype(np.int)
            y = np.asarray(df_r.Y, dtype=np.float).astype(np.int)
            poly = Polygon([[xi, yi] for xi, yi in zip(x, y)])
            polygons.append([counter, poly])
    polygons = pd.DataFrame(
        data=polygons, columns=["Polygon_ID", "PolygonObject"])
    polygons.Polygon_ID = polygons.Polygon_ID.astype(np.int)
    polygons = polygons.set_index("Polygon_ID")
    logger.info("Found {} polygon definition(s) in total."
                .format(len(polygons)))
    return polygons


def create_selection(polygons, regions, layer=None):
    """
    Creates a net polygonal selection object by adding positive polygonal
    regions and subtracting negative polygonal regions. Positive regions are
    included in the net selection, whereas negative regions are excluded from
    it.

    :param polygons: table of all Polygon objects
    :type polygons: pd.DataFrame
    :param regions: table of all Regions
    :type regions: pd.DataFrame
    :param layer: only include polygons from the specified annotation layer
    :type layer: int

    :returns: net polygonal selection object
    :rtype: shapely.Polygon

    """
    # Sort polygons based on whether they represent positive or negative
    # selections.
    positive = []
    negative = []
    for poly_id, p in polygons.iterrows():
        if (layer is not None) and (regions.iloc[poly_id].Annotation != layer):
            continue
        selected = bool(int(regions.iloc[poly_id].Selected))
        nroa = bool(int(regions.iloc[poly_id].NegativeROA))
        logger.debug("Current polygon: {}, Selected: {}, NegativeROA: {}"
                     .format(poly_id, selected, nroa))
        if not nroa:
            positive.append(p.PolygonObject)
        else:
            negative.append(p.PolygonObject)

    # Set algebra: union of positive polygons
    if positive:
        positive = fix_polygon(*positive)
        if isinstance(positive, (tuple, list)):
            union = reduce(Polygon.union, positive)
            selection = fix_polygon(union)
        else:
            selection = positive
    else:
        return None
    # Set algebra: intersection between union and negated polygons
    for neg in negative:
        neg = fix_polygon(neg)
        selection = selection.difference(neg)

    return selection


def fix_polygon(*polygons):
    """
    Corrects self-intersecting polygons.

    """
    single_input = bool(len(polygons) == 1)
    fixed = []
    for p in polygons:
        if not p.is_valid:
            p = p.buffer(0)
            if not p.is_valid:
                logger.critical("Fixing an invalid polygon was unsuccessful.")
            else:
                logger.info("Fixing an invalid polygon was successful.")
        fixed.append(p)

    if single_input:
        return fixed[0]
    else:
        return fixed


def create_mask(selection, original_shape=None, target_shape=None, scale_x=1,
                scale_y=1, invert=False, fill_value=1):
    """
    Creates an 8-bit binary mask based on the net polygonal selection.
    Depending on the exact specification of the parameters, the function may
    return te mask in the following formats:

    1. Full image mask (covering the entire FOV of the histological slide)
    2. Cropped image mask (confined to the rectangular bounds of the selection)
    3. Either (1) or (2) at the specified resolution.

    :param selection:
        The net polygonal selection object.
    :type selection: shapely.Polygon
    :param original_shape:
        If the original shape of the histology image (in pixels) is specified,
        the mask will be returned with a full field-of-view (FOV). The shape
        must be specified as an iterable: (vertical, horizontal). If None, the
        mask is only computed for the tight bounding box of the ROI.
    :type original_shape: tuple[int, int]
    :param target_shape:
        Specify the target shape as an iterable (vertical, horizontal) to
        precisely control the output shape of the mask. When the target shape
        is specified, the scale parameters are overridden.
    :param scale_x:
        Specify the scaling along the horizontal axis for fine-grain
        anisotropic control of the output resolution. THe recommended use is
        setting this equal to scale_y. Note that the output image size is
        calculated by rounding, and therefore it may differ from the expected
        matrix size.
    :type scale_x: Number
    :param scale_y:
        Specify the scaling along the vertical axis for fine-grain
        anisotropic control of the output resolution. THe recommended use is
        setting this equal to scale_x. Note that the output image size is
        calculated by rounding, and therefore it may differ from the expected
        matrix size.
    :param scale_y: Number
    :param invert:
        If False (default), the ROI will be assigned 1, whereas the rest of
        the image will be assigned 0. Turn this option on for a reverse
        assignment of mask values.
    :type invert: bool
    :param fill_value: Value (1-255) of the mask in the ROI. (Default=1)
    :type fill_value: int

    :returns: binary mask highlighting the ROI
    :rtype: np.ndarray

    """
    # Set scale to match target shape
    if target_shape is not None:
        if original_shape is not None:
            scale_y, scale_x = np.divide(target_shape, original_shape)
        else:
            xmin, ymin, xmax, ymax = selection.bounds
            shape = [int(dim) for dim in (ymax - ymin + 1, xmax - xmin + 1)]
            scale_y, scale_x = np.divide(target_shape, shape)

    # Define FOV
    if original_shape is None:
        xmin, ymin, xmax, ymax = selection.bounds
        xmin = int(round(xmin * scale_x))
        ymin = int(round(ymin * scale_y))
        xmax = int(round(xmax * scale_x))
        ymax = int(round(ymax * scale_y))
        shape = [int(dim) for dim in (ymax - ymin + 1, xmax - xmin + 1)]
    else:
        xmin = 0
        ymin = 0
        xmax = int(round(original_shape[1] * scale_x)) - 1
        ymax = int(round(original_shape[0] * scale_y)) - 1
        shape = (ymax - ymin + 1, xmax - xmin + 1)
    logger.info("Binary mask FOV (pixels): {}".format(shape))

    # Define canvas
    canvas = np.zeros(shape, dtype=np.uint8, order="C")

    # Fill exterior contour
    if hasattr(selection, "geoms"):
        for geom in selection.geoms:
            ex, ey = geom.exterior.xy
            ex = np.asarray(ex) * scale_x
            ey = np.asarray(ey) * scale_y
            rr, cc = draw_polygon(ey - ymin, ex - xmin, shape)
            canvas[rr, cc] = fill_value
    else:
        ex, ey = selection.exterior.xy
        ex = np.asarray(ex) * scale_x
        ey = np.asarray(ey) * scale_y
        rr, cc = draw_polygon(ey - ymin, ex - xmin, shape)
        canvas[rr, cc] = fill_value

    # Clear internal contours
    if hasattr(selection, "geoms"):
        for geom in selection.geoms:
            for interior in geom.interiors:
                ix, iy = interior.xy
                ix = np.asarray(ix) * scale_x
                iy = np.asarray(iy) * scale_y
                rr, cc = draw_polygon(iy - ymin, ix - xmin, shape)
                canvas[rr, cc] = 0
    else:
        for interior in selection.interiors:
            ix, iy = interior.xy
            ix = np.asarray(ix) * scale_x
            iy = np.asarray(iy) * scale_y
            rr, cc = draw_polygon(iy - ymin, ix - xmin, shape)
            canvas[rr, cc] = 0

    if invert:
        canvas = fill_value - canvas

    return canvas


def visualise_polygon(p, show=True, save=False):
    # Create figure
    plt.figure()

    # Visualise exterior boundary/boundaries
    if hasattr(p, "geoms"):
        for geom in p.geoms:
            x, y = geom.exterior.xy
            plt.plot(np.asarray(x), np.asarray(y), color="blue")
    else:
        x, y = p.exterior.xy
        plt.plot(np.asarray(x), np.asarray(y), color="blue")

    # Visualise interior boundary/boundaries
    if hasattr(p, "geoms"):
        for geom in p.geoms:
            for interior in geom.interiors:
                xi, yi = interior.xy
                plt.plot(np.asarray(xi), np.asarray(yi), color="red")
    else:
        for interior in p.interiors:
            xi, yi = interior.xy
            plt.plot(np.asarray(xi), np.asarray(yi), color="red")

    # Perform the specified operations
    if save:
        plt.savefig(save)
    if show:
        plt.show()


if __name__ == "__main__":
    """ Module execution protocol. """

    # Example configuration.
    process("NP391-16_PLP_LVC_20x.xml", **DEFAULT_OPTIONS)
