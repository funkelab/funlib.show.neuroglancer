from .scale_pyramid import ScalePyramid
from funlib.geometry import Coordinate
import neuroglancer
import random


rgb_shader_code = """
void main() {
    emitRGB(
        %f*vec3(
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

adjustable_shader_code = """
#uicontrol invlerp normalized
#uicontrol vec3 color color(default="red")
void main() {
    emitRGB(
    color * vec3(
        normalized(getDataValue(%i)),
        normalized(getDataValue(%i)),
        normalized(getDataValue(%i)))
    );
}
"""

singlechannel_shader_code = """
#uicontrol invlerp normalized
#uicontrol int channel slider(min=0, max=%f)
#uicontrol vec3 color color(default="red")
void main() {
	emitRGB(color * (normalized(getDataValue(%i))));
}
"""


def generate_random_color():
    lower_bound = 0.5  # to prevent dim colors
    r = random.uniform(lower_bound, 1.0)
    g = random.uniform(lower_bound, 1.0)
    b = random.uniform(lower_bound, 1.0)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def combined_additive_shader(num_channels, scale=0.5):
    pos_bias = (float(num_channels) + 1.0) / float(num_channels)

    shader = f"""
#define NUM_CHANNELS {num_channels}

#uicontrol float pos_bias slider(default={pos_bias}, min=0, max=5, step=0.1)

