from scale_pyramid import ScalePyramid

def add_layer(context, array, name, shader=None):
    '''Add a layer to a neuroglancer context.

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

        shader:

            A string to be used as the shader. If set to ``'rgb'``, an RGB
            shader will be used.
    '''

    if shader == 'rgb':
        shader="""
void main() {
    emitRGB(
        vec3(
            toNormalized(getDataValue(0)),
            toNormalized(getDataValue(1)),
            toNormalized(getDataValue(2)))
        );
}"""

    kwargs = {}

    if shader is not None:
        kwargs['shader'] = shader

    is_multiscale = type(array) == list

    if is_multiscale:

        for v in array:
            print("voxel size: ", v.voxel_size)

        layer = ScalePyramid(
            [
                neuroglancer.LocalVolume(
                    data=v.data,
                    offset=v.roi.get_offset()[::-1],
                    voxel_size=v.voxel_size[::-1])
                for v in array
            ])
    else:
        layer = neuroglancer.LocalVolume(
            data=array.data,
            offset=array.roi.get_offset()[::-1],
            voxel_size=array.voxel_size[::-1])

    context.layers.append(
            name=name,
            layer=layer,
            **kwargs)
