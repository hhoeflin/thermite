from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import (
    Any,
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

    @final
    def num_requested_args(self, num_offered_args: int) -> int:
        return args_used(num_offered_args, self.num_req_args)


@mutable(slots=False)
class CLIArgConverterSimple(CLIArgConverterBase):
    _target_type: Type


@mutable(slots=False)
class BasicCLIArgConverter(CLIArgConverterSimple):
    _supported_type: ClassVar[Any] = None
    _bound_arg: Optional[str] = field(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        self.num_req_args = 1
        if self._target_type != self._supported_type:
            raise TypeError(
                f"{str(self._target_type)} not same as "
                f"supported type {str(self._supported_type)}"
            )

    @property
    def target_type(self) -> Type:
        return self._target_type

    def _convert(self, args: Sequence[str]) -> Any:
        return self._target_type(*args)


@mutable(slots=False)
class StrCLIArgConverter(BasicCLIArgConverter):
    _supported_type = str
    _target_type: Type = str


@mutable(slots=False)
class PathCLIArgConverter(BasicCLIArgConverter):
    _supported_type = Path
    _target_type: Type = Path


@mutable(slots=False)
class FloatCLIArgConverter(BasicCLIArgConverter):
    _supported_type = float
    _target_type: Type = float


@mutable(slots=False)
class IntCLIArgConverter(BasicCLIArgConverter):
    _supported_type = int
    _target_type: Type = int


# TODO: Should the next classes have base BasicCLIArgConverter?
@mutable(slots=False)
class LiteralCLIArgConverter(BasicCLIArgConverter):
    _args_mapper: Dict[str, Any] = field(factory=dict, init=False)

    def __attrs_post_init__(self) -> None:
        self.num_req_args = 1
        if not get_origin(self._target_type) == get_origin(Literal["a", "b"]):
            raise TypeError(f"{str(self._target_type)} is not of type 'Literal'")
        literal_args = get_args(self._target_type)
        self._args_mapper = {str(arg): arg for arg in literal_args}
        # need to make sure that no args are duplicated
        if len(self._args_mapper) < len(literal_args):
            raise ValueError(
                f"Type {str(self._target_type)} has duplicate values "
                "when converted to string."
            )

    def _convert(self, args: Sequence[str]) -> Any:
        if args[0] in self._args_mapper:
            return self._args_mapper[args[0]]
        else:
            raise ValueError(f"{args[0]} not part of {str(self._target_type)}")


@mutable(slots=False)
class EnumCLIArgConverter(BasicCLIArgConverter):
    _args_mapper: Dict[str, Any] = field(factory=dict, init=False)

    def __attrs_post_init__(self) -> None:
        self.num_req_args = 1
        if not issubclass(self._target_type, Enum):
            raise TypeError(f"{str(self._target_type)} is not an Enum")
        self._args_mapper = {e.name: e for e in self._target_type}

    def _convert(self, args: Sequence[str]) -> Any:
        if args[0] in self._args_mapper:
            return self._args_mapper[args[0]]
        else:
            raise ValueError(f"{args[0]} not part of {str(self._target_type)}")


@mutable(slots=False)
class BoolCLIArgConverter(BasicCLIArgConverter):
    def __attrs_post_init__(self) -> None:
        self.num_req_args = 1
        if self._target_type != bool:
            raise TypeError(f"{str(self._target_type)} is not a boolean")

    def _convert(self, args: Sequence[str]) -> Any:
        if args[0].lower() in ("true", "t", "yes"):
            return True
        elif args[0].lower() in ("false", "f", "no"):
            return False
        else:
            raise ValueError(f"Can't convert {args[0]} to boolean")


@mutable(slots=False)
class CLIArgConverterCompound(CLIArgConverterBase):
    _target_type: Type

    @classmethod
    @abstractmethod
    def from_store(cls, target_type: Type, store: "CLIArgConverterStore"):
        pass


class CLIArgConverterStore:
    _converters_with_priority: List[
        Tuple[Union[Type[CLIArgConverterSimple], Type[CLIArgConverterCompound]], float]
    ]

    def __init__(self, add_defaults: bool = True):
        self._converters_with_priority = []
        if add_defaults:
            self.add_default_converters()

    def add_converter(
        self,
        converter: Union[Type[CLIArgConverterSimple], Type[CLIArgConverterCompound]],
        priority: float,
    ):
        self._converters_with_priority.append((converter, priority))
        self._converters_with_priority.sort(key=lambda x: x[1], reverse=True)

    def add_default_converters(self):
        self.add_converter(StrCLIArgConverter, 1)
        self.add_converter(PathCLIArgConverter, 2)
        self.add_converter(BoolCLIArgConverter, 3)
        self.add_converter(FloatCLIArgConverter, 4)
        self.add_converter(IntCLIArgConverter, 5)
        self.add_converter(EnumCLIArgConverter, 6)
        self.add_converter(LiteralCLIArgConverter, 7)
        self.add_converter(UnionCLIArgConverter, 8)
        self.add_converter(ListCLIArgConverter, 9)
        self.add_converter(TupleCLIArgConverter, 10)

    def _get_converter_priority(
        self, target_type: Type
    ) -> Tuple[CLIArgConverterBase, float]:
        for converter_class, priority in self._converters_with_priority:
            try:
                converter: CLIArgConverterBase
                if issubclass(converter_class, CLIArgConverterCompound):
                    converter = converter_class.from_store(target_type, store=self)
                elif issubclass(converter_class, CLIArgConverterSimple):
                    converter = converter_class(target_type)
                else:
                    raise Exception("Unexpected converter class")
                return (converter, priority)
            except TypeError:
                pass

        raise TypeError(f"No available converter for {str(target_type)}")

    def get_converter(self, target_type: Type) -> CLIArgConverterBase:
        return self._get_converter_priority(target_type)[0]

    def get_sorted_converters(
        self, target_types: Sequence[Type]
    ) -> List[CLIArgConverterBase]:
        converters_list = [
            self._get_converter_priority(target_type) for target_type in target_types
        ]
        converters_list.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in converters_list]


@mutable(slots=False)
class UnionCLIArgConverter(CLIArgConverterCompound):
    _bound_args: List[str] = field(factory=list, init=False)
    _converters: List[CLIArgConverterBase] = field(factory=list)

    @classmethod
    def from_store(cls, target_type: Type, store: "CLIArgConverterStore"):
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

    @property
    def target_type(self) -> Type:
        return self._target_type

    def _convert(self, args: Sequence[str]) -> Any:
        for converter in self._converters:
            try:
                return converter.convert(args)
            except Exception:
                pass
        raise ValueError(f"No fitting type found in union for {args}")


@mutable(slots=False)
class ListCLIArgConverter(CLIArgConverterCompound):
    _bound_args: List[str] = field(factory=list, init=False)
    _inner_converter: CLIArgConverterBase = field(default=StrCLIArgConverter(str))

    @classmethod
    def from_store(cls, target_type: Type, store: "CLIArgConverterStore"):
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
        inner_num_args = self._inner_converter.num_req_args
        if not isinstance(inner_num_args, int):
            raise TypeError("Inner type can't have variable number of args")
        self.num_req_args = slice(0, None, inner_num_args)

    @property
    def target_type(self) -> Type:
        return self._target_type

    def _convert(self, args: Sequence[str]) -> Any:
        req_group_args = self.num_req_args.step  # type: ignore
        num_groups = len(args) // req_group_args
        num_args = num_groups * req_group_args
        if len(args) > num_args:
            raise TooManyArgsError()
        out = []
        for i in range(0, num_args, req_group_args):
            group_args = args[i : (i + req_group_args)]
            out.append(self._inner_converter.convert(group_args))
        return out


@mutable(slots=False)
class TupleCLIArgConverter(CLIArgConverterCompound):
    _bound_args: List[str] = field(factory=list, init=False)
    _tuple_converters: List[CLIArgConverterBase] = field(factory=list)

    @classmethod
    def from_store(cls, target_type: Type, store: "CLIArgConverterStore"):
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
        for converter in self._tuple_converters:
            if not isinstance(converter.num_req_args, int):
                raise CLIArgConverterError(
                    "Each type as part of a tuple has to have "
                    "constant number of arguments."
                )
            self.num_req_args += converter.num_req_args

    @property
    def target_type(self) -> Type:
        return self._target_type

    def _convert(self, args: Sequence[str]) -> Any:
        tuple_out = []
        pos = 0
        for converter in self._tuple_converters:
            assert isinstance(converter.num_req_args, int)
            tuple_args = args[pos : (pos + converter.num_req_args)]
            pos = pos + converter.num_req_args
            tuple_out.append(converter.convert(tuple_args))
        return tuple(tuple_out)
