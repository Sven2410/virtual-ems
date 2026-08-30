"""Config flow: installeren en later bijstellen zonder YAML."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
from homeassistant.util import slugify

from .const import (
    CONF_ANNUAL_KWH,
    CONF_BATTERY_KWH,
    CONF_EV_MAX_KW,
    CONF_NAME,
    CONF_PV_PEAK_KWP,
    CONF_START_HOUR,
    DEFAULT_ANNUAL_KWH,
    DEFAULT_BATTERY_KWH,
    DEFAULT_EV_MAX_KW,
    DEFAULT_NAME,
    DEFAULT_PV_PEAK_KWP,
    DOMAIN,
)


def _number(minimum: float, maximum: float, step: float, unit: str) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            unit_of_measurement=unit,
            mode=NumberSelectorMode.BOX,
        )
    )


PV_SELECTOR = _number(0.5, 30.0, 0.1, "kWp")
BATTERY_SELECTOR = _number(0.0, 100.0, 0.5, "kWh")
EV_SELECTOR = _number(1.4, 22.0, 0.1, "kW")
ANNUAL_SELECTOR = _number(500.0, 20000.0, 50.0, "kWh")
HOUR_SELECTOR = _number(0.0, 23.75, 0.25, "uur")


class VirtualEmsConfigFlow(ConfigFlow, domain=DOMAIN):
    """De installatiedialoog van het virtuele EMS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Vraag de docent naar de grootte van de gesimuleerde installatie."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = str(user_input[CONF_NAME]).strip()
            if not name or not slugify(name):
                errors[CONF_NAME] = "ongeldige_naam"
            else:
                await self.async_set_unique_id(slugify(name))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_NAME: name,
                        CONF_PV_PEAK_KWP: float(user_input[CONF_PV_PEAK_KWP]),
                        CONF_BATTERY_KWH: float(user_input[CONF_BATTERY_KWH]),
                        CONF_EV_MAX_KW: float(user_input[CONF_EV_MAX_KW]),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(),
                vol.Required(CONF_PV_PEAK_KWP, default=DEFAULT_PV_PEAK_KWP): PV_SELECTOR,
                vol.Required(CONF_BATTERY_KWH, default=DEFAULT_BATTERY_KWH): BATTERY_SELECTOR,
                vol.Required(CONF_EV_MAX_KW, default=DEFAULT_EV_MAX_KW): EV_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return VirtualEmsOptionsFlow()


class VirtualEmsOptionsFlow(OptionsFlow):
    """Capaciteiten later bijstellen, zonder opnieuw te installeren."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            options = {
                CONF_PV_PEAK_KWP: float(user_input[CONF_PV_PEAK_KWP]),
                CONF_BATTERY_KWH: float(user_input[CONF_BATTERY_KWH]),
                CONF_EV_MAX_KW: float(user_input[CONF_EV_MAX_KW]),
                CONF_ANNUAL_KWH: float(user_input[CONF_ANNUAL_KWH]),
            }
            if user_input.get(CONF_START_HOUR) is not None:
                options[CONF_START_HOUR] = float(user_input[CONF_START_HOUR])
            return self.async_create_entry(title="", data=options)

        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PV_PEAK_KWP,
                    default=current.get(CONF_PV_PEAK_KWP, DEFAULT_PV_PEAK_KWP),
                ): PV_SELECTOR,
                vol.Required(
                    CONF_BATTERY_KWH,
                    default=current.get(CONF_BATTERY_KWH, DEFAULT_BATTERY_KWH),
                ): BATTERY_SELECTOR,
                vol.Required(
                    CONF_EV_MAX_KW,
                    default=current.get(CONF_EV_MAX_KW, DEFAULT_EV_MAX_KW),
                ): EV_SELECTOR,
                vol.Required(
                    CONF_ANNUAL_KWH,
                    default=current.get(CONF_ANNUAL_KWH, DEFAULT_ANNUAL_KWH),
                ): ANNUAL_SELECTOR,
                vol.Optional(
                    CONF_START_HOUR,
                    description={"suggested_value": current.get(CONF_START_HOUR)},
                ): HOUR_SELECTOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
