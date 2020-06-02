from funlib.show.neuroglancer import add_layer
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
    help="The path to the container to show")
parser.add_argument(
    '--datasets',
    '-d',
    type=str,
    nargs='+',
    action='append',
    help="The datasets in the container to show")
parser.add_argument(
    '--graphs',
    '-g',
    type=str,
    nargs='+',
    action='append',
    help="The graphs in the container to show")

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

if args.graphs:
    for f, graphs in zip(args.file, args.graphs):

        for graph in graphs:

            graph_annotations = []
            ids = daisy.open_ds(f, graph + '-ids')
            loc = daisy.open_ds(f, graph + '-locations')
            for i, l in zip(ids.data, loc.data):
                graph_annotations.append(
                    neuroglancer.EllipsoidAnnotation(
                        center=l[::-1],
                        radii=(5, 5, 5),
                        id=i))
            graph_layer = neuroglancer.AnnotationLayer(
                annotations=graph_annotations,
                voxel_size=(1, 1, 1))

            with viewer.txn() as s:
                s.layers.append(name='graph', layer=graph_layer)

url = str(viewer)
print(url)
webbrowser.open_new(url)

print("Press ENTER to quit")
input()
