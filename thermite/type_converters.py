from abc import ABC, abstractmethod
from enum import Enum
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    final,
    get_args,
    get_origin,
)

from attrs import field, mutable


class TooFewArgsError(Exception):
    ...


class TooManyArgsError(Exception):
    ...


class NoBoundArgsError(Exception):
    ...


class UnequalNumberArgsError(Exception):
    ...


class RebindingError(Exception):
    ...


class CLIArgConverterError(Exception):
    ...


def args_used(num_offered: int, num_req: Union[int, slice]) -> int:
    if isinstance(num_req, int):
        if num_req <= num_offered:
            return num_req
        else:
            raise TooFewArgsError(
                f"Required {str(num_req)} but was offered {str(num_offered)}"
            )
    else:
        # it is a slice
        num_req_min = min(0, num_req.start) if num_req.start is not None else 0
        num_req_step: int = 1 if num_req.step is None else num_req.step
        num_req_max: int = (
            num_req.stop - num_req_step if num_req.stop is not None else None
        )
        if num_req_step < 1:
            raise ValueError(
                f"Step in slice has to be positive but was {str(slice.step)}"
            )

        if num_offered < num_req_min:
            raise TooFewArgsError(
                f"Required {num_req_min} but got {num_offered} arguments."
            )

        num_surplus = num_offered - num_req_min
        num_surplus_used = num_surplus // num_req_step

        num_used = num_req_min + num_surplus_used

        if num_req_max is not None and num_used >= num_req_max:
            num_used = num_req_max

        return num_used


def check_correct_nargs(num_offered: int, num_req: Union[int, slice]) -> None:
    num_used = args_used(num_offered, num_req)

    if num_used < num_offered:
        raise TooManyArgsError(
            f"Required {str(num_req)} but was offered {str(num_offered)}"
        )


def split_args_by_nargs(
    x: Sequence[str], num_req_args: Union[int, slice]
) -> Tuple[Sequence[str], Sequence[str]]:
    num_args_used = args_used(num_offered=len(x), num_req=num_req_args)
    return (x[:num_args_used], x[num_args_used:])


@mutable
class CLIArgConverterBase(ABC):
    num_req_args: Union[int, slice] = field(init=False)

    @property
    @abstractmethod
    def target_type(self) -> Type:
        ...

    @abstractmethod
    def _convert(self, args: Sequence[str]) -> Any:
        ...

    @final
    def convert(self, args: Sequence[str]) -> Any:
        check_correct_nargs(len(args), self.num_req_args)
        return self._convert(args)


@mutable
class BasicCLIArgConverter(CLIArgConverterBase):
    supported_type: Type
    conv_func: Callable
    target_type: Type

    def __attrs_post_init__(self) -> None:
        self.num_req_args = 1
        if self.target_type != self.supported_type:
            raise TypeError(
                f"{str(self.target_type)} not same as "
                f"supported type {str(self.supported_type)}"
            )

    def _convert(self, args: Sequence[str]) -> Any:
        return self.conv_func(*args)

    @classmethod
    def factory(
        cls,
        target_type: Type,
        store: "CLIArgConverterStore",
        supported_type: Type,
        conv_func: Optional[Callable] = None,
    ):
        del store
        if conv_func is None:
            conv_func = supported_type
        return cls(
            supported_type=supported_type, target_type=target_type, conv_func=conv_func
        )


# TODO: Should the next classes have base BasicCLIArgConverter?
@mutable
class LiteralCLIArgConverter(CLIArgConverterBase):
    target_type: Type
    _args_mapper: Dict[str, Any] = field(factory=dict, init=False)

    def __attrs_post_init__(self) -> None:
        self.num_req_args = 1
        if not get_origin(self.target_type) == get_origin(Literal["a", "b"]):
            raise TypeError(f"{str(self.target_type)} is not of type 'Literal'")
        literal_args = get_args(self.target_type)
        self._args_mapper = {str(arg): arg for arg in literal_args}
        # need to make sure that no args are duplicated
        if len(self._args_mapper) < len(literal_args):
            raise ValueError(
                f"Type {str(self.target_type)} has duplicate values "
                "when converted to string."
            )

    def _convert(self, args: Sequence[str]) -> Any:
        if args[0] in self._args_mapper:
            return self._args_mapper[args[0]]
        else:
            raise ValueError(f"{args[0]} not part of {str(self.target_type)}")

    @classmethod
    def factory(cls, target_type: Type, store: "CLIArgConverterStore"):
        del store
        return cls(target_type=target_type)


