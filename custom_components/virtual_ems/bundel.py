"""De frontendbundel van virtual_ems aanmelden bij Home Assistant.

Dit bestand heet bundel.py en niet frontend.py: naast deze map staat de map
frontend/ met de javascript erin, en twee dingen met dezelfde naam in dezelfde
map is vragen om een importfout die niemand terugvindt.

De integratie zet zijn eigen bundel op een eigen URL, meldt hem aan bij de
frontend en registreert hem als Lovelace-resource. De klant hoeft dus niets toe
te voegen: geen resource intikken, geen bestand kopieren.

De URL krijgt een ?v= met de hash van de frontendmap, berekend bij het opzetten
van de config entry. Zelfde hash betekent zelfde bestand, en een andere hash
betekent een andere URL, waar geen cache tussen kan zitten. Diezelfde hash komt
ook als kenmerk op een entiteit te staan, zodat een scherm dat oude code draait
dat zelf kan merken.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .bundelversie import URL_BASIS, bereken_versie, bundel_url, frontend_map
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_VLAG = f"{DOMAIN}_frontend_aangemeld"

__all__ = ["URL_BASIS", "async_setup_frontend", "bereken_versie", "bundel_url", "frontend_map"]


async def async_setup_frontend(hass: HomeAssistant) -> str:
    """Meld de bundel aan. Geeft de versie terug.

    Dit gebeurt één keer per Home Assistant, ook als er meerdere installaties
    draaien: een tweede keer hetzelfde pad aanmelden is een fout.
    """
    versie: str = await hass.async_add_executor_job(bereken_versie)

    if hass.data.get(_VLAG):
        return str(hass.data[_VLAG])

    pad = frontend_map()
    if not pad.is_dir():
        _LOGGER.warning("De map met de frontend ontbreekt: %s", pad)
        return versie

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(URL_BASIS, str(pad), False)]
        )
    except (ImportError, AttributeError):
        # Oudere versies kennen StaticPathConfig nog niet.
        hass.http.register_static_path(URL_BASIS, str(pad), False)
    except RuntimeError as fout:
        # Al aangemeld door een eerdere config entry; dat is geen probleem.
        _LOGGER.debug("Het pad naar de frontend stond er al: %s", fout)

    url = bundel_url(versie)

    try:
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, url)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("De frontend kon niet bij Home Assistant aangemeld worden")

    await _async_registreer_resource(hass, url)

    hass.data[_VLAG] = versie
    _LOGGER.info("De frontend van virtual_ems staat klaar op %s", url)
    return versie


async def _async_registreer_resource(hass: HomeAssistant, url: str) -> bool:
    """Zet de bundel ook in de lijst met Lovelace-resources.

    Dit is met opzet vergevingsgezind. In YAML-modus is die lijst niet te
    bewerken, en dan is er niets aan de hand: de bundel is al aangemeld bij de
    frontend en wordt op elke pagina geladen.
    """
    gegevens: Any = hass.data.get("lovelace")
    resources = getattr(gegevens, "resources", None)
    if resources is None and isinstance(gegevens, dict):
        resources = gegevens.get("resources")
    if resources is None:
        _LOGGER.debug("Lovelace is nog niet klaar, de resource wordt overgeslagen")
        return False

    try:
        if hasattr(resources, "async_get_info"):
            await resources.async_get_info()
        if not hasattr(resources, "async_items"):
            return False

        kaal = url.split("?")[0]
        for item in resources.async_items():
            if str(item.get("url", "")).split("?")[0] != kaal:
                continue
            if item.get("url") == url:
                return True
            if hasattr(resources, "async_update_item"):
                await resources.async_update_item(item["id"], {"url": url})
                return True
            return False

        if hasattr(resources, "async_create_item"):
            await resources.async_create_item({"res_type": "module", "url": url})
            return True
    except Exception as fout:  # noqa: BLE001
        _LOGGER.debug("De Lovelace-resource kon niet gezet worden: %s", fout)
    return False
