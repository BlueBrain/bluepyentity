import re
import pytest
from bluepyentity.exceptions import BluepyEntityError
from bluepyentity import environments as tested


def test_create_forge__raises():

    with pytest.raises(BluepyEntityError, match="Unsupported 'store_overrides' keys."):
        tested.create_forge("prod", None, None, store_overrides={"John": "Beatle"})

    with pytest.raises(BluepyEntityError, match="Unsupported 'store_overrides' keys."):
        tested.create_forge(
            "prod", None, None, store_overrides={"searchendpoints": {}, "John": "Beatle"}
        )
