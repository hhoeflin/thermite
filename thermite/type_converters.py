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
    get_args,
    get_origin,
)

from attrs import field, mutable


class TooManyArgsError(Exception):
    ...


class NoBoundArgsError(Exception):
    ...


class UnequalNumberArgsError(Exception):
    ...


class RebindingError(Exception):
    ...


class TooFewArgsError(Exception):
    ...


class CLIArgConverterError(Exception):
    ...


@mutable()
class NumReqArgs:
    min: int
    max: int


class CLIArgConverterBase(ABC):
    @property
    @abstractmethod
    def num_required_args(self) -> NumReqArgs:
        ...

    @abstractmethod
    def num_requested_args(self, num_offered_args: int) -> int:
        ...

    @property
    @abstractmethod
    def target_type(self) -> Type:
        ...

    @abstractmethod
    def convert(self, args: Sequence[str]) -> Any:
        ...


@mutable(slots=False)
class CLIArgConverterSimple(CLIArgConverterBase):
    _target_type: Type


@mutable(slots=False)
class BasicCLIArgConverter(CLIArgConverterSimple):
    _supported_type: ClassVar[Any] = None
    _bound_arg: Optional[str] = field(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        if self._target_type != self._supported_type:
            raise TypeError(
                f"{str(self._target_type)} not same as "
                f"supported type {str(self._supported_type)}"
            )

    @property
    def num_required_args(self) -> NumReqArgs:
        return NumReqArgs(1, 1)

    def num_requested_args(self, num_offered_args: int) -> int:
        if num_offered_args < 1:
            raise TooFewArgsError("Require at least 1 argument")
        return 1

    @property
    def target_type(self) -> Type:
        return self._target_type

    def convert(self, args: Sequence[str]) -> Any:
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


@mutable(slots=False)
class LiteralCLIArgConverter(BasicCLIArgConverter):
    _args_mapper: Dict[str, Any] = field(factory=dict, init=False)

    def __attrs_post_init__(self) -> None:
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

    def convert(self, args: Sequence[str]) -> Any:
        if len(args) > 1:
            raise TooManyArgsError()
        elif len(args) == 0:
            raise TooFewArgsError()

        if args[0] in self._args_mapper:
            return self._args_mapper[args[0]]
        else:
            raise ValueError(f"{args[0]} not part of {str(self._target_type)}")


@mutable(slots=False)
class EnumCLIArgConverter(BasicCLIArgConverter):
    _args_mapper: Dict[str, Any] = field(factory=dict, init=False)

    def __attrs_post_init__(self) -> None:
        if not issubclass(self._target_type, Enum):
            raise TypeError(f"{str(self._target_type)} is not an Enum")
        self._args_mapper = {e.name: e for e in self._target_type}

    def convert(self, args: Sequence[str]) -> Any:
        if len(args) > 1:
            raise TooManyArgsError()
        elif len(args) == 0:
            raise TooFewArgsError()

        if args[0] in self._args_mapper:
            return self._args_mapper[args[0]]
        else:
            raise ValueError(f"{args[0]} not part of {str(self._target_type)}")


@mutable(slots=False)
class BoolCLIArgConverter(BasicCLIArgConverter):
    def __attrs_post_init__(self) -> None:
        if self._target_type != bool:
            raise TypeError(f"{str(self._target_type)} is not a boolean")

    def convert(self, args: Sequence[str]) -> Any:
        if len(args) > 1:
            raise TooManyArgsError()
        elif len(args) == 0:
            raise TooFewArgsError()

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
    _num_required_args: NumReqArgs = field(default=NumReqArgs(0, 0), init=False)

    @classmethod
    def from_store(cls, target_type: Type, store: "CLIArgConverterStore"):
        if not get_origin(target_type) == get_origin(Union[int, str]):
            raise TypeError(f"{str(target_type)} is not of type 'Union'")

        converters = store.get_sorted_converters(get_args(target_type))

        return cls(target_type=target_type, converters=converters)

    def __attrs_post_init__(self) -> None:
        # ensure that all converters require the same number of arguments
        self._num_required_args = self._converters[0].num_required_args
        for converter in self._converters:
            if converter.num_required_args != self._num_required_args:
                raise UnequalNumberArgsError(
                    "Number of required arguments for all types of"
                    " a Union has to be equal"
                )

    @property
    def num_required_args(self) -> NumReqArgs:
        return self._num_required_args

    def num_requested_args(self, num_offered_args: int) -> int:
        return self._converters[0].num_requested_args(num_offered_args)

    @property
    def target_type(self) -> Type:
        return self._target_type

    def convert(self, args: Sequence[str]) -> Any:
        if len(args) > self.num_required_args.max:
            raise TooManyArgsError()
        elif len(args) < self.num_required_args.min:
            raise TooFewArgsError()
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
            inner_num_args = inner_converter.num_required_args
            if inner_num_args.min != inner_num_args.max:
                raise TypeError("Inner type can't have variable number of args")
        else:
            raise TypeError("Inner type has several arguments.")

        return cls(target_type=target_type, inner_converter=inner_converter)

    @property
    def num_required_args(self) -> NumReqArgs:
        return NumReqArgs(self._inner_converter.num_required_args.min, -1)

    def num_requested_args(self, num_offered_args: int) -> int:
        inner_num_args = self._inner_converter.num_required_args.min
        if num_offered_args < inner_num_args:
            raise TooFewArgsError(f"Require at least {inner_num_args} arguments")
        return int(int(num_offered_args) / int(inner_num_args) * int(inner_num_args))

    @property
    def target_type(self) -> Type:
        return self._target_type

    def convert(self, args: Sequence[str]) -> Any:
        req_group_args = self._inner_converter.num_required_args.min
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
        # ensure that all of them have finite number of required args
        for converter in tuple_converters:
            if converter.num_required_args.max == -1:
                raise CLIArgConverterError(
                    "A list is not allowed to be part of a tuple."
                )
            if converter.num_required_args.min != converter.num_required_args.max:
                raise CLIArgConverterError(
                    "Type in a tuple has to have a constant number of arguments."
                )
        return cls(target_type=target_type, tuple_converters=tuple_converters)

    @property
    def num_required_args(self) -> NumReqArgs:
        num_args = sum([x.num_required_args.min for x in self._tuple_converters])

        return NumReqArgs(num_args, num_args)

    def num_requested_args(self, num_offered_args: int) -> int:
        if num_offered_args < self.num_required_args.min:
            raise TooFewArgsError(
                "Require at least {self.num_requested_args.min} argument"
            )
        return self.num_required_args.min

    @property
    def target_type(self) -> Type:
        return self._target_type

    def convert(self, args: Sequence[str]) -> Any:
        if len(args) > self.num_required_args.max:
            raise TooManyArgsError()
        elif len(args) < self.num_required_args.min:
            raise TooFewArgsError()
        tuple_out = []
        pos = 0
        for converter in self._tuple_converters:
            tuple_args = args[pos : (pos + converter.num_required_args.min)]
            pos = pos + converter.num_required_args.min
            tuple_out.append(converter.convert(tuple_args))
        return tuple(tuple_out)
