import pytest
from bluepyentity import materialize as test_module


@pytest.mark.parametrize(
    "entry,expected",
    [
        ({"@id": "my-id"}, "my-id"),
        ({"@id": "my-id?rev=10000"}, "my-id?rev=10000"),
        ({"@id": "my-id", "_rev": 2}, "my-id?rev=2"),
        ({"@id": "my-id?rev=3", "_rev": 3}, "my-id?rev=3"),
    ],
)
def test_density_entry(entry, expected):
    result = test_module._get_density_id(entry)
    assert result == expected
