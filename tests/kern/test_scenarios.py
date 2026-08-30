"""Proeven op de lesscenario's."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from kernlader import SCENARIOS, PlantConfig, Simulation, apply_scenario

AMSTERDAM = ZoneInfo("Europe/Amsterdam")


def maak_simulatie() -> Simulation:
    return Simulation(PlantConfig(), seed=1)


def draai(sim: Simulation, uur: float, minuten: int = 10) -> None:
    moment = datetime(2026, 5, 20, int(uur), 0, tzinfo=AMSTERDAM)
    for _ in range(minuten):
        sim.step(moment, 60)
        moment += timedelta(minutes=1)


def test_elk_scenario_is_toe_te_passen():
    for sleutel, scenario in SCENARIOS.items():
        sim = maak_simulatie()
        apply_scenario(sim, scenario)
        assert sim.setpoints.cloud_pct == scenario.cloud_pct, sleutel
        assert sim.soc_pct == pytest.approx(scenario.soc_pct), sleutel
        assert set(sim.setpoints.appliances) == {
            naam for naam, _vermogen in sim.config.appliances
        }, sleutel


def test_scenario_laat_de_tellers_staan():
    """Een scenario zet een lessituatie klaar; terugzetten is een aparte knop."""
    sim = maak_simulatie()
    draai(sim, 12)
    voor = sim.totals.pv_kwh
    assert voor > 0

    apply_scenario(sim, SCENARIOS["bewolkte_dag"])
    assert sim.totals.pv_kwh == voor


def test_zonnige_dag_levert_daadwerkelijk_zon():
    sim = maak_simulatie()
    scenario = SCENARIOS["zonnige_dag"]
    apply_scenario(sim, scenario)
    draai(sim, scenario.start_hour)
    assert sim.last_snapshot.pv_power_w > 0
    assert sim.setpoints.cloud_pct == 0.0


def test_bewolkte_dag_levert_veel_minder_dan_een_zonnige_dag():
    zon = maak_simulatie()
    apply_scenario(zon, SCENARIOS["zonnige_dag"])
    draai(zon, 12, minuten=1)

    wolk = maak_simulatie()
    apply_scenario(wolk, SCENARIOS["bewolkte_dag"])
    draai(wolk, 12, minuten=1)

    assert wolk.last_snapshot.pv_power_w < zon.last_snapshot.pv_power_w / 2


def test_piekbelasting_avond_geeft_een_forse_netafname():
    sim = maak_simulatie()
    scenario = SCENARIOS["piekbelasting_avond"]
    apply_scenario(sim, scenario)
    draai(sim, scenario.start_hour, minuten=5)

    snapshot = sim.last_snapshot
    assert snapshot.ev_power_w == pytest.approx(11000.0)
    # Wasmachine (2000 W) en boiler (2500 W) staan aan, plus de basislast.
    assert snapshot.household_power_w > 4500.0
    assert snapshot.grid_power_w > 15000.0


def test_lege_batterij_start_werkelijk_bijna_leeg():
    sim = maak_simulatie()
    apply_scenario(sim, SCENARIOS["lege_batterij"])
    assert sim.soc_pct == pytest.approx(5.0)
    assert sim.setpoints.soc_min_pct == 0.0


def test_scenario_zet_de_laadpaal_terug_op_nul_voor_de_oploop():
    """Anders begint de piek met het vermogen van het vorige scenario."""
    sim = maak_simulatie()
    sim.setpoints.ev_enabled = True
    sim.setpoints.ev_setpoint_w = 11000.0
    draai(sim, 19, minuten=2)
    assert sim.ev_power_w > 0

    apply_scenario(sim, SCENARIOS["zonnige_dag"])
    assert sim.ev_power_w == 0.0
