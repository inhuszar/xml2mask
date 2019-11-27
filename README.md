# xml2mask

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
<span style="color:red">Important:</span> do not forget to activate the conda environment before using the above command (see installation step #5).

### Setting the output shape
One of the following must be specified as command-line options:

1. `--image <svs_file>`: use the lowest available resolution in the specified histology image file (must have .svs extension).
2. `--image auto`: use the lowest available resolution in the histology file that is next to the xml file and has the same filename. (The histology image must have .svs extension.) If --tile is specified, this selects the highest available resolution.
3. `--scale 0.1 0.1`: the size of the binary mask will be 10% x 10% of the original size of the histology image at the highest available resolution. The numbers represent scaling along the horizontal (x) and the vertical (y) axes, respectively.
4. `--target 3000 2000`: sets a precise value for the output shape. Behind the scenes, these are used to calculate scaling factors for the histology image. If --scale is also specified, the target shape is further scaled by the specified factors.
5. `--image <svs_file>/auto [--scale 0.5 [0.5]] --tile 14500 8500 1000 1000`: Take the highest-resolution image from the specified SVS image file, scale it by (x=50%, y=50%) and create a binary mask for a 1000x1000 pixel large tile, the top-left corner of which is at x=14500 y=8500 in the scaled image. Note that the scale parameter is optional.


## Uninstallation
xml2mask can be uninstalled by removing the conda environment:

```
conda remove -n histroi --all
```
