# xml2mask v2.0

Converts XML annotation files from Aperio Image Analysis to binary masks.

## Installation
1. Download and install **openslide** (the framework, not the Python interface!) from <https://openslide.org/download/>
2. Download and install **Miniconda3** from <https://docs.conda.io/en/latest/miniconda.html>
3. Download this git package and cd into it:

	```
	git clone https://github.com/inhuszar/xml2mask.git
	cd xml2mask
	```

4. Create new conda environment from one of the provided environment files:

	```
	conda env create -f environment_macosx.yml
	```

5. Activate the new environment:

	```
	conda activate histroi
	```

6. Install xml2mask:

	```
	python setup.py install
	```

7. Restart the terminal, and don't forget to activate the histroi environment before running the program.

## Usage
### Syntax
```
xml2mask <xml_file> [options]
```

Example:
```
xml2mask my_annotations.xml --resolution high --tile 29000 17000 2000 2000 --histo --out my_annotations/results
```

<span style="color:red">Important:</span> do not forget to activate the conda environment before using the above command (see installation step #5).

### Options
The following may be specified as command-line options (either alone or in combination):

1. `--image <svs_file>`: specifies the location of the concomitant SVS file (the actual histology image). If the --image argument is not given, the script will assume that it is next to the XML file and has an identical name.
2. `--resolution high/low/0/1/2`: Specifies which of the resolution levels of the SVS files the program will use. Default=low. The low resolution is approximately 3000x2000 pixels large and is suitable for generating whole-slide annotation masks. The high option corresponds to the highest resolution (image size: 60k x 50k pixels), which is suitable for creating annotation masks for smaller tiles (2000 x 2000). Usually there are 3 resolution levels in an SVS file, low=2 (or -1), and high=0.
3. `--scale 0.1 0.1`: the size of the binary mask will be 10% x 10% of the original size of the histology image at the chosen resolution level (low-res by default). The numbers represent scaling along the horizontal (x) and the vertical (y) axes, respectively. The default scaling factors are (x=1, y=1).
4. `--target 3000 2000`: sets a precise value for the output shape. Behind the scenes, these are used to calculate scaling factors for the histology image. If --scale is also specified, the target shape specification takes precedence and overrides the scaling factors.
5. `--tile 29000 17000 2000 2000`: creates a binary mask for a (x=2000 x y=2000) pixel large tile of the original histology image, the top-left corner of which is at (x=29000px, y=17000px). The coordinates and the size of the tile must be specified with respect to the output reference frame, i.e. taking all scaling into account. If no scaling or target shape is specified, and `--resolution high` is set, the coordinates and tile sizes are in the reference frame of the highest-
resolution histology image.
6. `--out outdir`: specifies the output directory where all files will be saved to. The output directory may or may not exist at the time of executing the command, but it must not contain a file name specification. If `--out` is not given, the out will be saved next to the input XML file.
7. `--histo`: saves a histology image output next to the annotation masks with a matching FOV, so that the overlap of the two can be verified by eye.


## Uninstallation
xml2mask can be uninstalled by removing the conda environment:

```
conda remove -n histroi --all
```
