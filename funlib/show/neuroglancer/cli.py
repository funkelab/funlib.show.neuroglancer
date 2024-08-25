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


def to_slice(slice_str):
    values = [int(x) for x in slice_str.split(":")]
    if len(values) == 1:
        return values[0]

    return slice(*values)


def parse_ds_name(ds):
    tokens = ds.split("[")

    if len(tokens) == 1:
        return ds, None

    ds, slices = tokens
    slices = list(map(to_slice, slices.rstrip("]").split(",")))

    return ds, slices


class Project:
    def __init__(self, array, dim, value):
        self.array = array
        self.dim = dim
        self.value = value
        self.shape = array.shape[: self.dim] + array.shape[self.dim + 1 :]
        self.dtype = array.dtype

    def __getitem__(self, key):
        slices = key[: self.dim] + (self.value,) + key[self.dim :]
        ret = self.array[slices]
        return ret


def slice_dataset(a, slices):
    dims = a.roi.dims

    for d, s in list(enumerate(slices))[::-1]:
        if isinstance(s, slice):
            raise NotImplementedError("Slicing not yet implemented!")
        else:
            index = (s - a.roi.begin[d]) // a.voxel_size[d]
            a.data = Project(a.data, d, index)
            a.roi = daisy.Roi(
                a.roi.begin[:d] + a.roi.begin[d + 1 :],
                a.roi.shape[:d] + a.roi.shape[d + 1 :],
            )
            a.voxel_size = a.voxel_size[:d] + a.voxel_size[d + 1 :]

    return a


def open_dataset(fs):
    original_fs = fs
    ds, slices = parse_ds_name(fs)
    slices_str = original_fs[len(ds) :]

    try:
        dataset_as = []
        if all(
            key.startswith("s") or key.startswith("") for key in zarr.open(fs).keys()
        ):
            raise AttributeError("This group is a multiscale array!")
        for key in zarr.open(fs).keys():
            dataset_as.extend(open_dataset(f"{fs}/{key}{slices_str}"))
        return dataset_as
    except AttributeError as e:
        # dataset is an array, not a group
        pass

    print("ds    :", ds)
    print("slices:", slices)
    try:
        zarr.open(fs).keys()
        is_multiscale = True
    except:
        is_multiscale = False

    if not is_multiscale:
        a = open_ds(fs)

        if slices is not None:
            a = slice_dataset(a, slices)

        if a.data.dtype == np.int64 or a.data.dtype == np.int16:
            print("Converting dtype in memory...")
            a.data = a.data[:].astype(np.uint64)

        return [(a, fs)]
    else:
        return [([open_ds(f"{fs}/{key}") for key in zarr.open(f)[ds].keys()], ds)]


parser = argparse.ArgumentParser()
parser.add_argument(
    "--paths", "-p", type=str, nargs="+", help="The path to the container to show"
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
        for ds_path in glob.glob(glob_path):
            arrays = []
            try:
                print("Adding %s" % (ds_path))
                dataset_as = open_dataset(ds_path)

            except Exception as e:
                print(type(e), e)
                print("Didn't work, checking if this is multi-res...")

                scales = glob.glob(os.path.join(ds_path, "s*"))
                if len(scales) == 0:
                    print(f"Couldn't read {ds_path}, skipping...")
                    raise e
                print("Found scales %s" % ([os.path.relpath(s, ds_path) for s in scales],))
                dataset_as = [
                    open_dataset(ds_path, os.path.relpath(scale_ds, ds_path)) for scale_ds in scales
                ]
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
