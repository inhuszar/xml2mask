#!/usr/bin/env python3

import os
import sys
from setuptools import setup, find_packages

dylibs = os.getenv("DYLD_FALLBACK_LIBRARY_PATH")
if not dylibs or ("/usr/lib" not in dylibs.split(":")):
      if sys.platform == "darwin":
            configfile = os.path.expanduser("~/.bash_profile")
      elif sys.platform in ("linux", "linux2"):
            configfile = os.path.expanduser("~/.bashrc")
      else:
            raise OSError("Unsupported platform.")
      with open(configfile, "a") as outfile:
            outfile.write("\n#Added by the xml2mask installer.\n")
            outfile.write("export DYLD_FALLBACK_LIBRARY_PATH="
                          "/usr/lib:$DYLD_FALLBACK_LIBRARY_PATH\n")

setup(name="xml2mask",
      version="1.0",
      description="Create binary masks from Aperio XML annotation files.",
      author="Istvan N. Huszar",
      author_email="istvan.huszar@dtc.ox.ac.uk",
      url="",
      license="MIT",
      packages=find_packages(),
      py_modules=["histroi.roi", "histroi.xml2mask"],
      entry_points={"console_scripts": ["xml2mask=histroi.xml2mask:init"]},
      install_requires=["numpy", "pandas", "dill", "pillow", "attrdict",
                        "geos", "shapely", "scikit-image", "openslide-python"])
