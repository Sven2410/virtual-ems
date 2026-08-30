"""Proeven op de regelaar: het stuk dat er een systeem van maakt."""

from __future__ import annotations

import pytest

from kernlader import (
    MODUS_HANDMATIG,
    MODUS_PIEKSCHEREN,
    MODUS_ZELFCONSUMPTIE,
    MODUSSEN,
    Situatie,
    bepaal,
)

AANSLUITING = 17250.0  # 3 maal 25 A bij 230 V


def situatie(**kwargs) -> Situatie:
    basis = {
        "pv_w": 0.0,
        "household_w": 400.0,
        "ev_request_w": 0.0,
        "battery_request_w": 0.0,
        "max_charge_w": 5000.0,
        "max_discharge_w": 5000.0,
        "connection_w": AANSLUITING,
    }
    basis.update(kwargs)
    return Situatie(**basis)


def net(besluit, huis: float) -> float:
    """Wat er na het besluit op de aansluiting overblijft."""
    return huis + besluit.ev_w + besluit.battery_w - besluit.pv_w


# --- Handmatig ---------------------------------------------------------------


def test_handmatig_laat_de_cursist_zijn_gang_gaan():
    besluit = bepaal(situatie(battery_request_w=-2500.0), modus=MODUS_HANDMATIG)
    assert besluit.battery_w == -2500.0
    assert besluit.ingegrepen is False
    assert besluit.redenen == []


def test_handmatig_knijpt_wel_af_op_wat_de_batterij_aankan():
    besluit = bepaal(
        situatie(battery_request_w=-9000.0, max_discharge_w=1200.0), modus=MODUS_HANDMATIG
    )
    assert besluit.battery_w == -1200.0


# --- Zelfconsumptie ----------------------------------------------------------


def test_zelfconsumptie_slaat_het_overschot_van_de_zon_op():
    huis = 400.0
    besluit = bepaal(situatie(pv_w=3000.0, household_w=huis), modus=MODUS_ZELFCONSUMPTIE)
    assert besluit.battery_w == pytest.approx(2600.0)
    assert net(besluit, huis) == pytest.approx(0.0)
    assert "laadt" in besluit.reden


def test_zelfconsumptie_dekt_het_tekort_uit_de_batterij():
    huis = 2200.0
    besluit = bepaal(situatie(pv_w=0.0, household_w=huis), modus=MODUS_ZELFCONSUMPTIE)
    assert besluit.battery_w == pytest.approx(-2200.0)
    assert net(besluit, huis) == pytest.approx(0.0)
    assert "ontlaadt" in besluit.reden


def test_zelfconsumptie_belooft_niets_wat_de_batterij_niet_kan():
    """Een lege batterij kan niets dekken, en dan hoort dat er ook te staan."""
    huis = 2200.0
    besluit = bepaal(
        situatie(household_w=huis, max_discharge_w=0.0), modus=MODUS_ZELFCONSUMPTIE
    )
    assert besluit.battery_w == 0.0
    assert net(besluit, huis) == pytest.approx(2200.0)
    assert "niet verder ontladen" in besluit.reden


def test_zelfconsumptie_laadt_niet_verder_dan_er_in_past():
    besluit = bepaal(
        situatie(pv_w=6000.0, household_w=400.0, max_charge_w=1500.0),
        modus=MODUS_ZELFCONSUMPTIE,
    )
    assert besluit.battery_w == pytest.approx(1500.0)


# --- Piekscheren -------------------------------------------------------------


def test_piekscheren_doet_niets_zolang_de_afname_onder_de_grens_blijft():
    besluit = bepaal(
        situatie(household_w=1800.0), modus=MODUS_PIEKSCHEREN, piekgrens_w=3000.0
    )
    assert besluit.battery_w == 0.0
    assert "hoeft niets te doen" in besluit.reden


