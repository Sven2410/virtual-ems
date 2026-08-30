"""Constanten voor de virtual_ems integratie.

Alle getallen hieronder zijn óf een instelling (aanpasbaar via de config flow /
options flow), óf een gepubliceerde natuurkundige constante met bronvermelding,
óf een vormfactor die expliciet als vorm is gedocumenteerd. Er staan geen
verzonnen kentallen in dit bestand.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "virtual_ems"
MANUFACTURER: Final = "DomotiTech"
MODEL: Final = "Virtueel EMS (simulatie)"

# --- Config entry keys -------------------------------------------------------

CONF_NAME: Final = "naam"
CONF_PV_PEAK_KWP: Final = "pv_piek_kwp"
CONF_BATTERY_KWH: Final = "batterij_kwh"
CONF_EV_MAX_KW: Final = "laadpaal_max_kw"
CONF_ANNUAL_KWH: Final = "jaarverbruik_kwh"
CONF_START_HOUR: Final = "dagstart_uur"
CONF_CONNECTION_A: Final = "aansluiting_a"
CONF_PHASES: Final = "fasen"

DEFAULT_NAME: Final = "Virtueel EMS"
DEFAULT_PV_PEAK_KWP: Final = 4.0
DEFAULT_BATTERY_KWH: Final = 10.0
DEFAULT_EV_MAX_KW: Final = 11.0

# Standaard jaarverbruik van het huishouden. Dit is een INSTELLING met een
# ordegrootte-default, geen meting: de docent hoort hier het werkelijke
# jaarverbruik van de voorbeeldwoning in te vullen. Het bepaalt uitsluitend de
# schaal van het basislastprofiel.
DEFAULT_ANNUAL_KWH: Final = 2900.0

# De netaansluiting. Drie fasen van 25 A is de gangbare Nederlandse
# woningaansluiting; een oudere woning heeft vaak één fase van 35 A. Dit is een
# instelling, en de balken op het dashboard hangen eraan: zonder deze twee zou
# een balk een verzonnen maximum tonen.
DEFAULT_CONNECTION_A: Final = 25.0
DEFAULT_PHASES: Final = 3

# --- Simulatie ---------------------------------------------------------------

# De coordinator ververst elke UPDATE_INTERVAL_SECONDS seconde. De opdracht
# vraagt 5 tot 10 seconden.
UPDATE_INTERVAL_SECONDS: Final = 5

# Een stap groter dan dit (bijvoorbeeld nadat een Pi in slaap is geweest of na
# een herstart) wordt afgekapt, zodat er geen onrealistische energiesprong in de
# tellers komt.
MAX_STEP_SECONDS: Final = 900.0

# Virtuele apparaten. De vermogens komen uit de opdracht en zijn dus een
# instelling van het lesmateriaal, geen meting aan een echt apparaat.
APPLIANCE_WASMACHINE: Final = "wasmachine"
APPLIANCE_BOILER: Final = "boiler"
APPLIANCE_AIRCO: Final = "airco"

APPLIANCES: Final[dict[str, dict[str, object]]] = {
    APPLIANCE_WASMACHINE: {"power_w": 2000.0, "icon": "mdi:washing-machine"},
    APPLIANCE_BOILER: {"power_w": 2500.0, "icon": "mdi:water-boiler"},
    APPLIANCE_AIRCO: {"power_w": 1200.0, "icon": "mdi:air-conditioner"},
}

# Uurlijkse VORM van de huishoudelijke basislast (ochtend- en avondpiek).
# Dit is een profielvorm, geen absoluut vermogen: de reeks wordt in
# simulation.py genormaliseerd op gemiddelde 1,0 en daarna geschaald met het
# ingestelde jaarverbruik. De piekmomenten volgen het bekende patroon van een
# Nederlands huishouden (ochtendpiek rond 07:00-09:00, avondpiek rond
# 17:00-21:00); de exacte waarden zijn een didactische keuze en staan hier
# bewust zichtbaar zodat een docent ze kan aanpassen.
HOUSEHOLD_PROFILE: Final[tuple[float, ...]] = (
    0.55, 0.50, 0.48, 0.47, 0.48, 0.55, 0.80, 1.30,
    1.35, 1.05, 0.90, 0.85, 0.95, 0.90, 0.85, 0.90,
    1.10, 1.55, 1.85, 1.70, 1.45, 1.25, 0.95, 0.70,
)

# --- Services ----------------------------------------------------------------

SERVICE_SET_SCENARIO: Final = "set_scenario"
SERVICE_RESET: Final = "reset"

ATTR_SCENARIO: Final = "scenario"
ATTR_ONLY_COUNTERS: Final = "alleen_tellers"

# --- Opslag ------------------------------------------------------------------

STORAGE_VERSION: Final = 1
STORAGE_KEY_TEMPLATE: Final = f"{DOMAIN}.{{entry_id}}"
STORAGE_SAVE_DELAY: Final = 10.0

PLATFORMS: Final[list[str]] = ["number", "sensor", "switch"]
