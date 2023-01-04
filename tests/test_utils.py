import pytest
from bluepyentity import utils as test_module
from bluepyentity.exceptions import BluepyEntityError


@pytest.mark.parametrize(
    "url,expected",
    [
        ("my-url?rev=5", 5),
        ("my-url", None),
    ],
)
def test_url_get_revision(url, expected):
    result = test_module.url_get_revision(url)
    assert result == expected


@pytest.mark.parametrize(
    "url,revision,expected",
    [
        ("my-url", 5, "my-url?rev=5"),
        ("my-url?rev=5", 5, "my-url?rev=5"),
    ],
)
def test_url_with_revision(url, revision, expected):
    result = test_module.url_with_revision(url, revision)
    assert result == expected


def test_url_with_revision__mismatch():
    expected_str = r"Url \'my-id\?rev=5\' revision \'5\' does not match the input \'10\' one."
    with pytest.raises(BluepyEntityError, match=expected_str):
        test_module.url_with_revision("my-id?rev=5", 10)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("my-url", "my-url"),
        ("my-url?rev=1", "my-url"),
    ],
)
def test_url_without_revision(url, expected):
    result = test_module.url_without_revision(url)
    assert result == expected
