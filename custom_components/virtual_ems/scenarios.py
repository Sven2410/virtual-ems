"""Lesscenario's voor het virtuele EMS.

Ook dit bestand is losse Python zonder Home Assistant-imports: een scenario is
niets anders dan een setje instellingen dat in één keer op de simulatie wordt
gezet. Daardoor is elk scenario in een gewone unittest door te rekenen.
"""

from __future__ import annotations

from dataclasses import dataclass

from .simulation import Setpoints, Simulation


@dataclass(frozen=True)
class Scenario:
    """Eén complete lessituatie."""

    key: str
    #: Bewolking in procent.
    cloud_pct: float
    #: Start-SoC van de batterij in procent.
    soc_pct: float
    #: Doelvermogen van de batterij in W (negatief is ontladen).
    battery_setpoint_w: float = 0.0
    #: Ondergrens waaronder de batterij niet verder ontlaadt, in procent.
    soc_min_pct: float = 10.0
    ev_enabled: bool = False
    ev_setpoint_w: float = 0.0
    appliances_on: tuple[str, ...] = ()
    #: Uur van de dag waarop de gesimuleerde dag gezet wordt. None laat de
    #: simulatieklok staan waar hij staat.
    start_hour: float | None = None
    #: Tijdversnelling die bij dit scenario hoort.
    time_factor: float = 1.0


SCENARIOS: dict[str, Scenario] = {
    # Volop zon rond het middaguur: de PV levert meer dan het huis vraagt, dus
    # er gaat vanzelf stroom terug het net op tenzij de cursist iets doet.
    "zonnige_dag": Scenario(
        key="zonnige_dag",
        cloud_pct=0.0,
        soc_pct=30.0,
        battery_setpoint_w=0.0,
        start_hour=12.0,
        time_factor=10.0,
    ),
    # Zwaar bewolkte dag: nauwelijks opbrengst, het huis hangt aan het net.
    "bewolkte_dag": Scenario(
        key="bewolkte_dag",
        cloud_pct=85.0,
        soc_pct=50.0,
        battery_setpoint_w=0.0,
        start_hour=12.0,
        time_factor=10.0,
    ),
    # Avondpiek: geen zon, auto aan de lader en twee zware apparaten aan.
    "piekbelasting_avond": Scenario(
        key="piekbelasting_avond",
        cloud_pct=0.0,
        soc_pct=70.0,
        battery_setpoint_w=0.0,
        ev_enabled=True,
        ev_setpoint_w=11000.0,
        appliances_on=("wasmachine", "boiler"),
        start_hour=19.0,
        time_factor=10.0,
    ),
    # Lege batterij aan het begin van de dag: eerst laden, dan pas luxe.
    "lege_batterij": Scenario(
        key="lege_batterij",
        cloud_pct=20.0,
        soc_pct=5.0,
        battery_setpoint_w=0.0,
        soc_min_pct=0.0,
        start_hour=9.0,
        time_factor=10.0,
    ),
}


def apply_scenario(simulation: Simulation, scenario: Scenario) -> None:
    """Zet een scenario op de simulatie.

    De tellers blijven staan: een scenario zet een lessituatie klaar, het is
    geen reset. Wil de docent ook schoon beginnen, dan is daar de reset-service
    voor.
    """
    setpoints = Setpoints(
        cloud_pct=scenario.cloud_pct,
        battery_setpoint_w=scenario.battery_setpoint_w,
        soc_min_pct=scenario.soc_min_pct,
        soc_max_pct=100.0,
        ev_enabled=scenario.ev_enabled,
        ev_setpoint_w=scenario.ev_setpoint_w,
        time_factor=scenario.time_factor,
        appliances={
            name: name in scenario.appliances_on for name, _power in simulation.config.appliances
        },
    )
    simulation.setpoints = setpoints
    simulation.set_soc_pct(scenario.soc_pct)
    simulation.ev_power_w = 0.0
