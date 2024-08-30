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


We also have slicing support (This command will select only the first channel of raw from every crop):

`neuroglancer data.zarr/crop_*/raw[0]`

This can lead to a conflict if you want to use glob expansion to select multiple arrays.
Here it is unclear if you want to visualize the arrays `raw_1`, `raw_3`, `raw_4` and `raw_5`,
or if you want to visualize channel `1345` of the array `raw_`.

`neuroglancer data.zarr/raw_[1345]`

To make this less ambiguous, we allow the use of the `:` character to separate the array glob from the
slicing patter. So the following command will select the arrays `raw_1`, `raw_3`, `raw_4` and `raw_5`:

`neuroglancer data.zarr/raw_[1345]:`