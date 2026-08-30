"""Proeven op de hoofdzekering."""

from __future__ import annotations

import pytest

from kernlader import Zekering

NOMINAAL = 17250.0  # 3 maal 25 A bij 230 V
UUR = 3600.0


def draai(zekering: Zekering, vermogen: float, seconden: float, stap: float = 10.0) -> float:
    """Belast de zekering en geef terug na hoeveel seconden hij doorsmolt."""
    verstreken = 0.0
    while verstreken < seconden:
        if zekering.stap(vermogen, stap):
            return verstreken + stap
        verstreken += stap
    return -1.0


def test_binnen_de_aansluitwaarde_gebeurt_er_niets():
    zekering = Zekering(nominaal_w=NOMINAAL)
    assert draai(zekering, NOMINAAL, 4 * UUR) == -1.0
    assert zekering.warmte == 0.0
    assert zekering.gesprongen is False


def test_de_conventionele_niet_smeltstroom_smelt_niet_binnen_de_conventionele_tijd():
    """IEC 60269-1: bij 1,25 keer de nominale stroom houdt een gG het een uur uit."""
    zekering = Zekering(nominaal_w=NOMINAAL)
    assert draai(zekering, NOMINAAL * 1.25, UUR) == -1.0
    assert zekering.gesprongen is False


def test_de_conventionele_smeltstroom_smelt_wel_binnen_de_conventionele_tijd():
    """IEC 60269-1: bij 1,6 keer de nominale stroom smelt hij binnen het uur."""
    zekering = Zekering(nominaal_w=NOMINAAL)
    tijd = draai(zekering, NOMINAAL * 1.6, 2 * UUR)
    assert tijd > 0
    assert tijd == pytest.approx(UUR, rel=0.02)
    assert zekering.gesprongen is True


def test_zwaarder_belasten_gaat_sneller():
    tijden = []
    for factor in (1.8, 2.5, 4.0):
        zekering = Zekering(nominaal_w=NOMINAAL)
        tijden.append(draai(zekering, NOMINAAL * factor, 4 * UUR, stap=1.0))
    assert all(tijd > 0 for tijd in tijden)
    assert tijden[0] > tijden[1] > tijden[2]


def test_teruglevering_belast_de_zekering_net_zo_goed():
    zekering = Zekering(nominaal_w=NOMINAAL)
    tijd = draai(zekering, -NOMINAAL * 1.6, 2 * UUR)
    assert tijd == pytest.approx(UUR, rel=0.02)


def test_de_zekering_koelt_weer_af():
    zekering = Zekering(nominaal_w=NOMINAAL)
    draai(zekering, NOMINAAL * 1.5, 1200.0)
    warm = zekering.warmte
    assert warm > 0

    draai(zekering, NOMINAAL * 0.5, 1800.0)
    assert zekering.warmte < warm


def test_afkoelen_gaat_niet_onder_nul():
    zekering = Zekering(nominaal_w=NOMINAAL)
    draai(zekering, 0.0, 10 * UUR)
    assert zekering.warmte == 0.0


def test_een_gesprongen_zekering_blijft_gesprongen():
    zekering = Zekering(nominaal_w=NOMINAAL)
    draai(zekering, NOMINAAL * 3, 2 * UUR)
    assert zekering.gesprongen is True

    # Ook een uur niets doen maakt hem niet weer heel.
    draai(zekering, 0.0, UUR)
    assert zekering.gesprongen is True
    assert zekering.warmte == 1.0


def test_herstellen_zet_hem_terug():
    zekering = Zekering(nominaal_w=NOMINAAL)
    draai(zekering, NOMINAAL * 3, 2 * UUR)
    zekering.herstel()
    assert zekering.gesprongen is False
    assert zekering.warmte == 0.0
    assert zekering.warmte_pct == 0.0


def test_de_warmte_is_af_te_lezen_als_percentage():
    zekering = Zekering(nominaal_w=NOMINAAL)
    assert zekering.warmte_pct == 0.0
    draai(zekering, NOMINAAL * 1.6, UUR / 2)
    assert 0 < zekering.warmte_pct < 100


def test_opslaan_en_terugzetten():
    zekering = Zekering(nominaal_w=NOMINAAL)
    draai(zekering, NOMINAAL * 1.5, 600.0)
    bewaard = zekering.as_dict()

    nieuw = Zekering(nominaal_w=NOMINAAL)
    nieuw.restore(bewaard)
    assert nieuw.warmte == pytest.approx(zekering.warmte)
    assert nieuw.gesprongen == zekering.gesprongen


def test_een_aansluiting_zonder_waarde_gaat_niet_stuk():
    zekering = Zekering(nominaal_w=0.0)
    assert zekering.stap(10000.0, 3600.0) is False
    assert zekering.gesprongen is False
