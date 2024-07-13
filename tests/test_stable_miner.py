import os
import unittest
from unittest.mock import patch, MagicMock
from diffusers import (
    AutoPipelineForText2Image,
    AutoPipelineForImage2Image,
    DPMSolverMultistepScheduler,
)
import torch

from neurons.miners.StableMiner.model_loader import ModelLoader
from neurons.miners.StableMiner.schema import TaskType, TaskConfig
from neurons.miners.StableMiner.stable_miner import StableMiner
from neurons.protocol import ModelType
from neurons.safety import StableDiffusionSafetyChecker
from transformers import CLIPImageProcessor


class TestStableMiner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["USE_TORCH"] = "1"

    @patch("neurons.miners.StableMiner.stable_miner.ModelLoader.load")
    @patch("neurons.miners.StableMiner.stable_miner.ModelLoader.load_safety_checker")
    @patch("neurons.miners.StableMiner.stable_miner.ModelLoader.load_processor")
    def test_initialization(
        self, mock_load_processor, mock_load_safety_checker, mock_load_model
    ):
        mock_model = MagicMock()
        mock_safety_checker = MagicMock()
        mock_processor = MagicMock()
        mock_load_model.return_value = mock_model
        mock_load_safety_checker.return_value = mock_safety_checker
        mock_load_processor.return_value = mock_processor

        task_configs = [
            TaskConfig(
                model_type=ModelType.CUSTOM,
                task_type=TaskType.TEXT_TO_IMAGE,
                pipeline=AutoPipelineForText2Image,
                torch_dtype=torch.float16,
                use_safetensors=True,
                variant="fp16",
                scheduler=DPMSolverMultistepScheduler,
                safety_checker=StableDiffusionSafetyChecker,
                processor=CLIPImageProcessor,
            ),
            TaskConfig(
                model_type=ModelType.CUSTOM,
                task_type=TaskType.IMAGE_TO_IMAGE,
                pipeline=AutoPipelineForImage2Image,
                torch_dtype=torch.float16,
                use_safetensors=True,
                variant="fp16",
                scheduler=DPMSolverMultistepScheduler,
                safety_checker=StableDiffusionSafetyChecker,
                processor=CLIPImageProcessor,
            ),
        ]

        miner = StableMiner(task_configs)

        self.assertEqual(mock_load_model.call_count, 2)
        self.assertEqual(mock_load_safety_checker.call_count, 2)
        self.assertEqual(mock_load_processor.call_count, 2)

        self.assertIsNotNone(miner.safety_checkers)
        self.assertIsNotNone(miner.processors)
        self.assertIsNotNone(miner.model_configs)

    @patch("neurons.miners.StableMiner.stable_miner.ModelLoader.load")
    def test_load_model(self, mock_load_model):
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model

        task_config = TaskConfig(
            model_type=ModelType.CUSTOM,
            task_type=TaskType.TEXT_TO_IMAGE,
            pipeline=AutoPipelineForText2Image,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
            scheduler=DPMSolverMultistepScheduler,
            safety_checker=None,
            processor=None,
        )

        loader = ModelLoader(config=MagicMock())

        model = loader.load("dummy_model_name", task_config)

        self.assertEqual(model, mock_model)
        mock_load_model.assert_called_once_with("dummy_model_name", task_config)


if __name__ == "__main__":
    unittest.main()