@mutable
class EnumCLIArgConverter(CLIArgConverterBase):
    target_type: Type
    _args_mapper: Dict[str, Any] = field(factory=dict, init=False)

    def __attrs_post_init__(self) -> None:
        self.num_req_args = 1
        if not issubclass(self.target_type, Enum):
            raise TypeError(f"{str(self.target_type)} is not an Enum")
        self._args_mapper = {e.name: e for e in self.target_type}

    def _convert(self, args: Sequence[str]) -> Any:
        if args[0] in self._args_mapper:
            return self._args_mapper[args[0]]
        else:
            raise ValueError(f"{args[0]} not part of {str(self.target_type)}")

    @classmethod
    def factory(cls, target_type: Type, store: "CLIArgConverterStore"):
        del store
        return cls(target_type=target_type)


@mutable
class BoolCLIArgConverter(CLIArgConverterBase):
    target_type: Type

    def __attrs_post_init__(self) -> None:
        self.num_req_args = 1
        if self.target_type != bool:
            raise TypeError(f"{str(self.target_type)} is not a boolean")

    def _convert(self, args: Sequence[str]) -> Any:
        if args[0].lower() in ("true", "t", "yes"):
            return True
        elif args[0].lower() in ("false", "f", "no"):
            return False
        else:
            raise ValueError(f"Can't convert {args[0]} to boolean")

    @classmethod
    def factory(cls, target_type: Type, store: "CLIArgConverterStore"):
        del store
        return cls(target_type=target_type)


@mutable
class UnionCLIArgConverter(CLIArgConverterBase):
    target_type: Type
    _converters: List[CLIArgConverterBase] = field(factory=list)

    @classmethod
    def factory(cls, target_type: Type, store: "CLIArgConverterStore"):
        if not get_origin(target_type) == get_origin(Union[int, str]):
            raise TypeError(f"{str(target_type)} is not of type 'Union'")

        converters = store.get_sorted_converters(get_args(target_type))

        return cls(target_type=target_type, converters=converters)

    def __attrs_post_init__(self) -> None:
        # ensure that all converters require the same number of arguments
        self.num_req_args = self._converters[0].num_req_args
        for converter in self._converters:
            if converter.num_req_args != self.num_req_args:
                raise UnequalNumberArgsError(
                    "Number of required arguments for all types of"
                    " a Union has to be equal"
                )

    def _convert(self, args: Sequence[str]) -> Any:
        for converter in self._converters:
            try:
                return converter.convert(args)
            except Exception:
                pass
        raise ValueError(f"No fitting type found in union for {args}")


@mutable
class ListCLIArgConverter(CLIArgConverterBase):
    target_type: Type
    inner_converter: CLIArgConverterBase = field(
        factory=lambda: BasicCLIArgConverter(str, str, str)
    )

    @classmethod
    def factory(cls, target_type: Type, store: "CLIArgConverterStore"):
        if not get_origin(target_type) == get_origin(List):
            raise TypeError(f"{str(target_type)} is not of type 'List'")

        type_args = get_args(target_type)
        if len(type_args) == 0:
            # default is already correct
            pass
        elif len(type_args) == 1:
            inner_converter = store.get_converter(type_args[0])
        else:
            raise TypeError("Inner type has several arguments.")

        return cls(target_type=target_type, inner_converter=inner_converter)

    def __attrs_post_init__(self) -> None:
        # ensure that all converters require the same number of arguments
        inner_num_args = self.inner_converter.num_req_args
        if not isinstance(inner_num_args, int):
            raise TypeError("Inner type can't have variable number of args")
        self.num_req_args = slice(0, None, inner_num_args)

    def _convert(self, args: Sequence[str]) -> Any:
        req_group_args = self.num_req_args.step  # type: ignore
        num_groups = len(args) // req_group_args
        num_args = num_groups * req_group_args
        if len(args) > num_args:
            raise TooManyArgsError()
        out = []
        for i in range(0, num_args, req_group_args):
            group_args = args[i : (i + req_group_args)]
            out.append(self.inner_converter.convert(group_args))
        return out


