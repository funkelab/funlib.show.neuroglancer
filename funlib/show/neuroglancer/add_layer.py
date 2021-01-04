from .scale_pyramid import ScalePyramid
import neuroglancer


def add_layer(
    context,
    array,
    name,
    opacity=None,
    shader=None,
    visible=True,
    reversed_axes=False,
    scale_rgb=False,
    c=[0, 1, 2],
    h=[0.0, 0.0, 1.0],
):

    """Add a layer to a neuroglancer context.

    Args:

        context:

            The neuroglancer context to add a layer to, as obtained by
            ``viewer.txn()``.

        array:

            A ``daisy``-like array, containing attributes ``roi``,
            ``voxel_size``, and ``data``. If a list of arrays is given, a
            ``ScalePyramid`` layer is generated.

        name:

            The name of the layer.

        opacity:

            A float to define the layer opacity between 0 and 1

        shader:

            A string to be used as the shader. If set to ``'rgb'``, an RGB
            shader will be used.

        visible:

            A bool which defines layer visibility

        c (channel):

            A list of ints to define which channels to use for an rgb shader

        h (hue):

            A list of floats to define rgb color for an rgba shader
    """

    is_multiscale = type(array) == list

    if not is_multiscale:

        a = array if not is_multiscale else array[0]

        spatial_dim_names = ["t", "z", "y", "x"]
        channel_dim_names = ["b^", "c^"]

        dims = len(a.data.shape)
        spatial_dims = a.roi.dims()
        channel_dims = dims - spatial_dims

        attrs = {
            "names": (channel_dim_names[-channel_dims:] if channel_dims > 0 else [])
            + spatial_dim_names[-spatial_dims:],
            "units": [""] * channel_dims + ["nm"] * spatial_dims,
            "scales": [1] * channel_dims + list(a.voxel_size),
        }
        if reversed_axes:
            attrs = {k: v[::-1] for k, v in attrs.items()}
        dimensions = neuroglancer.CoordinateSpace(**attrs)

        voxel_offset = [0] * channel_dims + list(a.roi.get_offset() / a.voxel_size)

    else:
        dimensions = []
        voxel_offset = None
        for i, a in enumerate(array):

            spatial_dim_names = ["t", "z", "y", "x"]
            channel_dim_names = ["b^", "c^"]

            dims = len(a.data.shape)
            spatial_dims = a.roi.dims()
            channel_dims = dims - spatial_dims

            attrs = {
                "names": (channel_dim_names[-channel_dims:] if channel_dims > 0 else [])
                + spatial_dim_names[-spatial_dims:]
                if spatial_dims > 0
                else [],
                "units": [""] * channel_dims + ["nm"] * spatial_dims,
                "scales": [1] * channel_dims + list(a.voxel_size),
            }
            if reversed_axes:
                attrs = {k: v[::-1] for k, v in attrs.items()}
            dimensions.append(neuroglancer.CoordinateSpace(**attrs))

            if voxel_offset is None:
                voxel_offset = [0] * channel_dims + list(
                    a.roi.get_offset() / a.voxel_size
                )

    if reversed_axes:
        voxel_offset = voxel_offset[::-1]

    if shader is None:
        a = array if not is_multiscale else array[0]
        dims = a.roi.dims()
        if dims < len(a.data.shape):
            channels = a.data.shape[0]
            if channels > 1:
                shader = "rgb"

    if shader == "rgb":
        if scale_rgb:
            shader = """
void main() {
    emitRGB(
        255.0*vec3(
            toNormalized(getDataValue(%i)),
            toNormalized(getDataValue(%i)),
            toNormalized(getDataValue(%i)))
        );
}""" % (
                c[0],
                c[1],
                c[2],
            )

        else:
            shader = """
void main() {
    emitRGB(
        vec3(
            toNormalized(getDataValue(%i)),
            toNormalized(getDataValue(%i)),
            toNormalized(getDataValue(%i)))
        );
}""" % (
                c[0],
                c[1],
                c[2],
            )

    elif shader == "rgba":
        shader = """
void main() {
    emitRGBA(
        vec4(
        %f, %f, %f,
        toNormalized(getDataValue()))
        );
}""" % (
            h[0],
            h[1],
            h[2],
        )

    elif shader == "mask":
        shader = """
void main() {
  emitGrayscale(255.0*toNormalized(getDataValue()));
}"""

    elif shader == "heatmap":
        shader = """
void main() {
    float v = toNormalized(getDataValue(0));
    vec4 rgba = vec4(0,0,0,0);
    if (v != 0.0) {
        rgba = vec4(colormapJet(v), 1.0);
    }
    emitRGBA(rgba);
}"""

    kwargs = {}

    if shader is not None:
        kwargs["shader"] = shader
    if opacity is not None:
        kwargs["opacity"] = opacity

    if is_multiscale:

        layer = ScalePyramid(
            [
                neuroglancer.LocalVolume(
                    data=a.data, voxel_offset=voxel_offset, dimensions=array_dims
                )
                for a, array_dims in zip(array, dimensions)
            ]
        )

    else:
        layer = neuroglancer.LocalVolume(
            data=array.data,
            voxel_offset=voxel_offset,
            dimensions=dimensions,
        )

    context.layers.append(name=name, layer=layer, visible=visible, **kwargs)
