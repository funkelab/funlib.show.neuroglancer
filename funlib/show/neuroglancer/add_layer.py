from .scale_pyramid import ScalePyramid
import neuroglancer
from funlib.persistence import Array


rgb_shader_code = """
void main() {
    emitRGB(
        vec3(
            toNormalized(getDataValue(%i)),
            toNormalized(getDataValue(%i)),
            toNormalized(getDataValue(%i)))
        );
}"""

color_shader_code = """
void main() {
    emitRGBA(
        vec4(
        %f, %f, %f,
        toNormalized(getDataValue()))
        );
}"""

binary_shader_code = """
void main() {
  emitGrayscale(255.0*toNormalized(getDataValue()));
}"""

heatmap_shader_code = """
void main() {
    float v = toNormalized(getDataValue(0));
    vec4 rgba = vec4(0,0,0,0);
    if (v != 0.0) {
        rgba = vec4(colormapJet(v), 1.0);
    }
    emitRGBA(rgba);
}"""


def create_coordinate_space(
    array: Array,
) -> tuple[neuroglancer.CoordinateSpace, list[int]]:
    assert array.spatial_dims > 0

    def interleave(list, fill_value, axis_names):
        return_list = [fill_value] * len(axis_names)
        for i, name in enumerate(axis_names):
            if "^" not in name:
                return_list[i] = list.pop(0)
        return return_list

    units = interleave(list(array.units), "", array.axis_names)
    scales = interleave(list(array.voxel_size), 1, array.axis_names)
    offset = interleave(list(array.offset / array.voxel_size), 0, array.axis_names)

    return (
        neuroglancer.CoordinateSpace(
            names=array.axis_names, units=units, scales=scales
        ),
        offset,
    )


def guess_shader_code(array: Array):
    """
    TODO: This function is not used yet.
    It should make some reasonable guesses for basic visualization parameters.
    Guess volume type (or read from optional metadata?):
        - bool/uint32/uint64/int32/int64 -> Segmentation
        - floats/int8/uint8 -> Image
    Guess shader for Image volumes:
        - 1 channel dimension:
            - 1 channel -> grayscale (add shader options for color and threshold)
            - 2 channels -> projected RGB (set B to 0 or 1 or R+G?)
            - 3 channels -> RGB
            - 4 channels -> projected RGB (PCA? Random linear combinations? Randomizable with "l" key?)
        - multiple channel dimensions?:
    """
    raise NotImplementedError()
    channel_dim_shapes = [
        array.shape[i]
        for i in range(len(array.axis_names))
        if "^" in array.axis_names[i]
    ]
    if len(channel_dim_shapes) == 0:
        return None  # default shader

    if len(channel_dim_shapes) == 1:
        num_channels = channel_dim_shapes[0]
        if num_channels == 1:
            return None  # default shader
        if num_channels == 2:
            return projected_rgb_shader_code % num_channels
        if num_channels == 3:
            return rgb_shader_code % (0, 1, 2)
        if num_channels > 3:
            return projected_rgb_shader_code % num_channels


def create_shader_code(
    shader, channel_dims, rgb_channels=None, color=None, scale_factor=1.0
):
    if shader is None:
        if channel_dims > 1:
            shader = "rgb"
        else:
            return None

    if rgb_channels is None:
        rgb_channels = [0, 1, 2]

    if shader == "rgb":
        return rgb_shader_code % (
            scale_factor,
            rgb_channels[0],
            rgb_channels[1],
            rgb_channels[2],
        )

    if shader == "color":
        assert (
            color is not None
        ), "You have to pass argument 'color' to use the color shader"
        return color_shader_code % (
            color[0],
            color[1],
            color[2],
        )

    if shader == "binary":
        return binary_shader_code

    if shader == "heatmap":
        return heatmap_shader_code


def add_layer(
    context,
    array: Array | list[Array],
    name: str,
    opacity: float | None = None,
    shader: str | None = None,
    rgb_channels=None,
    color=None,
    visible=True,
    value_scale_factor=1.0,
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

            A float to define the layer opacity between 0 and 1.

        shader:

            A string to be used as the shader. Possible values are:

                None     :  neuroglancer's default shader
                'rgb'    :  An RGB shader on dimension `'c^'`. See argument
                            ``rgb_channels``.
                'color'  :  Shows intensities as a constant color. See argument
                            ``color``.
                'binary' :  Shows a binary image as black/white.
                'heatmap':  Shows an intensity image as a jet color map.

        rgb_channels:

            Which channels to use for RGB (default is ``[0, 1, 2]``).

        color:

            A list of floats representing the RGB values for the constant color
            shader.

        visible:

            A bool which defines the initial layer visibility.

        value_scale_factor:

            A float to scale array values with for visualization.

        units:

            The units used for resolution and offset.
    """

    if rgb_channels is None:
        rgb_channels = [0, 1, 2]

    is_multiscale = isinstance(array, list)

    if is_multiscale:
        dimensions = []
        for a in array:
            dimensions.append(create_coordinate_space(a))

        layer = ScalePyramid(
            [
                neuroglancer.LocalVolume(
                    data=a.data, voxel_offset=voxel_offset, dimensions=array_dims
                )
                for a, (array_dims, voxel_offset) in zip(array, dimensions)
            ]
        )

        array = array[0]

    else:
        dimensions, voxel_offset = create_coordinate_space(array)

        layer = neuroglancer.LocalVolume(
            data=array.data,
            voxel_offset=voxel_offset,
            dimensions=dimensions,
        )

    if shader is not None:
        shader_code = create_shader_code(
            shader, array.channel_dims, rgb_channels, color, value_scale_factor
        )
    else:
        shader_code = None

    if opacity is not None:
        if shader_code is None:
            context.layers.append(
                name=name, layer=layer, visible=visible, opacity=opacity
            )
        else:
            context.layers.append(
                name=name,
                layer=layer,
                visible=visible,
                shader=shader_code,
                opacity=opacity,
            )
    else:
        if shader_code is None:
            context.layers.append(name=name, layer=layer, visible=visible)
        else:
            context.layers.append(
                name=name, layer=layer, visible=visible, shader=shader_code
            )
