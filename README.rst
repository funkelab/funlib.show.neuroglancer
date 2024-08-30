funlib.show.neuroglancer
========================

Scripts and helpers for the
`neuroglancer <https://github.com/google/neuroglancer>`_ WebGL viewer.

Currently contains:

- a layer to show multi-scale volumes from python

- a modified ``video_tool.py`` to work with ``LocalVolume``

- a convenience method to add daisy-like arrays to a neuroglancer context

Usage
-----

You can use terminal glob syntax to select multiple volumes for visualization:

`neuroglancer path/to/your/data.zarr/and/volumes/*`

Extra optional arguments are:

- `--no-browser`
- `--bind-address`
- `--port`


We also have slicing support (This command will select only the first channel of raw from every crop, along with the ground truth and the 3rd 4th and 5th channel of the affs):

`neuroglancer -d data.zarr/crop_*/raw -s [0] -d data.zarr/crop_*/gt -d data.zarr/crop_*/affs -s [3,4,5]`