void main() {{
    vec3 transform[NUM_CHANNELS / 3];
    for (int i = 0; i < NUM_CHANNELS / 3; ++i) {{
        transform[i] = vec3(0.5, 0.5, 0.5); // Default transformation
    }}
    transform[0] = vec3(1.0, 0.0, 0.0);
    transform[1] = vec3(0.0, 1.0, 0.0);
    transform[2] = vec3(0.0, 0.0, 1.0);

    vec3 color = vec3(0.0, 0.0, 0.0);

    for (int i = 0; i < NUM_CHANNELS; ++i) {{
        float channelValue = pos_bias * (toNormalized(getDataValue(i)) - {scale});
        color.r += channelValue * transform[i / 3].r;
        color.g += channelValue * transform[i / 3].g;
        color.b += channelValue * transform[i / 3].b;
    }}

    emitRGB(color);
}}
"""

    return shader


def additive_shader(
    num_channels,
    shuffle=False,
    total_default=1.0,
    total_min=0.5,
    total_max=2.5,
    channel_default=1.0,
    channel_min=0.5,
    channel_max=2.5,
    saved_defaults=None,
):
    if saved_defaults and "total" in saved_defaults:
        total_default = saved_defaults["total"]
        total_min = min(total_min, total_default)
        total_max = max(total_max, total_default)

    slider_controls = (
        "#uicontrol float total slider(default={}, min={}, max={}, step=0.1)".format(
            total_default, total_min, total_max
        )
    )

    r_terms, g_terms, b_terms = [], [], []
    channel_indices = list(range(num_channels))

    if shuffle:
        random.shuffle(channel_indices)

    for i in channel_indices:
        # Initialize channel parameters with defaults
        current_channel_default = channel_default
        current_channel_min = channel_min
        current_channel_max = channel_max

        # Adjust each channel's default, min, and max based on saved values, if present
        if saved_defaults and f"channel_{i}" in saved_defaults:
            current_channel_default = saved_defaults[f"channel_{i}"]
            current_channel_min = min(channel_min, current_channel_default)
            current_channel_max = max(channel_max, current_channel_default)

        current_channel_default = (
            random.uniform(current_channel_min, current_channel_max)
            if shuffle
            else current_channel_default
        )

        slider_controls += (
            "\n#uicontrol float channel_"
            + str(i)
            + " slider(default={}, min={}, max={}, step=0.1)".format(
                current_channel_default, current_channel_min, current_channel_max
            )
        )

        term = "channel_" + str(i) + " * toNormalized(getDataValue(" + str(i) + "))"
        if i % 3 == 0:
            r_terms.append(term)
        elif i % 3 == 1:
            g_terms.append(term)
        else:
            b_terms.append(term)

    r_sum = " + ".join(r_terms)
    g_sum = " + ".join(g_terms)
    b_sum = " + ".join(b_terms)

    shader_code = """
{}
void main() {{
    emitRGB(
        total * vec3(
            {},
            {},
            {}
        )
    );
}}
""".format(
        slider_controls, r_sum, g_sum, b_sum
    )

    return shader_code


def create_shuffle_shader(
    num_channels, slider_default_min=0.0, slider_default_max=0.03, saved_defaults=None
):
    assert (
        num_channels >= 3
    ), f"Data must be at least three dimensional, got {num_channels} channels!"

    shader = []

    # ui controls for each channel
    for i in range(num_channels):
        # get saved defaults if any
        chan_active_default = (
            saved_defaults.get(f"chan{i}_active", True) if saved_defaults else True
        )
        chan_min_default = (
            saved_defaults.get(f"chan{i}_min", slider_default_min)
            if saved_defaults
            else slider_default_min
        )
        chan_max_default = (
            saved_defaults.get(f"chan{i}_max", slider_default_max)
            if saved_defaults
            else slider_default_max
        )

        # adjust min and max values if necessary
        chan_min = min(0, chan_min_default)
        chan_max = max(1, chan_max_default)

        shader.extend(
            [
                f"#uicontrol bool chan{i}_active checkbox(default={str(chan_active_default).lower()})",
                f"#uicontrol float chan{i}_min slider(min={chan_min}, max=1, step=0.001, default={chan_min_default})",
                f"#uicontrol float chan{i}_max slider(min=0, max={chan_max}, step=0.001, default={chan_max_default})",
            ]
        )

    # extra controls with checks for saved defaults
    contrast_default = saved_defaults.get("contrast", 0) if saved_defaults else 0
    brightness_default = saved_defaults.get("brightness", 0) if saved_defaults else 0
    scaleR_default = saved_defaults.get("scaleR", 1) if saved_defaults else 1
    scaleG_default = saved_defaults.get("scaleG", 1) if saved_defaults else 1
    scaleB_default = saved_defaults.get("scaleB", 1) if saved_defaults else 1
    seed_default = saved_defaults.get("seed", 1) if saved_defaults else 1

    # dynamically adjust contrast, brightness, scaleR min/max values if necessary
    contrast_min = min(-3, contrast_default)
    contrast_max = max(3, contrast_default)
    brightness_min = min(-3, brightness_default)
    brightness_max = max(3, brightness_default)
    scaleR_min = min(-3, scaleR_default)
    scaleR_max = max(3, scaleR_default)
    scaleG_min = min(-3, scaleG_default)
    scaleG_max = max(3, scaleG_default)
    scaleB_min = min(-3, scaleB_default)
    scaleB_max = max(3, scaleB_default)
    scaleB_max = max(3, scaleB_default)
    seed_min = min(0, seed_default)
    seed_max = max(20, seed_default)

    shader.extend(
        [
            f"#uicontrol float contrast slider(min={contrast_min}, max={contrast_max}, step=0.01, default={contrast_default})",
            f"#uicontrol float brightness slider(min={brightness_min}, max={brightness_max}, step=0.01, default={brightness_default})",
            f"#uicontrol float scaleR slider(min={scaleR_min}, max={scaleR_max}, step=0.01, default={scaleR_default})",
            f"#uicontrol float scaleG slider(min={scaleG_min}, max={scaleG_max}, step=0.01, default={scaleG_default})",
            f"#uicontrol float scaleB slider(min={scaleB_min}, max={scaleB_max}, step=0.01, default={scaleB_default})",
            f"#uicontrol float seed slider(min={seed_min}, max={seed_max}, step=1, default={seed_default})",
            f"#uicontrol bool invert checkbox(default=false)",
        ]
    )

    # helper functions for display range and random shuffling
    shader.extend(
        [
            "float disp_range(float im, float min, float max) {",
            "    return clamp((im - min) / (max - min), 0.0, 1.0);",
            "}",
            "float rand(float x) {",
            "    return fract(sin(dot(vec2(x, seed), vec2(12.9898, 78.233))) * 43758.5453);",
            "}",
            f"vec3[{num_channels}] shuffleBoolArray(vec3 arr[{num_channels}], int n) {{",
            "    vec3[] output_arr = vec3[]("
            + ", ".join([f"arr[{i}]" for i in range(num_channels)])
            + ");",
            "    if (seed == 0.) {",
            "        return output_arr;",
            "    }",
            "    for (int i = n - 1; i > 0; i--) {",
            "        int j = int(rand(float(i)) * float(i + 1));",
            "        vec3 temp = output_arr[i];",
            "        output_arr[i] = output_arr[j];",
            "        output_arr[j] = temp;",
            "    }",
            "    return output_arr;",
            "}",
        ]
    )

    # base color pattern
    color_pattern = ["vec3(1, 0, 0)", "vec3(0, 1, 0)", "vec3(0, 0, 1)"]

    # repeat pattern for extra channels
    extended_colors = (color_pattern * ((num_channels + 2) // 3))[:num_channels]

    # convert to string
    temp_colors = ", ".join(extended_colors)

    # add to glsl
    temp_colors_definition = (
        f"vec3 temp_colors[{num_channels}] = vec3[]({temp_colors});"
    )

    # main logic
    shader.extend(
        [
            "void main() {",
            "    vec3 colorSum = vec3(0.0);",
            f"    float channelData[{num_channels}] = float[]("
            + ", ".join(
                [f"toNormalized(getDataValue({i}))" for i in range(num_channels)]
            )
            + ");",
            f"    float minVals[{num_channels}] = float[]("
            + ", ".join([f"chan{i}_min" for i in range(num_channels)])
            + ");",
            f"    float maxVals[{num_channels}] = float[]("
            + ", ".join([f"chan{i}_max" for i in range(num_channels)])
            + ");",
            f"    bool active_chans[{num_channels}] = bool[]("
            + ", ".join([f"chan{i}_active" for i in range(num_channels)])
            + ");",
            f"    {temp_colors_definition}",
            f"    vec3[{num_channels}] colors = shuffleBoolArray(temp_colors, {num_channels});",
            f"    for (int i = 0; i < {num_channels}; i++) {{",
            "        if (active_chans[i]) {",
            "            colorSum += colors[i] * disp_range(channelData[i], minVals[i], maxVals[i]);",
            "        }",
            "    }",
            "    vec3 final_im = vec3(colorSum.r * scaleR, colorSum.g * scaleG, colorSum.b * scaleB);",
            "    final_im = clamp(final_im, 0.0, 1.0);",
            "    final_im = (final_im - 0.5) * pow(2.0, contrast) + 0.5 + brightness;",
            "    if (invert == true) {emitRGB(1.0-final_im);} else {emitRGB(final_im);}"
            "}",
        ]
    )

    return "\n".join(shader)


def parse_dims(array):
    if type(array) == list:
        array = array[0]

    dims = len(array.data.shape)
    spatial_dims = array.roi.dims
    channel_dims = dims - spatial_dims

    print("dims        :", dims)
    print("spatial dims:", spatial_dims)
    print("channel dims:", channel_dims)

    return dims, spatial_dims, channel_dims


def create_coordinate_space(array, spatial_dim_names, channel_dim_names, unit, voxel_size):
    dims, spatial_dims, channel_dims = parse_dims(array)
    assert spatial_dims > 0

    if channel_dims > 0:
        channel_names = channel_dim_names[-channel_dims:]
    else:
        channel_names = []
    spatial_names = spatial_dim_names[-spatial_dims:]
    names = channel_names + spatial_names
    units = [""] * channel_dims + [unit] * spatial_dims

    scales = [1] * channel_dims + voxel_size

    print("Names    :", names)
    print("Units    :", units)
    print("Scales   :", scales)

    # print("Channel dim names: " + str(channel_dim_names))

    return neuroglancer.CoordinateSpace(names=names, units=units, scales=scales)


def create_shader_code(
    shader,
    channel_dims,
    rgb_channels=None,
    color=None,
    scale_factor=1.0,
    num_channels=None,
    channel=None
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

    if shader == "adjustable":
        return adjustable_shader_code % (
            rgb_channels[0],
            rgb_channels[1],
            rgb_channels[2],
        )
    
    if shader == "singlechannel":
        assert (
            channel is not None
        ), "Channel must be passed if using single channel shader"
        return singlechannel_shader_code % (
            int(num_channels),
            channel
        )
    if shader == "binary":
        return binary_shader_code

    if shader == "heatmap":
        return heatmap_shader_code

    if shader == "add":
        assert (
            num_channels is not None
        ), "Num channels must be passed if using additive shader"
        return additive_shader(num_channels)

    if shader == "cadd":
        assert (
            num_channels is not None
        ), "Num channels must be passed if using additive shader"
        return combined_additive_shader(num_channels)

    if shader == "shuffle":
        assert (
            num_channels is not None
        ), "Num channels must be passed if using additive shader"
        return create_shuffle_shader(num_channels)



    if shader == "random_color":
        random_color_css = generate_random_color()
        random_color_shader = f"""
            #uicontrol vec3 color color(default="{random_color_css}")
            #uicontrol float brightness slider(min=-1, max=1)
            #uicontrol float contrast slider(min=-3, max=3, step=0.01)
            void main() {{
            emitRGB(color *
                    (255.0*toNormalized(getDataValue(0)) + brightness) *
                    exp(contrast));
            }}
            """
        return random_color_shader


def add_layer(
    context,
    array,
    name,
    spatial_dim_names=None,
    channel_dim_names=None,
    opacity=None,
    shader=None,
    rgb_channels=None,
    color=None,
    visible=True,
    value_scale_factor=1.0,
    units="mm",
    volume_type=None,
    voxel_size=None,
    channel=None,
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

        spatial_dim_names:

            The names of the spatial dimensions. Defaults to ``['t', 'z', 'y',
            'x']``. The last elements of this list will be used (e.g., if your
            data is 2D, the channels will be ``['y', 'x']``).

        channel_dim_names:

            The names of the non-spatial (channel) dimensions. Defaults to
            ``['b^', 'c^']``.  The last elements of this list will be used
            (e.g., if your data is 2D but the shape of the array is 3D, the
            channels will be ``['c^']``).

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
                'add':  Dynamically adds channels and renders as rgb. Adds
                    invlerp sliders to adjust brightness
                'cadd':  Dynamically adds channels and renders as rgb. Adds
                    single slider to adjust bias
                'random_color': A random color between 0.5 and 1. Adds invlerp
                    sliders for brightness and contrast
                'shuffle' : Dynamically shuffles channels and renders as rgb.
                'adjustable' : similar to color, but allows adjusting range and color.
                'single_channel' : renders a single channel as grayscale. Adds invlerp slider to adjust brightness

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

        volume_type:

            An optional string defining the volume type. Should be one of "None, image",
            "segmentation". Defaults to None, and volume type is set based on
            array data type. Can be useful to override in some cases, for
            example if you have raw image data that is stored at 16 bit but
            don't want it rendered as a segmentation layer

        voxel_size:

            An optional list of ints denoting the voxel size to use. Defaults to
            None and voxel size is determined based on the array data voxel
            size. This can be useful if no voxel size is added to the zarr meta
            data in which case it defaults to 1 * spatial dims, unless
            overridden. If this is set then it assumes non multiscale data.
    """

    if channel_dim_names is None:
        channel_dim_names = ["b", "c^"]
    if channel is not None:
        channel_dim_names += ["c'"]
    if spatial_dim_names is None:
        spatial_dim_names = ["t", "z", "y", "x"]

    if rgb_channels is None:
        rgb_channels = [0, 1, 2]

    is_multiscale = False if voxel_size else type(array) == list

    dims, spatial_dims, channel_dims = parse_dims(array)

    if is_multiscale:
        dimensions = []
        for a in array:
            dimensions.append(
                create_coordinate_space(
                    a, spatial_dim_names, channel_dim_names, units, list(a.voxel_size)
                )
            )

        # why only one offset, shouldn't that be a list?
        voxel_offset = [0] * channel_dims + list(
            array[0].roi.offset / array[0].voxel_size
        )
        #     # added_data = a.data[channel:channel+1]

        layer = ScalePyramid(
            [
                neuroglancer.LocalVolume(
                    data=a.data,
                    voxel_offset=voxel_offset,
                    dimensions=array_dims,
                    volume_type=volume_type,
                )
                for a, array_dims in zip(array, dimensions)
            ]
        )

    else:
        voxel_size = array.voxel_size if voxel_size is None else voxel_size
        voxel_offset = [0] * channel_dims + list(
            array.roi.offset / Coordinate(voxel_size)
        )

        dimensions = create_coordinate_space(
            array, spatial_dim_names, channel_dim_names, units, list(voxel_size)
        )

        layer = neuroglancer.LocalVolume(
            data=array.data,
            voxel_offset=voxel_offset,
            dimensions=dimensions,
            volume_type=volume_type,
        )

    num_channels = (
        array[0].shape[0]
        if isinstance(array, (list, tuple))
        else array.shape[0]
        if shader is not None and "add" in shader
        else None
    )

    shader_code = create_shader_code(
        shader,
        channel_dims,
        rgb_channels,
        color,
        value_scale_factor,
        num_channels=num_channels,
        channel=channel
    )

    print(shader)

    print(shader_code)
    
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
