from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    List,
    Literal,
    Protocol,
    Sequence,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from .exceptions import IncorrectNumberArgs


class TypeConverterMulti(Protocol):
    """Protocol for type converters."""

    def __call__(self, *args: str) -> Any:
        """Run the type converter."""
        ...


TypeConverter = Union[Callable[[str], Any], TypeConverterMulti]


@dataclass
class TypeConverterNargs:
    converter: TypeConverter
    nargs: int

    def __call__(self, *args: Any) -> Any:
        return self.converter(*args)


TypeConverterFactory = Callable[[Type], TypeConverterNargs]


def literal_type_converter_factory(target_type: Type) -> TypeConverterNargs:
    if get_origin(target_type) == Literal:
        literal_args = get_args(target_type)
        args_mapper = {str(arg): arg for arg in literal_args}
        # need to make sure that no args are duplicated
        if len(args_mapper) < len(literal_args):
            raise ValueError(
                f"Type {str(target_type)} has duplicate values "
                "when converted to string."
            )

        def literal_converter(arg: str) -> Any:
            if arg in args_mapper:
                return args_mapper[arg]
            else:
                raise ValueError(f"{arg} not part of {str(target_type)}")

        return TypeConverterNargs(literal_converter, 1)

    else:
        raise TypeError("Not a literal type")


def enum_type_converter_factory(target_type: Type) -> TypeConverterNargs:
    if issubclass(target_type, Enum):
        args_mapper = {e.name: e for e in target_type}

        def enum_converter(arg: str) -> Any:
            if arg in args_mapper:
                return args_mapper[arg]
            else:
                raise ValueError(f"{arg} not part of {str(target_type)}")

        return TypeConverterNargs(enum_converter, 1)
    else:
        raise TypeError("Not an enum type.")


def bool_type_converter_factory(target_type: Type) -> TypeConverterNargs:
    if target_type != bool:
        raise TypeError("Not a bool type.")
    else:

        def bool_converter(arg: str) -> bool:
            if arg.lower() in ("true", "t", "yes"):
                return True
            elif arg.lower() in ("false", "f", "no"):
                return False
            else:
                raise ValueError(f"Can't convert {arg} to boolean")

        return TypeConverterNargs(bool_converter, 1)


class SimpleTypeConverterFactory:
    _factories: List[Tuple[TypeConverterFactory, float]]

    def __init__(self):
        """Add all standard simple type converters."""
        self._factories = [
            (self.union_converter_factory, 8),
            (literal_type_converter_factory, 7),
            (enum_type_converter_factory, 6),
            (bool_type_converter_factory, 3),
        ]
        self._add_simple_type(int, 5)
        self._add_simple_type(float, 4)
        self._add_simple_type(Path, 2)
        self._add_simple_type(str, 1)

    def _add_simple_type(self, simple_type: Type, priority: float):
        def simple_type_converter_factory(
            target_type: Type,
        ) -> TypeConverterNargs:
            if target_type == simple_type:

                def simple_type_converter(arg: str) -> Any:
                    return target_type(arg)

                return TypeConverterNargs(simple_type_converter, 1)

            else:
                raise TypeError(f"{str(target_type)} not supported")

        self._factories.append((simple_type_converter_factory, priority))

    def _get_converter_with_priority(
        self,
        target_type: Type,
    ) -> Tuple[TypeConverterNargs, float]:
        for factory, priority in self._factories:
            try:
                converter = factory(target_type)
                return (converter, priority)
            except TypeError:
                pass

        raise ValueError(f"No available converter for {str(target_type)}")

    def _order_converter_factories(
        self, types_list: Sequence[Type]
    ) -> List[TypeConverterNargs]:
        converter_list_ranked = [
            self._get_converter_with_priority(target_type) for target_type in types_list
        ]
        # need to sort by
        converter_list_ranked.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in converter_list_ranked]

    def union_converter_factory(self, target_type: Type) -> TypeConverterNargs:
        if get_origin(target_type) == Union:
            converters = self._order_converter_factories(get_args(target_type))

            def union_converter(arg: Any) -> Any:
                for converter in converters:
                    try:
                        return converter(arg)
                    except Exception:
                        pass
                raise ValueError(f"No fitting type found in union for {arg}")

            return TypeConverterNargs(union_converter, 1)

        else:
            raise TypeError("Not a union type.")

    def converter_factory(self, target_type: Type) -> TypeConverterNargs:
        converter, _ = self._get_converter_with_priority(target_type)
        return TypeConverterNargs(converter, 1)


class ComplexTypeConverterFactory:
    _simple_factory: SimpleTypeConverterFactory
    _complex_factories: List[TypeConverterFactory]

    def __init__(self, simple_factory: SimpleTypeConverterFactory):
        self._simple_factory = simple_factory
        self._complex_factories = [
            self.list_converter_factory,
            self.tuple_converter_factory,
        ]

    def list_converter_factory(self, target_type: Type) -> TypeConverterNargs:
        if get_origin(target_type) == list:
            type_args = get_args(target_type)
            if len(type_args) == 0:
                # if Any, we set type to str
                inner_type = str
            elif len(type_args) == 1:
                inner_type = type_args[0]
            else:
                raise TypeError("Inner type has several arguments.")

            inner_type_converter = self._simple_factory.converter_factory(inner_type)

            def list_converter(*args) -> List[Any]:
                return [inner_type_converter(arg) for arg in args]

            return TypeConverterNargs(list_converter, -1)
        else:
            raise TypeError(f"{str(target_type)} not a list type.")

    def tuple_converter_factory(self, target_type: Type) -> TypeConverterNargs:
        if get_origin(target_type) == tuple:

            tuple_type_converters: List[TypeConverter] = [
                self._simple_factory.converter_factory(type_arg)
                for type_arg in get_args(target_type)
            ]

            def tuple_converter(*args) -> Tuple[Any, ...]:
                if len(args) != len(tuple_type_converters):
                    raise ValueError(
                        f"Expected {len(tuple_type_converters)} "
                        f"arguments but got {len(args)}"
                    )
                else:
                    return tuple(
                        [
                            type_converter(arg)
                            for type_converter, arg in zip(tuple_type_converters, args)
                        ]
                    )

            return TypeConverterNargs(tuple_converter, len(get_args(target_type)))
        else:
            raise TypeError(f"{str(target_type)} is not a tuple.")

    def converter_factory(self, target_type: Type) -> TypeConverterNargs:
        for factory in self._complex_factories:
            try:
                converter = factory(target_type)
                return converter
            except TypeError:
                pass
        return self._simple_factory.converter_factory(target_type)
