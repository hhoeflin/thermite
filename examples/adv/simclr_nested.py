from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from thermite import Config, Event, run
from thermite.pp_utils import multi_extend, multi_str_replace, pg_trigger_map


@dataclass(kw_only=True)
class GPU:
    """
    GPU settings

    Args:
        fp16_precision: Whether or not to use 16bit GPU precision
        disable_cuda: Disable CUDA
        gpu_index: Gpu index

    """

    fp16_precision: bool = False
    disable_cuda: bool = False
    index: int = 0


@dataclass(kw_only=True)
class Model:
    """
    Model description

    Args:
        arch: Model architectures
        out_dim: Feature Dimension of SimCLR projection

    """

    arch: Literal["resnet18", "resnet50"] = "resnet50"
    out_dim: int = 128


@dataclass(kw_only=True)
class Data:
    """
    Data description

    Args:
        data: Path to dataset
        dataset_name: Name of the dataset to use

    """

    path: Path = Path("./datasets")
    name: Literal["stl10", "cifar10"] = "stl10"


@dataclass(kw_only=True)
class Training:
    """
    Config for training

    Args:
        workers: Number of data loading workers
        epochs: Number of epochs to run
        batch_size: Mini-batch-size. Total of all GPUs on a node
        learning_rate: Initial learning rate
        weight_decay: Optimizer weight decay
        seed: Seed for initializing training
        log_every_n_steps: Number of steps between logging
        temperature: Softmax temperature
        n_views: Number of views for contrastive learning

    """

    workers: int = 12
    epochs: int = 200
    batch_size: int = 256
    learning_rate: float = 0.0003
    weight_decay: float = 1e-4
    seed: int
    log_every_n_steps: int = 100
    temperature: float = 0.07
    n_views: int = 2


@dataclass(kw_only=True)
class PytorchSimCLR:
    """
    PyTorch SimCLR training

    Args:
        data: dataset config
        gpu: Gpu settings
        model: Model description
    """

    data: Data
    train_vars: Training
    gpu: GPU
    model: Model

    def train(self):
        """Training the model."""
        ...


if __name__ == "__main__":
    config = Config()
    config.event_cb_deco(Event.PG_POST_CREATE, PytorchSimCLR)(
        pg_trigger_map(multi_str_replace({"--train-vars-": "--"}))
    )
    config.event_cb_deco(Event.PG_POST_CREATE, PytorchSimCLR)(
        pg_trigger_map(
            multi_extend(
                {
                    "--model-arch": "-a",
                    "--workers": "-j",
                    "--batch-size": "-b",
                    "--learning-rate": "--lr",
                    "--weight-decay": "--wd",
                }
            )
        )
    )
    run(PytorchSimCLR, config=config)
