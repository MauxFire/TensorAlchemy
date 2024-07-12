from typing import Dict, Optional

import torch
from base import BaseMiner
from diffusers import (
    AutoPipelineForImage2Image,
    AutoPipelineForText2Image,
    DPMSolverMultistepScheduler,
)
from loguru import logger
from neurons.miners.StableMiner.schema import ModelConfig, TaskType, TaskConfig
from neurons.protocol import ModelType
from neurons.safety import StableDiffusionSafetyChecker
from transformers import CLIPImageProcessor
from utils import warm_up

TASK_CONFIG = {
    TaskType.TEXT_TO_IMAGE: TaskConfig(
        pipeline=AutoPipelineForText2Image,
        torch_dtype=torch.float16,
        use_safetensors=True,
        variant="fp16",
    ),
    TaskType.IMAGE_TO_IMAGE: TaskConfig(
        pipeline=AutoPipelineForImage2Image,
        torch_dtype=torch.float16,
        use_safetensors=True,
        variant="fp16",
    ),
}


class StableMiner(BaseMiner):
    def __init__(self) -> None:
        self.model_configs: Dict[ModelType, Dict[TaskType, ModelConfig]] = {}
        self.safety_checker: Optional[StableDiffusionSafetyChecker] = None
        self.processor: Optional[CLIPImageProcessor] = None

        super().__init__()

        try:
            logger.info("Initializing StableMiner...")

            # Load the models
            self.load_models()

            # Optimize model
            self.optimize_models()

            # Serve the axon
            self.start_axon()

            # Start the miner loop
            self.loop()
        except Exception as e:
            logger.error(f"Error in StableMiner initialization: {e}")
            raise

    def load_models(self) -> None:
        try:
            logger.info("Loading safety checker...")
            self.safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                "CompVis/stable-diffusion-safety-checker"
            ).to(self.config.miner.device)

            logger.info("Loading image processor...")
            self.processor = CLIPImageProcessor()

            logger.info("Setting up model configurations...")
            self.setup_model_configs()
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise

    def get_model_config(
        self,
        model_type: ModelType,
        task_type: TaskType,
    ) -> ModelConfig:
        try:
            if model_type not in self.model_configs:
                raise ValueError(f"{model_type} was not found in model_configs!")

            if task_type not in self.model_configs[model_type]:
                raise ValueError(
                    f"{task_type} was not found in model_configs {model_type}!"
                )

            return self.model_configs[model_type][task_type]
        except ValueError as e:
            logger.error(e)
            raise

    def load_model(self, model_name: str, task_type: TaskType) -> torch.nn.Module:
        try:
            logger.info(f"Loading model {model_name} for task {task_type}...")
            config = TASK_CONFIG[task_type]
            pipeline_class = config.pipeline
            model = pipeline_class.from_pretrained(
                model_name,
                torch_dtype=config.torch_dtype,
                use_safetensors=config.use_safetensors,
                variant=config.variant,
            )

            model.to(self.config.miner.device)
            model.set_progress_bar_config(disable=True)
            model.scheduler = DPMSolverMultistepScheduler.from_config(
                model.scheduler.config
            )

            logger.info(f"Model {model_name} loaded successfully.")
            return model
        except Exception as e:
            logger.error(f"Error loading {task_type.value} model: {e}")
            raise

    def setup_model_configs(self) -> None:
        logger.info("Setting up model configurations...")
        self.model_configs = {
            ModelType.CUSTOM: {
                TaskType.TEXT_TO_IMAGE: ModelConfig(
                    args=self.t2i_args,
                    model=self.load_model(
                        self.config.miner.custom_model, TaskType.TEXT_TO_IMAGE
                    ),
                ),
                # TaskType.IMAGE_TO_IMAGE: ModelConfig(
                #     args=self.i2i_args,
                #     model=self.load_model(self.config.miner.custom_model, TaskType.IMAGE_TO_IMAGE),
                # ),
            },
            # ModelType.ALCHEMY: {
            #     TaskType.TEXT_TO_IMAGE: ModelConfig(
            #         args=self.t2i_args,
            #         model=self.load_model(self.config.miner.alchemy_model, TaskType.TEXT_TO_IMAGE),
            #     ),
            #     TaskType.IMAGE_TO_IMAGE: ModelConfig(
            #         args=self.i2i_args,
            #         model=self.load_model(self.config.miner.alchemy_model, TaskType.IMAGE_TO_IMAGE),
            #     ),
            # },
        }
        logger.info("Model configurations set up successfully.")

    def optimize_models(self) -> None:
        logger.info("Optimizing models...")
        # TODO: the code before was only doing this for alchemy and was deactivated
        # decide if we want to run this all or only for alchemy; for now leaving as deactive
        if self.config.miner.optimize:
            try:
                for model_type, tasks in self.model_configs.items():
                    for task_type, config in tasks.items():
                        if config.model:
                            config.model.unet = torch.compile(
                                config.model.unet,
                                mode="reduce-overhead",
                                fullgraph=True,
                            )

                            # Warm up model
                            logger.info(
                                f">>> Warming up {model_type} {task_type} model with compile... "
                                "this takes roughly two minutes...",
                                color="yellow",
                            )
                            warm_up(config.model, config.args)
                logger.info("Models optimized successfully.")
            except Exception as e:
                logger.error(f"Error optimizing models: {e}")
                raise
        else:
            logger.info("Model optimization is disabled.")
