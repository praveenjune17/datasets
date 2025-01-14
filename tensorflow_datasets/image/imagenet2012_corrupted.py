# coding=utf-8
# Copyright 2019 The TensorFlow Datasets Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Corrupted ImageNet2012 dataset.

Apply common corruptions to the validation images in ImageNet2012 dataset.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from absl import logging
import numpy as np
import tensorflow as tf
from tensorflow_datasets.core import api_utils
from tensorflow_datasets.image import corruptions
from tensorflow_datasets.image.imagenet import Imagenet2012
import tensorflow_datasets.public_api as tfds

_DESCRIPTION = """\
Imagenet2012Corrupted is a dataset generated by adding common corruptions to the
validation images in the ImageNet dataset. In the original paper, there are
15 different corruptions, and each has 5 levels of severity. In this dataset,
we implement 12 out of the 15 corruptions, including Gaussian noise, shot noise,
impulse_noise, defocus blur, frosted glass blur, zoom blur, fog, brightness,
contrast, elastic, pixelate, and jpeg compression. The randomness is fixed so
that regeneration is deterministic.
"""

_CITATION = """\
@inproceedings{
  hendrycks2018benchmarking,
  title={Benchmarking Neural Network Robustness to Common Corruptions and Perturbations},
  author={Dan Hendrycks and Thomas Dietterich},
  booktitle={International Conference on Learning Representations},
  year={2019},
  url={https://openreview.net/forum?id=HJz6tiCqYm},
}
"""

_LABELS_FNAME = 'image/imagenet2012_labels.txt'

# This file contains the validation labels, in the alphabetic order of
# corresponding image names (and not in the order they have been added to the
# tar file).
_VALIDATION_LABELS_FNAME = 'image/imagenet2012_validation_labels.txt'

TYPE_LIST = [
    'gaussian_noise', 'shot_noise', 'impulse_noise', 'defocus_blur',
    'frosted_glass_blur', 'zoom_blur', 'fog', 'brightness', 'contrast',
    'elastic', 'pixelate', 'jpeg_compression'
]


class Imagenet2012CorruptedConfig(tfds.core.BuilderConfig):
  """BuilderConfig for Imagenet2012Corrupted."""

  @api_utils.disallow_positional_args
  def __init__(self, corruption_type=None, severity=1, **kwargs):
    """BuilderConfig for Imagenet2012Corrupted.

    Args:
      corruption_type: string, must be one of the items in TYPE_LIST.
      severity: integer, bewteen 1 and 5.
      **kwargs: keyword arguments forwarded to super.
    """
    super(Imagenet2012CorruptedConfig, self).__init__(**kwargs)
    self.corruption_type = corruption_type
    self.severity = severity


_VERSION = tfds.core.Version('0.0.1',
                             experiments={tfds.core.Experiment.S3: False})
_SUPPORTED_VERSIONS = [
    # Will be made canonical in near future.
    tfds.core.Version('3.0.0'),
]
# Version history:
# 3.0.0: Fix colorization (all RGB) and format (all jpeg); use TAR_STREAM.
#        (jump to match imagenet version).
# 0.0.1: Initial dataset.


def _make_builder_configs():
  """Construct a list of BuilderConfigs.

  Construct a list of 60 Imagenet2012CorruptedConfig objects, corresponding to
  the 12 corruption types, with each type having 5 severities.

  Returns:
    A list of 60 Imagenet2012CorruptedConfig objects.
  """
  config_list = []
  for each_corruption in TYPE_LIST:
    for each_severity in range(1, 6):
      name_str = each_corruption + '_' + str(each_severity)
      description_str = 'corruption type = ' + each_corruption + ', severity = '
      description_str += str(each_severity)
      config_list.append(
          Imagenet2012CorruptedConfig(
              name=name_str,
              version=_VERSION,
              supported_versions=_SUPPORTED_VERSIONS,
              description=description_str,
              corruption_type=each_corruption,
              severity=each_severity,
          ))
  return config_list


class Imagenet2012Corrupted(Imagenet2012):
  """Corrupted ImageNet2012 dataset."""
  BUILDER_CONFIGS = _make_builder_configs()

  def _info(self):
    """Basic information of the dataset.

    Returns:
      tfds.core.DatasetInfo.
    """
    names_file = tfds.core.get_tfds_path(_LABELS_FNAME)
    return tfds.core.DatasetInfo(
        builder=self,
        description=_DESCRIPTION,
        features=tfds.features.FeaturesDict({
            'image': tfds.features.Image(),
            'label': tfds.features.ClassLabel(names_file=names_file),
            'file_name': tfds.features.Text(),  # Eg: 'n15075141_54.JPEG'
        }),
        supervised_keys=('image', 'label'),
        urls=['https://openreview.net/forum?id=HJz6tiCqYm'],
        citation=_CITATION,
    )

  def _split_generators(self, dl_manager):
    """Return the validation split of ImageNet2012.

    Args:
      dl_manager: download manager object.

    Returns:
      validation split.
    """
    splits = super(Imagenet2012Corrupted, self)._split_generators(dl_manager)
    validation = splits[1]
    return [validation]

  def _generate_examples_validation(self, archive, labels):
    """Generate corrupted imagenet validation data.

    Apply corruptions to the raw images according to self.corruption_type.

    Args:
      archive: an iterator for the raw dataset.
      labels: a dictionary that maps the file names to imagenet labels.

    Yields:
      dictionary with the file name, an image file objective, and label of each
      imagenet validation data.
    """
    # Get the current random seeds.
    numpy_st0 = np.random.get_state()
    # Set new random seeds.
    np.random.seed(135)
    logging.warning('Overwriting cv2 RNG seed.')
    tfds.core.lazy_imports.cv2.setRNGSeed(357)

    for example in super(Imagenet2012Corrupted,
                         self)._generate_examples_validation(archive, labels):
      with tf.Graph().as_default():
        tf_img = tf.image.decode_jpeg(example['image'].read(), channels=3)
        image_np = tfds.as_numpy(tf_img)
      example['image'] = self._get_corrupted_example(image_np)
      yield example
    # Reset the seeds back to their original values.
    np.random.set_state(numpy_st0)

  def _get_corrupted_example(self, x):
    """Return corrupted images.

    Args:
      x: numpy array, uncorrupted image.

    Returns:
      numpy array, corrupted images.
    """
    corruption_type = self.builder_config.corruption_type
    severity = self.builder_config.severity

    return {
        'gaussian_noise': corruptions.gaussian_noise,
        'shot_noise': corruptions.shot_noise,
        'impulse_noise': corruptions.impulse_noise,
        'defocus_blur': corruptions.defocus_blur,
        'frosted_glass_blur': corruptions.frosted_glass_blur,
        'zoom_blur': corruptions.zoom_blur,
        'fog': corruptions.fog,
        'brightness': corruptions.brightness,
        'contrast': corruptions.contrast,
        'elastic': corruptions.elastic,
        'pixelate': corruptions.pixelate,
        'jpeg_compression': corruptions.jpeg_compression,
    }[corruption_type](x, severity)
