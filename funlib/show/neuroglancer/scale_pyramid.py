import neuroglancer
import operator
import logging

logger = logging.getLogger(__name__)

class ScalePyramid(neuroglancer.LocalVolume):
    '''A neuroglancer layer that provides volume data on different scales.
    Mimics a LocalVolume.

    Args:

            volume_layers (``list`` of ``LocalVolume``):

                One ``LocalVolume`` per provided resolution.
    '''

    def __init__(self, volume_layers):

        super(neuroglancer.LocalVolume, self).__init__()

        logger.debug("Creating scale pyramid...")
        for l in volume_layers:
            logger.debug("volume layer voxel_size: %s", l.voxel_size)

        self.min_voxel_size = min(
            [
                tuple(l.voxel_size)
                for l in volume_layers
            ]
        )

        self.volume_layers = {
            tuple(map(operator.truediv, l.voxel_size, self.min_voxel_size)): l
            for l in volume_layers
        }

        logger.debug("min_voxel_size: %s", self.min_voxel_size)
        logger.debug("scale keys: %s", self.volume_layers.keys())
        logger.debug(self.info())

    @property
    def volume_type(self):
        return self.volume_layers[(1,1,1)].volume_type

    @property
    def token(self):
        return self.volume_layers[(1,1,1)].token

    def info(self):

        scales = []

        for scale, layer in sorted(self.volume_layers.items()):

            # TODO: support 2D
            scale_info = layer.info()['threeDimensionalScales'][0]
            scale_info['key'] = ','.join('%d'%s for s in scale)
            scales.append(scale_info)

        reference_layer = self.volume_layers[(1, 1, 1)]

        info = {
            'volumeType': reference_layer.volume_type,
            'dataType': reference_layer.data_type,
            'maxVoxelsPerChunkLog2': 20,    # Default is 18
            'encoding': reference_layer.encoding,
            'numChannels': reference_layer.num_channels,
            'generation': reference_layer.change_count,
            'threeDimensionalScales': scales
        }

        return info

    def get_encoded_subvolume(self, data_format, start, end, scale_key='1,1,1'):

        scale = tuple(int(s) for s in scale_key.split(','))

        return self.volume_layers[scale].get_encoded_subvolume(
            data_format,
            start,
            end,
            scale_key='1,1,1')

    def get_object_mesh(self, object_id):
        return self.volume_layers[(1,1,1)].get_object_mesh(object_id)

    def invalidate(self):
        return self.volume_layers[(1,1,1)].invalidate()
