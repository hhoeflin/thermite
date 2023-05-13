from typing import Callable, Dict, List

from .parameters import Option, ParameterGroup


def pg_trigger_map(
    f: Callable[[str], str | List[str] | None]
) -> Callable[[ParameterGroup], ParameterGroup]:
    def pg_trigger_map_inner(pg: ParameterGroup) -> ParameterGroup:
        for key, param in pg.params.items():
            if isinstance(param, Option):
                for processor in param.processors:
                    res = []
                    for trigger in processor.triggers:
                        f_res = f(trigger)
                        if isinstance(f_res, str):
                            res.append(f_res)
                        elif f_res is None:
                            continue
                        else:
                            res.extend(f_res)
                    processor.triggers = res
            elif isinstance(param, ParameterGroup):
                pg.params[key] = pg_trigger_map_inner(param)
        return pg

    return pg_trigger_map_inner


def multi_str_replace(repl_dict: Dict[str, str]) -> Callable[[str], str]:
    def multi_str_replace_inner(x: str) -> str:
        for old, new in repl_dict.items():
            if (new_x := x.replace(old, new)) != x:
                return new_x
        return x

    return multi_str_replace_inner


def multi_extend(
    ext_dict: Dict[str, str | List[str | None] | None]
) -> Callable[[str], str | List[str] | None]:
    def multi_extend_inner(x: str) -> str | List[str] | None:
        if x in ext_dict:
            item = ext_dict[x]
            if item is None:
                return None
            elif isinstance(item, str):
                return [x, item]
            elif isinstance(item, list):
                if any([y is None for y in item]):
                    return [y for y in item if y is not None]
                else:
                    return [x] + [y for y in item if y is not None]
            else:
                raise Exception("Unexpected return type")
        else:
            return x

    return multi_extend_inner
