from pathlib import Path
from typing import Union

from thermite.plugins.help import clean_type_str


def test_clean_type_str():
    assert clean_type_str(int) == "int"
    assert clean_type_str(Union[int, Path]) == "Union[int, Path]"
