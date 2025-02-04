import logging
from typing import Any, ClassVar, Dict, List, Sequence, Tuple, Type, Union

import cv2
import numpy as np
import numpy.typing as npt

from ..._utils import validate_postprocessor_type
from ...types import (
    Format,
    ImageClassificationModel,
    Metadata,
    Platform,
    PostProcessor,
    PreProcessor,
    Publication,
    PythonPostProcessor,
)
from ..common.datasets import imagenet1k
from ..preprocess import center_crop, read_image_opencv_if_needed, resize_with_aspect_ratio

CLASSES: List[str] = imagenet1k.ImageNet1k_CLASSES

logger = logging.getLogger(__name__)


class ResNet50PreProcessor(PreProcessor):
    @staticmethod
    def __call__(
        image: Union[str, npt.ArrayLike], with_scaling: bool = False
    ) -> Tuple[np.ndarray, None]:
        """Convert an input image to a model input tensor

        Args:
            image: A path of an image or
                an image loaded as a numpy array in BGR order.
            with_scaling: Whether to apply model-specific techniques that involve scaling the
                model's input and converting its data type to float32. Refer to the code to gain a
                precise understanding of the techniques used. Defaults to False.

        Returns:
            The first element of the tuple is a numpy array that meets the input requirements of the
                ResNet50 model. The second element of the tuple is unused in this model and has no
                value. To learn more information about the output numpy array, please refer to
                [Inputs](resnet50_v1.5.md#inputs).
        """
        # https://github.com/mlcommons/inference/blob/af7f5a0b856402b9f461002cfcad116736a8f8af/vision/classification_and_detection/python/main.py#L37-L39
        # https://github.com/mlcommons/inference/blob/af7f5a0b856402b9f461002cfcad116736a8f8af/vision/classification_and_detection/python/dataset.py#L168-L184
        image = read_image_opencv_if_needed(image)
        assert image.dtype == np.uint8
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = resize_with_aspect_ratio(
            image, 224, 224, percent=87.5, interpolation=cv2.INTER_AREA
        )
        image = center_crop(image, 224, 224)
        if with_scaling:
            image = np.asarray(image, dtype=np.float32)
            # https://github.com/mlcommons/inference/blob/af7f5a0b856402b9f461002cfcad116736a8f8af/vision/classification_and_detection/python/dataset.py#L178
            image -= np.array([123.68, 116.78, 103.94], dtype=np.float32)
        image = image.transpose([2, 0, 1])
        return image[np.newaxis, ...], None


class ResNet50PostProcessor(PythonPostProcessor):
    """Convert the outputs of a model to a label string, such as car and cat.

    Args:
        model_outputs: the outputs of the model.
            Please learn more about the output of model,
            please refer to [Outputs](resnet50_v1.5.md#outputs).

    Returns:
        str: A classified label, e.g., "tabby, tabby cat".
    """

    def __call__(self, model_outputs: Sequence[npt.ArrayLike], contexts: Any = None) -> str:
        return CLASSES[int(model_outputs[0]) - 1]


class ResNet50(ImageClassificationModel):
    """MLCommons ResNet50 model"""

    postprocessor_map: ClassVar[Dict[Platform, Type[PostProcessor]]] = {
        Platform.PYTHON: ResNet50PostProcessor,
    }

    def __init__(self, *, postprocessor_type: Union[str, Platform] = Platform.PYTHON):
        postprocessor_type = Platform(postprocessor_type)
        validate_postprocessor_type(postprocessor_type, self.postprocessor_map.keys())
        super().__init__(
            name="ResNet50",
            format=Format.ONNX,
            family="ResNet",
            version="v1.5",
            metadata=Metadata(
                description="ResNet50 v1.5 int8 ImageNet-1K",
                publication=Publication(url="https://arxiv.org/abs/1512.03385.pdf"),
            ),
            preprocessor=ResNet50PreProcessor(),
            postprocessor=self.postprocessor_map[postprocessor_type](),
        )

        self._artifact_name = "mlcommons_resnet50_v1.5"
