import os
import pathlib
import sys
import warnings
import traceback

import torch
from diffusers import (
    AutoPipelineForText2Image,
    AutoPipelineForImage2Image,
    DPMSolverMultistepScheduler,
    DiffusionPipeline,
)
from transformers import CLIPImageProcessor

from loguru import logger

from neurons.protocol import ModelType

# Suppress the eth_utils network warnings
# "does not have a valid ChainId."
# NOTE: It's not our bug, it's upstream
# TODO: Remove after updating bittensor
warnings.simplefilter("ignore")

# Use the older torch style for now
os.environ["USE_TORCH"] = "1"

if __name__ == "__main__":
    try:
        # Add the base repository to the path so the miner can access it
        file_path: str = str(
            pathlib.Path(__file__).parent.parent.parent.parent.resolve(),
        )
        if file_path not in sys.path:
            sys.path.append(file_path)
        from neurons.miners.StableMiner.schema import TaskType, TaskConfig
        from neurons.miners.StableMiner.stable_miner import StableMiner
        from neurons.safety import StableDiffusionSafetyChecker

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
                safety_checker_model_name="CompVis/stable-diffusion-safety-checker",
                processor=CLIPImageProcessor,
                refiner_class=DiffusionPipeline,
                refiner_model_name="stabilityai/stable-diffusion-xl-refiner-1.0",
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
                safety_checker_model_name="CompVis/stable-diffusion-safety-checker",
                processor=CLIPImageProcessor,
                refiner_class=DiffusionPipeline,
                refiner_model_name="stabilityai/stable-diffusion-xl-refiner-1.0",
            ),
        ]
        # Start the miner
        StableMiner(task_configs)
    except ImportError:
        logger.error(f"Error: {traceback.format_exc()}")
        logger.error("Please ensure all required packages are installed.")
        sys.exit(1)
    except Exception:
        logger.error(f"Error: {traceback.format_exc()}")
        sys.exit(1)
