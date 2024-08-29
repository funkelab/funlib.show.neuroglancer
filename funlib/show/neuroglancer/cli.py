#!/usr/bin/env python

from funlib.show.neuroglancer import add_layer
from funlib.persistence import open_ds
import argparse
import glob
import neuroglancer
import os
import webbrowser
from pathlib import Path
import numpy as np  # noqa: F401 This import is used in the eval statement below


def parse_ds_name(ds):
    if ":" in ds:
        ds, *slices = ds.split(":")
    else:
        ds, *slices = ds.split("[")

    if len(slices) == 0:
        return ds, None
    elif len(slices) == 1:
        slices = slices[0].strip("[]")
        if len(slices) == 0:
            slices = ":"
        slices = eval(f"np.s_[{slices}]")
        return ds, slices
    else:
        raise ValueError("Used multiple sets of brackets")


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
            try:
                print("Adding %s" % (ds_path))
                array = open_ds(ds_path)
                arrays = [(array, ds_path)]

            except Exception as e:
                print(type(e), e)
                print("Didn't work, checking if this is multi-res...")

                scales = glob.glob(f"{ds_path}/s*")
                if len(scales) == 0:
                    print(f"Couldn't read {ds_path}, skipping...")
                    raise e
                print(
                    "Found scales %s" % ([os.path.relpath(s, ds_path) for s in scales],)
                )
                arrays = [([open_ds(scale_ds) for scale_ds in scales], ds_path)]

            for array, _ in arrays:
                if not isinstance(array, list):
                    array = [array]
                for arr in array:
                    if slices is not None:
                        arr.lazy_op(slices)

            with viewer.txn() as s:
                for array, dataset in arrays:
                    add_layer(s, array, Path(dataset).name)

    url = str(viewer)
    print(url)
    if os.environ.get("DISPLAY") and not args.no_browser:
        webbrowser.open_new(url)

    print("Press ENTER to quit")
    input()
