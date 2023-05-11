"""
Base class and implementation for an cli-args splitter.

It yields the next set of arguments to be processed.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Sequence

from .preprocessing import split_and_expand, undeque

if TYPE_CHECKING:
    from .command import Command


class CliArgsSplitter(ABC):
    @abstractmethod
    def __init__(self, input_args: List[str], cmd: "Command"):
        ...

    @abstractmethod
    def next(self) -> Optional[List[str]]:
        ...

    @abstractmethod
    def add_remain(self, remain_args: Sequence[str]):
        ...

    @abstractmethod
    def final(self) -> List[str]:  # type: ignore
        ...


class EagerCliArgsSplitter:
    def __init__(self, input_args: List[str], cmd: "Command"):
        self.cmd = cmd
        self.deque = split_and_expand(input_args)

    def next(self) -> Optional[List[str]]:
        if len(self.deque) > 0:
            return self.deque.popleft()
        else:
            return None

    def add_remain(self, remain_args: Sequence[str]):
        if len(remain_args) > 0:
            self.deque.appendleft(list(remain_args))

    def final(self) -> List[str]:
        return undeque(self.deque)
