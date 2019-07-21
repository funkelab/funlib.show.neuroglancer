from funlib.show.neuroglancer import add_layer, ScalePyramid
import argparse
import daisy
import glob
import neuroglancer
import os
import webbrowser

parser = argparse.ArgumentParser()
parser.add_argument(
    '--file',
    '-f',
    type=str,
    action='append',
    required=True,
    help="The path to the container to show")
parser.add_argument(
    '--datasets',
    '-d',
    type=str,
    nargs='+',
    action='append',
    required=True,
    help="The datasets in the container to show")
parser.add_argument(
    '--no_browser',
    '-n',
    action='store_true',
    help="If set, do not open browser with generated URL")

args = parser.parse_args()

neuroglancer.set_server_bind_address('0.0.0.0')
viewer = neuroglancer.Viewer()

for f, datasets in zip(args.file, args.datasets):

    arrays = []
    for ds in datasets:
        try:

            print("Adding %s, %s" % (f, ds))
            a = daisy.open_ds(f, ds)

        except:

            print("Didn't work, checking if this is multi-res...")

            scales = glob.glob(os.path.join(f, ds, 's*'))
            print("Found scales %s" % ([
                os.path.relpath(s, f)
                for s in scales
            ],))
            a = [
                daisy.open_ds(f, os.path.relpath(scale_ds, f))
                for scale_ds in scales
            ]
        arrays.append(a)

    with viewer.txn() as s:
        for array, dataset in zip(arrays, datasets):
            add_layer(s, array, dataset)

url = str(viewer)
print('\nURL:\n%s\n' % url)

if not args.no_browser:
    webbrowser.open_new(url)

print("Press ENTER to quit")
input()