def test_piekscheren_vult_alleen_het_stuk_boven_de_grens_aan():
    huis = 5200.0
    besluit = bepaal(situatie(household_w=huis), modus=MODUS_PIEKSCHEREN, piekgrens_w=3000.0)
    assert besluit.battery_w == pytest.approx(-2200.0)
    assert net(besluit, huis) == pytest.approx(3000.0)
    assert "3,00 kW" in besluit.reden


def test_piekscheren_zegt_het_als_de_batterij_de_piek_niet_aankan():
    besluit = bepaal(
        situatie(household_w=9000.0, max_discharge_w=1000.0),
        modus=MODUS_PIEKSCHEREN,
        piekgrens_w=3000.0,
    )
    assert besluit.battery_w == pytest.approx(-1000.0)
    # De piek wordt niet gehaald, en dat hoort er dan ook te staan.
    assert "blijft met" in besluit.reden
    assert "boven de grens" in besluit.reden


def test_piekscheren_zegt_het_ook_als_de_batterij_helemaal_niets_kan():
    besluit = bepaal(
        situatie(household_w=9000.0, max_discharge_w=0.0),
        modus=MODUS_PIEKSCHEREN,
        piekgrens_w=3000.0,
    )
    assert besluit.battery_w == 0.0
    assert "kan niet verder ontladen" in besluit.reden


def test_piekscheren_slaat_een_overschot_ook_gewoon_op():
    besluit = bepaal(
        situatie(pv_w=4000.0, household_w=500.0), modus=MODUS_PIEKSCHEREN, piekgrens_w=3000.0
    )
    assert besluit.battery_w == pytest.approx(3500.0)


# --- Het vangnet -------------------------------------------------------------


def test_de_bewaking_stopt_eerst_het_laden_van_de_batterij():
    """Laden kan wachten; dat gaat er dus als eerste af."""
    huis = 5700.0
    besluit = bepaal(
        situatie(household_w=huis, ev_request_w=11000.0, battery_request_w=5000.0),
        modus=MODUS_HANDMATIG,
        bewaking=True,
    )
    assert besluit.ev_w == pytest.approx(11000.0)
    assert besluit.battery_w < 5000.0
    assert net(besluit, huis) <= AANSLUITING + 1e-6
    assert "teruggeregeld voor de aansluiting" in besluit.redenen[0]
    # En verder niets: is het met het laden opgelost, dan hoort er geen tweede
    # reden over de laadpaal bij te staan die niets heeft gedaan.
    assert len(besluit.redenen) == 1


def test_de_bewaking_regelt_daarna_de_laadpaal_terug():
    huis = 9000.0
    besluit = bepaal(
        situatie(household_w=huis, ev_request_w=11000.0),
        modus=MODUS_HANDMATIG,
        bewaking=True,
    )
    assert 0 < besluit.ev_w < 11000.0
    assert net(besluit, huis) <= AANSLUITING + 1e-6
    assert "laadpaal is teruggeregeld" in besluit.reden
    assert besluit.ingegrepen is True


def test_de_bewaking_laat_de_batterij_bijspringen_als_dat_nog_nodig_is():
    """Als de laadpaal al uit staat blijft alleen de batterij over."""
    huis = 19000.0
    besluit = bepaal(
        situatie(household_w=huis, max_discharge_w=5000.0),
        modus=MODUS_HANDMATIG,
        bewaking=True,
    )
    assert besluit.battery_w == pytest.approx(-1750.0)
    assert net(besluit, huis) == pytest.approx(AANSLUITING)
    assert "springt bij" in besluit.reden


def test_de_bewaking_geeft_het_eerlijk_toe_als_het_niet_meer_kan():
    """Een wasmachine kun je niet halverwege afknijpen."""
    huis = 25000.0
    besluit = bepaal(
        situatie(household_w=huis, max_discharge_w=0.0),
        modus=MODUS_HANDMATIG,
        bewaking=True,
    )
    assert besluit.knelpunt is True
    assert net(besluit, huis) > AANSLUITING
    assert "Zet zelf iets uit" in besluit.reden


