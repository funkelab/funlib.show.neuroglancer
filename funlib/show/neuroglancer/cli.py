#!/usr/bin/env python

from funlib.show.neuroglancer import add_layer
from funlib.persistence import open_ds
import argparse
import glob
import neuroglancer
import os
import webbrowser
import numpy as np
import zarr
from itertools import chain
from pathlib import Path



def parse_ds_name(ds):
    tokens = ds.split("[")

    if len(tokens) == 1:
        return ds, None

    ds, slices = tokens
    slices = eval("np.s_[" + slices)

    return ds, slices





parser = argparse.ArgumentParser()
parser.add_argument(
    "paths", type=str, nargs="+", help="The path to the container to show"
)
parser.add_argument(
    "--no-browser",
    "-n",
    type=bool,
    nargs="?",
    default=False,
    const=True,
    help="If set, do not open a browser, just print a URL",
)
parser.add_argument(
    "--bind-address",
    "-b",
    type=str,
    nargs="?",
    default="0.0.0.0",
    const=True,
    help="Bind address",
)
parser.add_argument("--port", type=int, default=0, help="The port to bind to.")


def main():
    args = parser.parse_args()

    neuroglancer.set_server_bind_address(args.bind_address, bind_port=args.port)
    viewer = neuroglancer.Viewer()
    for glob_path in args.paths:
        glob_path, slices = parse_ds_name(glob_path)
        print(f"Adding {glob_path} with slices {slices}")
        for ds_path in glob.glob(glob_path):
            ds_path = Path(ds_path)
            arrays = []
            try:
                print("Adding %s" % (ds_path))
                array = open_ds(ds_path)
                dataset_as = [(array, ds_path)]

            except Exception as e:
                print(type(e), e)
                print("Didn't work, checking if this is multi-res...")

                scales = glob.glob(ds_path / "s*")
                if len(scales) == 0:
                    print(f"Couldn't read {ds_path}, skipping...")
                    raise e
                print(
                    "Found scales %s" % ([os.path.relpath(s, ds_path) for s in scales],)
                )
                dataset_as = [(open_ds(scale_ds), scale_ds) for scale_ds in scales]
            for array, name in dataset_as:
                if slices is not None:
                    array.lazy_op(slices)
                arrays.append((array, name))

            with viewer.txn() as s:
                for array, dataset in arrays:
                    add_layer(s, array, Path(dataset).name)

    url = str(viewer)
    print(url)
    if os.environ.get("DISPLAY") and not args.no_browser:
        webbrowser.open_new(url)

    print("Press ENTER to quit")
    input()
