"""Proeven op de rekenkern.

Deze proeven draaien zonder Home Assistant: alleen Python en pytest. Daardoor
is de hele dag door te rekenen zonder dat er ergens een integratie opgestart
hoeft te worden.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from kernlader import PlantConfig, Simulation, solar_position

AMSTERDAM = ZoneInfo("Europe/Amsterdam")

# 21 juni 2026, de langste dag: hier is de zonnestand met een onafhankelijke
# formule na te rekenen.
MIDZOMER = datetime(2026, 6, 21, 0, 0, tzinfo=AMSTERDAM)
MIDWINTER = datetime(2026, 12, 21, 0, 0, tzinfo=AMSTERDAM)


def maak_simulatie(**kwargs) -> Simulation:
    config = PlantConfig(**kwargs)
    return Simulation(config, seed=42)


# --- Zonnestand --------------------------------------------------------------


def test_zonnehoogte_op_de_langste_dag_klopt_met_de_meetkunde():
    """Op de zonnewende is de hoogte 90 - breedtegraad + scheefstand.

    De scheefstand van de aardas is 23,44 graden. Op 21 juni staat de zon in
    Amersfoort (52,156 graden noorderbreedte) dus op ongeveer 61,3 graden.
    """
    breedte = 52.156
    verwacht = 90.0 - breedte + 23.44

    hoogste = max(
        solar_position(MIDZOMER + timedelta(minutes=minuut), breedte, 5.388)[0]
        for minuut in range(0, 24 * 60, 5)
    )
    assert hoogste == pytest.approx(verwacht, abs=0.5)


def test_zon_staat_op_zijn_hoogst_pal_in_het_zuiden():
    breedte, lengte = 52.156, 5.388
    standen = [
        (solar_position(MIDZOMER + timedelta(minutes=m), breedte, lengte), m)
        for m in range(0, 24 * 60)
    ]
    (hoogte, azimut), _minuut = max(standen, key=lambda paar: paar[0][0])
    assert hoogte > 0
    assert azimut == pytest.approx(180.0, abs=1.0)


def test_zon_staat_s_ochtends_in_het_oosten_en_s_avonds_in_het_westen():
    """De azimut moet per kwadrant kloppen, niet alleen op het middaguur.

    Een berekening met één acos geeft 's ochtends en 's avonds dezelfde
    uitkomst; dan staat de zon een halve dag aan de verkeerde kant van de hemel
    en klaagt niemand, want de hoogte klopt wel.
    """
    breedte, lengte = 52.156, 5.388
    _hoogte_ochtend, azimut_ochtend = solar_position(
        datetime(2026, 6, 21, 8, 0, tzinfo=AMSTERDAM), breedte, lengte
    )
    _hoogte_avond, azimut_avond = solar_position(
        datetime(2026, 6, 21, 18, 0, tzinfo=AMSTERDAM), breedte, lengte
    )
    assert 45.0 < azimut_ochtend < 135.0
    assert 225.0 < azimut_avond < 315.0


def test_zon_staat_s_nachts_onder_de_horizon():
    hoogte, _azimut = solar_position(
        datetime(2026, 6, 21, 1, 0, tzinfo=AMSTERDAM), 52.156, 5.388
    )
    assert hoogte < 0


def test_winterzon_komt_lager_dan_zomerzon():
    def hoogste(dag: datetime) -> float:
        return max(
            solar_position(dag + timedelta(minutes=m), 52.156, 5.388)[0]
            for m in range(0, 24 * 60, 5)
        )

    assert hoogste(MIDWINTER) < hoogste(MIDZOMER) - 40


# --- PV ----------------------------------------------------------------------


def test_pv_levert_niets_in_het_donker():
    sim = maak_simulatie()
    snapshot = sim.step(datetime(2026, 6, 21, 1, 0, tzinfo=AMSTERDAM), 60)
    assert snapshot.pv_power_w == 0.0


def test_pv_levert_overdag_maar_nooit_meer_dan_de_piek():
    sim = maak_simulatie(pv_peak_kwp=4.0)
    moment = datetime(2026, 6, 21, 0, 0, tzinfo=AMSTERDAM)
    hoogste = 0.0
    for _ in range(24 * 60):
        snapshot = sim.step(moment, 60)
        hoogste = max(hoogste, snapshot.pv_power_w)
        moment += timedelta(minutes=1)
    assert 0 < hoogste <= 4000.0


def test_bewolking_verlaagt_de_opbrengst_evenredig():
    moment = datetime(2026, 6, 21, 13, 0, tzinfo=AMSTERDAM)

    helder = maak_simulatie()
    vol_vermogen = helder.step(moment, 60).pv_power_w

    half = maak_simulatie()
    half.setpoints.cloud_pct = 50.0
    half_vermogen = half.step(moment, 60).pv_power_w

    dicht = maak_simulatie()
    dicht.setpoints.cloud_pct = 100.0
    dicht_vermogen = dicht.step(moment, 60).pv_power_w

    assert half_vermogen == pytest.approx(vol_vermogen / 2.0, rel=1e-9)
    assert dicht_vermogen == 0.0


# --- Batterij ----------------------------------------------------------------


def test_soc_blijft_altijd_tussen_nul_en_honderd():
    """Een hele dag met willekeurige bediening mag de grenzen nooit passeren."""
    sim = maak_simulatie(battery_capacity_kwh=10.0)
    sim.setpoints.soc_min_pct = 0.0
    sim.setpoints.soc_max_pct = 100.0
    trekking = random.Random(7)
    moment = datetime(2026, 3, 15, 0, 0, tzinfo=AMSTERDAM)

    for _ in range(24 * 60):
        sim.setpoints.battery_setpoint_w = trekking.uniform(-50000, 50000)
        snapshot = sim.step(moment, 60)
        assert 0.0 <= snapshot.battery_soc_pct <= 100.0
        assert 0.0 <= snapshot.battery_energy_kwh <= 10.0
        moment += timedelta(minutes=1)


def test_batterij_laadt_niet_boven_de_ingestelde_bovengrens():
    sim = maak_simulatie(battery_capacity_kwh=10.0)
    sim.setpoints.soc_max_pct = 80.0
    sim.setpoints.battery_setpoint_w = 5000.0
    sim.set_soc_pct(79.0)

    moment = datetime(2026, 3, 15, 12, 0, tzinfo=AMSTERDAM)
    for _ in range(60):
        snapshot = sim.step(moment, 60)
        assert snapshot.battery_soc_pct <= 80.0 + 1e-9
        moment += timedelta(minutes=1)
    assert sim.soc_pct == pytest.approx(80.0, abs=1e-6)


def test_batterij_ontlaadt_niet_onder_de_ingestelde_ondergrens():
    sim = maak_simulatie(battery_capacity_kwh=10.0)
    sim.setpoints.soc_min_pct = 20.0
    sim.setpoints.battery_setpoint_w = -5000.0
    sim.set_soc_pct(21.0)

    moment = datetime(2026, 3, 15, 12, 0, tzinfo=AMSTERDAM)
    for _ in range(60):
        snapshot = sim.step(moment, 60)
        assert snapshot.battery_soc_pct >= 20.0 - 1e-9
        moment += timedelta(minutes=1)
    assert sim.soc_pct == pytest.approx(20.0, abs=1e-6)


def test_vermogen_wordt_afgeknepen_bij_het_naderen_van_de_grens():
    """Vlak voor de bovengrens levert de batterij minder dan het verzoek."""
    sim = maak_simulatie(battery_capacity_kwh=10.0)
    sim.setpoints.soc_max_pct = 100.0
    sim.setpoints.battery_setpoint_w = 5000.0
    sim.set_soc_pct(99.9)

    snapshot = sim.step(datetime(2026, 3, 15, 12, 0, tzinfo=AMSTERDAM), 60)
    assert 0 < snapshot.battery_power_w < 5000.0


def test_c_rate_begrenst_het_gevraagde_vermogen():
    sim = maak_simulatie(battery_capacity_kwh=10.0, battery_c_rate=0.5)
    assert sim.config.battery_max_power_w == 5000.0

    sim.setpoints.battery_setpoint_w = 99000.0
    snapshot = sim.step(datetime(2026, 3, 15, 12, 0, tzinfo=AMSTERDAM), 60)
    assert snapshot.battery_power_w == pytest.approx(5000.0)


def test_omgedraaide_grenzen_worden_verwisseld_in_plaats_van_geweigerd():
    sim = maak_simulatie(battery_capacity_kwh=10.0)
    sim.setpoints.soc_min_pct = 80.0
    sim.setpoints.soc_max_pct = 20.0
    sim.setpoints.battery_setpoint_w = 5000.0
    sim.set_soc_pct(50.0)

    for _ in range(30):
        snapshot = sim.step(datetime(2026, 3, 15, 12, 0, tzinfo=AMSTERDAM), 60)
        assert 20.0 - 1e-9 <= snapshot.battery_soc_pct <= 80.0 + 1e-9


def test_retourrendement_komt_uit_op_negentig_procent():
    """Laad de batterij vol en ontlaad hem weer: er blijft 90 procent over."""
    sim = maak_simulatie(battery_capacity_kwh=10.0, round_trip_efficiency=0.90)
    sim.setpoints.soc_min_pct = 0.0
    sim.setpoints.soc_max_pct = 100.0
    sim.set_soc_pct(0.0)

    moment = datetime(2026, 3, 15, 0, 0, tzinfo=AMSTERDAM)
    sim.setpoints.battery_setpoint_w = 5000.0
    for _ in range(300):
        sim.step(moment, 60)
        moment += timedelta(minutes=1)
    assert sim.soc_pct == pytest.approx(100.0, abs=1e-6)

    sim.setpoints.battery_setpoint_w = -5000.0
    for _ in range(300):
        sim.step(moment, 60)
        moment += timedelta(minutes=1)
    assert sim.soc_pct == pytest.approx(0.0, abs=1e-6)

    verhouding = sim.totals.battery_discharged_kwh / sim.totals.battery_charged_kwh
    assert verhouding == pytest.approx(0.90, rel=1e-6)


# --- Laadpaal ----------------------------------------------------------------


def test_laadpaal_loopt_op_in_plaats_van_te_springen():
    sim = maak_simulatie(ev_max_power_w=11000.0)
    sim.setpoints.ev_enabled = True
    sim.setpoints.ev_setpoint_w = 11000.0
    moment = datetime(2026, 3, 15, 19, 0, tzinfo=AMSTERDAM)

    na_een_seconde = sim.step(moment, 1).ev_power_w
    assert 0 < na_een_seconde < 11000.0

    for _ in range(20):
        snapshot = sim.step(moment, 1)
    assert snapshot.ev_power_w == pytest.approx(11000.0)


def test_laadpaal_uit_betekent_terug_naar_nul():
    sim = maak_simulatie(ev_max_power_w=11000.0)
    sim.setpoints.ev_enabled = True
    sim.setpoints.ev_setpoint_w = 11000.0
    moment = datetime(2026, 3, 15, 19, 0, tzinfo=AMSTERDAM)
    for _ in range(30):
        sim.step(moment, 1)

    sim.setpoints.ev_enabled = False
    for _ in range(30):
        snapshot = sim.step(moment, 1)
    assert snapshot.ev_power_w == 0.0


def test_laadvermogen_wordt_begrensd_door_de_installatie():
    sim = maak_simulatie(ev_max_power_w=11000.0)
    sim.setpoints.ev_enabled = True
    sim.setpoints.ev_setpoint_w = 22000.0
    moment = datetime(2026, 3, 15, 19, 0, tzinfo=AMSTERDAM)
    for _ in range(60):
        snapshot = sim.step(moment, 1)
    assert snapshot.ev_power_w == pytest.approx(11000.0)


# --- Huishouden --------------------------------------------------------------


def test_apparaat_verhoogt_het_verbruik_met_precies_zijn_vermogen():
    moment = datetime(2026, 3, 15, 14, 0, tzinfo=AMSTERDAM)

    zonder = maak_simulatie()
    basis = zonder.step(moment, 60).household_power_w

    met = maak_simulatie()
    met.setpoints.appliances["wasmachine"] = True
    met_apparaat = met.step(moment, 60).household_power_w

    assert met_apparaat - basis == pytest.approx(2000.0, abs=1e-9)


def test_basislast_heeft_een_ochtend_en_een_avondpiek():
    per_uur = {}
    for uur in range(24):
        deel = maak_simulatie()
        deel._noise = 0.0
        per_uur[uur] = deel.base_load(datetime(2026, 3, 15, uur, 0, tzinfo=AMSTERDAM))

    assert per_uur[8] > per_uur[3]
    assert per_uur[18] > per_uur[14]
    assert max(per_uur, key=per_uur.get) in (17, 18, 19)


def test_basislast_schaalt_mee_met_het_ingestelde_jaarverbruik():
    klein = maak_simulatie(annual_consumption_kwh=2000.0)
    groot = maak_simulatie(annual_consumption_kwh=4000.0)
    klein._noise = 0.0
    groot._noise = 0.0
    moment = datetime(2026, 3, 15, 14, 0, tzinfo=AMSTERDAM)
    assert groot.base_load(moment) == pytest.approx(2.0 * klein.base_load(moment))


# --- Netaansluiting ----------------------------------------------------------


def test_net_vermogen_is_de_optelsom_van_alle_stromen():
    """Bij elke stap moet gelden: net = huis + laadpaal + batterij - pv."""
    sim = maak_simulatie()
    trekking = random.Random(11)
    moment = datetime(2026, 5, 10, 0, 0, tzinfo=AMSTERDAM)

    for _ in range(24 * 12):
        sim.setpoints.cloud_pct = trekking.uniform(0, 100)
        sim.setpoints.battery_setpoint_w = trekking.uniform(-6000, 6000)
        sim.setpoints.ev_enabled = trekking.random() > 0.5
        sim.setpoints.ev_setpoint_w = trekking.uniform(0, 11000)
        for naam in ("wasmachine", "boiler", "airco"):
            sim.setpoints.appliances[naam] = trekking.random() > 0.5

        s = sim.step(moment, 300)
        verwacht = s.household_power_w + s.ev_power_w + s.battery_power_w - s.pv_power_w
        assert s.grid_power_w == pytest.approx(verwacht, abs=1e-9)
        moment += timedelta(minutes=5)


def test_teruglevering_krijgt_een_negatief_netvermogen():
    sim = maak_simulatie(pv_peak_kwp=8.0, annual_consumption_kwh=1000.0)
    snapshot = sim.step(datetime(2026, 6, 21, 13, 0, tzinfo=AMSTERDAM), 60)
    assert snapshot.pv_power_w > snapshot.household_power_w
    assert snapshot.grid_power_w < 0


def test_afname_en_teruglevering_zijn_gescheiden_tellers():
    sim = maak_simulatie(pv_peak_kwp=8.0, annual_consumption_kwh=1000.0)
    moment = datetime(2026, 6, 21, 0, 0, tzinfo=AMSTERDAM)
    for _ in range(24 * 6):
        sim.step(moment, 600)
        moment += timedelta(minutes=10)

    assert sim.totals.grid_import_kwh > 0
    assert sim.totals.grid_export_kwh > 0


def test_energiebalans_over_een_hele_dag_klopt():
    """Wat er het huis in gaat moet gelijk zijn aan wat eruit komt.

    afname - teruglevering = huis + laadpaal + laden - ontladen - pv
    """
    sim = maak_simulatie(pv_peak_kwp=6.0, battery_capacity_kwh=10.0)
    trekking = random.Random(3)
    moment = datetime(2026, 4, 12, 0, 0, tzinfo=AMSTERDAM)

    for stap in range(24 * 60):
        if stap % 30 == 0:
            sim.setpoints.cloud_pct = trekking.uniform(0, 60)
            sim.setpoints.battery_setpoint_w = trekking.uniform(-5000, 5000)
            sim.setpoints.ev_enabled = trekking.random() > 0.7
            sim.setpoints.ev_setpoint_w = trekking.uniform(0, 11000)
            sim.setpoints.appliances["boiler"] = trekking.random() > 0.8
        sim.step(moment, 60)
        moment += timedelta(minutes=1)

    t = sim.totals
    links = t.grid_import_kwh - t.grid_export_kwh
    rechts = (
        t.household_kwh
        + t.ev_kwh
        + t.battery_charged_kwh
        - t.battery_discharged_kwh
        - t.pv_kwh
    )
    assert links == pytest.approx(rechts, abs=1e-6)
    assert t.pv_kwh > 0
    assert t.household_kwh > 0


def test_tellers_lopen_alleen_op():
    sim = maak_simulatie()
    trekking = random.Random(5)
    moment = datetime(2026, 4, 12, 0, 0, tzinfo=AMSTERDAM)
    vorige = sim.totals.as_dict()

    for _ in range(200):
        sim.setpoints.battery_setpoint_w = trekking.uniform(-5000, 5000)
        sim.step(moment, 60)
        huidige = sim.totals.as_dict()
        for sleutel, waarde in huidige.items():
            if isinstance(waarde, (int, float)):
                assert waarde >= vorige[sleutel] - 1e-12, sleutel
        vorige = huidige
        moment += timedelta(minutes=1)


# --- Beheer ------------------------------------------------------------------


def test_reset_zet_de_tellers_en_de_soc_terug():
    sim = maak_simulatie(battery_capacity_kwh=10.0)
    sim.setpoints.battery_setpoint_w = 3000.0
    sim.setpoints.appliances["boiler"] = True
    moment = datetime(2026, 4, 12, 12, 0, tzinfo=AMSTERDAM)
    for _ in range(60):
        sim.step(moment, 60)
        moment += timedelta(minutes=1)

    assert sim.totals.household_kwh > 0

    sim.reset()

    for sleutel, waarde in sim.totals.as_dict().items():
        if isinstance(waarde, (int, float)):
            assert waarde == 0.0, sleutel
    for naam, waarde in sim.totals.appliance_kwh.items():
        assert waarde == 0.0, naam
    assert sim.soc_pct == pytest.approx(50.0)
    assert sim.setpoints.battery_setpoint_w == 0.0
    assert sim.setpoints.appliances["boiler"] is False


def test_reset_met_alleen_tellers_laat_de_bediening_staan():
    sim = maak_simulatie()
    sim.setpoints.battery_setpoint_w = 3000.0
    sim.setpoints.cloud_pct = 40.0
    sim.setpoints.appliances["airco"] = True
    sim.step(datetime(2026, 4, 12, 12, 0, tzinfo=AMSTERDAM), 600)

    sim.reset(only_counters=True)

    assert sim.totals.household_kwh == 0.0
    assert sim.setpoints.battery_setpoint_w == 3000.0
    assert sim.setpoints.cloud_pct == 40.0
    assert sim.setpoints.appliances["airco"] is True


def test_opslaan_en_terugzetten_geeft_dezelfde_toestand():
    sim = maak_simulatie()
    sim.setpoints.cloud_pct = 30.0
    sim.setpoints.appliances["wasmachine"] = True
    sim.setpoints.battery_setpoint_w = -1500.0
    moment = datetime(2026, 4, 12, 12, 0, tzinfo=AMSTERDAM)
    for _ in range(10):
        sim.step(moment, 60)
        moment += timedelta(minutes=1)

    bewaard = sim.as_dict()

    nieuw = maak_simulatie()
    nieuw.restore(bewaard)

    assert nieuw.soc_pct == pytest.approx(sim.soc_pct)
    assert nieuw.totals.as_dict() == sim.totals.as_dict()
    assert nieuw.setpoints.cloud_pct == 30.0
    assert nieuw.setpoints.appliances["wasmachine"] is True


def test_een_hele_lange_stap_wordt_afgekapt():
    """Na een herstart of een slapende Pi mag er geen energiesprong ontstaan."""
    sim = maak_simulatie()
    sim.setpoints.battery_setpoint_w = 0.0
    snapshot = sim.step(datetime(2026, 4, 12, 12, 0, tzinfo=AMSTERDAM), 86400)
    assert snapshot.elapsed_s == 900.0


def test_stap_zonder_tijdsverloop_verandert_de_tellers_niet():
    sim = maak_simulatie()
    moment = datetime(2026, 4, 12, 12, 0, tzinfo=AMSTERDAM)
    sim.step(moment, 60)
    voor = sim.totals.as_dict()
    sim.step(moment, 0)
    assert sim.totals.as_dict() == voor


def test_batterij_zonder_capaciteit_gaat_niet_stuk():
    sim = maak_simulatie(battery_capacity_kwh=0.0)
    sim.setpoints.battery_setpoint_w = 1000.0
    snapshot = sim.step(datetime(2026, 4, 12, 12, 0, tzinfo=AMSTERDAM), 60)
    assert snapshot.battery_power_w == 0.0
    assert snapshot.battery_soc_pct == 0.0
    assert not math.isnan(snapshot.grid_power_w)
