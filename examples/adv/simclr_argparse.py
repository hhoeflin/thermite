"""
Code taken and adapted from: 
https://github.com/sthalles/SimCLR/blob/master/run.py
Original code under MIT license.
"""
import argparse

model_names = ["resnet18", "resnet50"]


parser = argparse.ArgumentParser(description="PyTorch SimCLR")
parser.add_argument(
    "-data", metavar="DIR", default="./datasets", help="path to dataset"
)
parser.add_argument(
    "-dataset-name", default="stl10", help="dataset name", choices=["stl10", "cifar10"]
)
parser.add_argument(
    "-a",
    "--arch",
    metavar="ARCH",
    default="resnet18",
    choices=model_names,
    help="model architecture: " + " | ".join(model_names) + " (default: resnet50)",
)
parser.add_argument(
    "-j",
    "--workers",
    default=12,
    type=int,
    metavar="N",
    help="number of data loading workers (default: 32)",
)
parser.add_argument(
    "--epochs", default=200, type=int, metavar="N", help="number of total epochs to run"
)
parser.add_argument(
    "-b",
    "--batch-size",
    default=256,
    type=int,
    metavar="N",
    help="mini-batch size (default: 256), this is the total "
    "batch size of all GPUs on the current node when "
    "using Data Parallel or Distributed Data Parallel",
)
parser.add_argument(
    "--lr",
    "--learning-rate",
    default=0.0003,
    type=float,
    metavar="LR",
    help="initial learning rate",
    dest="lr",
)
parser.add_argument(
    "--wd",
    "--weight-decay",
    default=1e-4,
    type=float,
    metavar="W",
    help="weight decay (default: 1e-4)",
    dest="weight_decay",
)
parser.add_argument(
    "--seed", default=None, type=int, help="seed for initializing training. "
)
parser.add_argument("--disable-cuda", action="store_true", help="Disable CUDA")
parser.add_argument(
    "--fp16-precision",
    action="store_true",
    help="Whether or not to use 16-bit precision GPU training.",
)

parser.add_argument(
    "--out_dim", default=128, type=int, help="feature dimension (default: 128)"
)
parser.add_argument(
    "--log-every-n-steps", default=100, type=int, help="Log every n steps"
)
parser.add_argument(
    "--temperature",
    default=0.07,
    type=float,
    help="softmax temperature (default: 0.07)",
)
parser.add_argument(
    "--n-views",
    default=2,
    type=int,
    metavar="N",
    help="Number of views for contrastive learning training.",
)
parser.add_argument("--gpu-index", default=0, type=int, help="Gpu index.")


def main():
    args = parser.parse_args()

    # production code would follow here


if __name__ == "__main__":
    main()
