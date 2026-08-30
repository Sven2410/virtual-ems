"""Laadt de rekenkern los van het Home Assistant-pakket eromheen.

`custom_components/virtual_ems/__init__.py` is het aanknopingspunt voor Home
Assistant en importeert dus `homeassistant` en `voluptuous`. Wie
`custom_components.virtual_ems.simulation` importeert voert eerst dat bestand
uit, en dan is de rekenkern in de praktijk niet meer los te draaien: op een
machine zonder Home Assistant valt hij om op een import die met de som niets te
maken heeft.

Deze lader zet daarom een eigen pakketnaam neer die naar dezelfde map wijst,
zonder dat `__init__.py` wordt uitgevoerd. De betrekkelijke imports binnen de
rekenkern (`from .const import ...`) blijven gewoon werken.

Dat is meteen de bewaking: zodra er in `simulation.py`, `scenarios.py`,
`catalog.py` of `const.py` een Home Assistant-import binnensluipt, vallen alle
kernproeven om op een machine zonder Home Assistant. `test_repo.py` controleert
dat bovendien nog eens op de tekst van de bestanden.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COMPONENT = REPO / "custom_components" / "virtual_ems"

#: De bestanden die samen de rekenkern vormen. Geen van vier mag Home Assistant
#: nodig hebben.
KERNBESTANDEN: tuple[str, ...] = ("const.py", "simulation.py", "scenarios.py", "catalog.py")

PAKKET = "virtual_ems_kern"
#: De naam is ook buiten dit bestand nodig, bijvoorbeeld om bundelversie.py
#: los te laden in test_frontend.py.

if PAKKET not in sys.modules:
    _pakket = types.ModuleType(PAKKET)
    _pakket.__path__ = [str(COMPONENT)]
    _pakket.__doc__ = "De rekenkern van virtual_ems, zonder Home Assistant eromheen."
    sys.modules[PAKKET] = _pakket

const = importlib.import_module(f"{PAKKET}.const")
simulation = importlib.import_module(f"{PAKKET}.simulation")
scenarios = importlib.import_module(f"{PAKKET}.scenarios")
catalog = importlib.import_module(f"{PAKKET}.catalog")

# Doorgeven wat de proeven gebruiken, zodat een proef gewoon
# `from kernlader import Simulation` kan schrijven.
PlantConfig = simulation.PlantConfig
Setpoints = simulation.Setpoints
Simulation = simulation.Simulation
Totals = simulation.Totals
solar_position = simulation.solar_position
clear_sky_dni = simulation.clear_sky_dni

SCENARIOS = scenarios.SCENARIOS
apply_scenario = scenarios.apply_scenario

ENTITY_KEYS = catalog.ENTITY_KEYS
entity_ids = catalog.entity_ids
slugify_naam = catalog.slugify_naam

APPLIANCES = const.APPLIANCES
DOMAIN = const.DOMAIN
DEFAULT_NAME = const.DEFAULT_NAME
SERVICE_RESET = const.SERVICE_RESET
SERVICE_SET_SCENARIO = const.SERVICE_SET_SCENARIO
UPDATE_INTERVAL_SECONDS = const.UPDATE_INTERVAL_SECONDS
