import pytest

from thermite.type_converters import CLIArgConverterStore


@pytest.fixture
def store():
    yield CLIArgConverterStore(add_defaults=True)