@mutable
class TupleCLIArgConverter(CLIArgConverterBase):
    target_type: Type
    tuple_converters: List[CLIArgConverterBase] = field(factory=list)

    @classmethod
    def factory(cls, target_type: Type, store: "CLIArgConverterStore"):
        if not get_origin(target_type) == get_origin(Tuple):
            raise TypeError(f"{str(target_type)} is not of type 'Tuple'")

        type_args = get_args(target_type)
        tuple_converters = []
        for type_arg in type_args:
            tuple_converters.append(store.get_converter(type_arg))
        return cls(target_type=target_type, tuple_converters=tuple_converters)

    def __attrs_post_init__(self) -> None:
        # ensure that all of them have finite number of required args
        self.num_req_args = 0
        for converter in self.tuple_converters:
            if not isinstance(converter.num_req_args, int):
                raise CLIArgConverterError(
                    "Each type as part of a tuple has to have "
                    "constant number of arguments."
                )
            self.num_req_args += converter.num_req_args

    def _convert(self, args: Sequence[str]) -> Any:
        tuple_out = []
        pos = 0
        for converter in self.tuple_converters:
            assert isinstance(converter.num_req_args, int)
            tuple_args = args[pos : (pos + converter.num_req_args)]
            pos = pos + converter.num_req_args
            tuple_out.append(converter.convert(tuple_args))
        return tuple(tuple_out)


class CLIArgConverterStore:
    _converter_factories: List[
        Tuple[Callable[[Type, "CLIArgConverterStore"], CLIArgConverterBase], float]
    ]

    def __init__(self, add_defaults: bool = True):
        self._converter_factories = []
        if add_defaults:
            self.add_default_converters()

    def add_converter_factory(
        self,
        converter_factory: Callable[
            [Type, "CLIArgConverterStore"], CLIArgConverterBase
        ],
        priority: float,
    ):
        self._converter_factories.append((converter_factory, priority))
        self._converter_factories.sort(key=lambda x: x[1], reverse=True)

    def add_default_converters(self):
        self.add_converter_factory(
            partial(BasicCLIArgConverter.factory, supported_type=str), 1
        )
        self.add_converter_factory(
            partial(BasicCLIArgConverter.factory, supported_type=Path), 2
        )
        self.add_converter_factory(BoolCLIArgConverter.factory, 3)
        self.add_converter_factory(
            partial(BasicCLIArgConverter.factory, supported_type=float), 4
        )
        self.add_converter_factory(
            partial(BasicCLIArgConverter.factory, supported_type=int), 5
        )
        self.add_converter_factory(EnumCLIArgConverter.factory, 6)
        self.add_converter_factory(LiteralCLIArgConverter.factory, 7)
        self.add_converter_factory(UnionCLIArgConverter.factory, 8)
        self.add_converter_factory(ListCLIArgConverter.factory, 9)
        self.add_converter_factory(TupleCLIArgConverter.factory, 10)

    def get_converter_with_priority(
        self, target_type: Type
    ) -> Tuple[CLIArgConverterBase, float]:
        for converter_factory, priority in self._converter_factories:
            try:
                converter = converter_factory(target_type, self)
                return (converter, priority)
            except TypeError:
                pass

        raise TypeError(f"No available converter for {str(target_type)}")

    def get_converter(self, target_type: Type) -> CLIArgConverterBase:
        return self.get_converter_with_priority(target_type)[0]

    def get_sorted_converters(
        self, target_types: Sequence[Type]
    ) -> List[CLIArgConverterBase]:
        converters_list = [
            self.get_converter_with_priority(target_type)
            for target_type in target_types
        ]
        converters_list.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in converters_list]