def test_zonder_bewaking_grijpt_er_niets_in():
    huis = 5700.0
    besluit = bepaal(
        situatie(household_w=huis, ev_request_w=11000.0, battery_request_w=5000.0),
        modus=MODUS_HANDMATIG,
        bewaking=False,
    )
    assert besluit.ev_w == pytest.approx(11000.0)
    assert besluit.battery_w == pytest.approx(5000.0)
    assert besluit.knelpunt is False
    assert net(besluit, huis) > AANSLUITING


def test_de_bewaking_regelt_de_omvormer_terug_bij_te_veel_teruglevering():
    """Een grote installatie op een kleine aansluiting."""
    besluit = bepaal(
        situatie(pv_w=12000.0, household_w=300.0, connection_w=5750.0, max_charge_w=0.0),
        modus=MODUS_HANDMATIG,
        bewaking=True,
    )
    assert besluit.pv_w < 12000.0
    assert abs(net(besluit, 300.0)) <= 5750.0 + 1e-6
    assert "omvormer is" in besluit.reden


def test_de_bewaking_zet_de_teruglevering_liever_in_de_batterij_dan_hem_weg_te_gooien():
    besluit = bepaal(
        situatie(pv_w=9000.0, household_w=300.0, connection_w=5750.0, max_charge_w=5000.0),
        modus=MODUS_HANDMATIG,
        bewaking=True,
    )
    assert besluit.pv_w == pytest.approx(9000.0)
    assert besluit.battery_w > 0
    assert "batterij vangt" in besluit.reden


# --- Vorm --------------------------------------------------------------------


def test_elke_modus_geeft_een_besluit_zonder_te_klappen():
    for modus in MODUSSEN:
        besluit = bepaal(situatie(pv_w=1500.0, household_w=800.0), modus=modus, piekgrens_w=2000.0)
        assert besluit.ev_w >= 0
        assert besluit.pv_w >= 0


def test_een_ingreep_krijgt_altijd_een_reden_mee():
    huis = 9000.0
    besluit = bepaal(
        situatie(household_w=huis, ev_request_w=11000.0), modus=MODUS_HANDMATIG, bewaking=True
    )
    assert besluit.ingegrepen is True
    assert besluit.redenen
    for reden in besluit.redenen:
        assert reden.endswith(".")
        assert "—" not in reden


def test_de_grootste_ingreep_staat_bovenaan_en_niet_de_laatste():
    """Gemeten in de praktijk: de kop toonde een ingreep van twintig watt.

    Alles aan geeft ruim 5 kW te veel. Het laden van de batterij gaat er als
    eerste af, en daarna hoeft de laadpaal nog maar een fractie terug. Zou de
    volgorde van de redenen omgekeerd staan, dan las de cursist bovenaan dat de
    laadpaal van 11,00 naar 10,98 kW ging, terwijl er 5 kW aan laden was
    weggehaald.
    """
    # Alles aan en een huis dat net iets meer vraagt dan het laden dekt, zodat
    # de laadpaal er nog een fractie af moet.
    huis = 6300.0
    besluit = bepaal(
        situatie(household_w=huis, ev_request_w=11000.0, battery_request_w=5000.0),
        modus=MODUS_HANDMATIG,
        bewaking=True,
    )
    assert len(besluit.redenen) >= 2
    assert "batterij" in besluit.redenen[0]
    assert "laadpaal" in besluit.redenen[1]
    assert net(besluit, huis) <= AANSLUITING + 1e-6


def test_een_knelpunt_staat_altijd_vooraan():
    huis = 30000.0
    besluit = bepaal(
        situatie(household_w=huis, ev_request_w=11000.0, battery_request_w=5000.0),
        modus=MODUS_HANDMATIG,
        bewaking=True,
    )
    assert besluit.knelpunt is True
    assert "Zet zelf iets uit" in besluit.redenen[0]
