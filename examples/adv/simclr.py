# from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from attrs import mutable

from thermite import run


@mutable(kw_only=True)
class Config:
    """
    Config for PyTorch SimCLR

    Args:
        data: Path to dataset
        dataset_name: Name of the dataset to use
        arch: Model architectures
        workers: Number of data loading workers
        epochs: Number of epochs to run
        batch_size: Mini-batch-size. Total of all GPUs on a node
        learning_rate: Initial learning rate
        weight_decay: Optimizer weight decay
        seed: Seed for initializing training
        fp16_precision: Whether or not to use 16bit GPU precision
        disable_cuda: Disable CUDA
        out_dim: Feature Dimension of SimCLR projection
        log_every_n_steps: Number of steps between logging
        temperature: Softmax temperature
        n_views: Number of views for contrastive learning
        gpu_index: Gpu index
    """

    data: Path = Path("./datasets")
    dataset_name: Literal["stl10", "cifar10"] = "stl10"
    arch: Literal["resnet18", "resnet50"] = "resnet50"
    workers: int = 12
    epochs: int = 200
    batch_size: int = 256
    learning_rate: float = 0.0003
    weight_decay: float = 1e-4
    seed: int
    fp16_precision: bool = False
    disable_cuda: bool = False
    out_dim: int = 128
    log_every_n_steps: int = 100
    temperature: float = 0.07
    n_views: int = 2
    gpu_index: int = 0


if __name__ == "__main__":
    run(Config)
