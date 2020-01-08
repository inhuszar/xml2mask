#!/usr/bin/env python3

import os
import sys
from setuptools import setup, find_packages

# The Shapely library depends on system-wide dylibs on MacOS
if sys.platform == "darwin":
      dylibs = os.getenv("DYLD_FALLBACK_LIBRARY_PATH")
      configfile = os.path.expanduser("~/.bash_profile")
      syslib = "/usr/lib"
      if not dylibs or (syslib not in dylibs.split(":")):
            with open(configfile, "a") as outfile:
                  outfile.write("\n#Added by the xml2mask installer.\n")
                  outfile.write("export DYLD_FALLBACK_LIBRARY_PATH="
                                "{}:$DYLD_FALLBACK_LIBRARY_PATH\n".format(syslib))

elif sys.platform in ("linux", "linux2"):
      pass  # Nothing to do
else:
      raise OSError("Unsupported platform.")

setup(name="xml2mask",
      version="2.0",
      description="Create binary masks from Aperio XML annotation files.",
      author="Istvan N. Huszar",
      author_email="istvan.huszar@dtc.ox.ac.uk",
      url="",
      license="MIT",
      packages=find_packages(),
      py_modules=["histroi.roi", "histroi.xml2mask"],
      entry_points={"console_scripts": ["xml2mask=histroi.xml2mask:init"]})
