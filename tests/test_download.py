import tempfile
from pathlib import Path
from unittest.mock import Mock
from bluepyentity import download as tested


def test_get_filesystem_location__no_resource_attributes():
    class Empty:
        """Empty"""

    res = tested._get_filesystem_location(Empty())
    assert res is None


def test_get_filesystem_location__non_existing_path():

    mock = Mock()
    mock.atLocation.location = "road-to-camelot"
    res = tested._get_filesystem_location(mock)
    assert res is None


def test_get_filesystem_location():

    with tempfile.NamedTemporaryFile() as tfile:
        path = Path(tfile.name)

        mock = Mock()
        # without file:// prefix
        mock.atLocation.location = str(path)
        res = tested._get_filesystem_location(mock)
        assert res == path

        # with file:// prefix
        mock.atLocation.location = f"file://{path}"
        res = tested._get_filesystem_location(mock)
        assert res == path
