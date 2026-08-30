"""Gedeelde opzet voor de proeven.

De kernproeven onder tests/kern draaien zonder Home Assistant. De proeven onder
tests/ha hebben pytest-homeassistant-custom-component nodig; die zetten een
echte Home Assistant op in het geheugen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


@pytest.fixture(autouse=True)
def sta_custom_integraties_toe(request):
    """Home Assistant laadt custom_components in een proef alleen op verzoek."""
    if "enable_custom_integrations" in request.fixturenames:
        return
    try:
        request.getfixturevalue("enable_custom_integrations")
    except pytest.FixtureLookupError:
        # De kernproeven draaien zonder Home Assistant; daar bestaat deze
        # fixture niet en is hij ook niet nodig.
        return
