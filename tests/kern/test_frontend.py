"""Bewakers op de frontend, zonder browser en zonder Home Assistant.

Wat hier staat zijn fouten die al eens gemaakt zijn en die een script kan
vangen. De echte metingen aan de kaarten staan in docs/virtual-ems/RAPPORT.md en
zijn in een browser gedaan; deze proeven bewaken de dingen die je in een
schermafdruk niet ziet.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import bewaak_frontend  # noqa: E402

from kernlader import ENTITY_KEYS, PAKKET  # noqa: E402

FRONTEND = REPO / "custom_components" / "virtual_ems" / "frontend"


def test_de_frontend_doorstaat_alle_bewakers():
    klachten = bewaak_frontend.alle_klachten()
    assert not klachten, "\n".join(str(klacht) for klacht in klachten)


def test_er_staat_javascript_in_de_bundel():
    bestanden = {pad.name for pad in bewaak_frontend.js_bestanden()}
    assert "virtual-ems.js" in bestanden
    assert "registratie.js" in bestanden
    assert "strategie.js" in bestanden


def test_de_entiteitenlijst_is_aan_beide_kanten_gelijk():
    """De kaarten leunen hierop; catalog.py is de bron."""
    van_js = bewaak_frontend.frontend_entiteiten()
    for platform, sleutels in ENTITY_KEYS.items():
        assert set(van_js[platform]) == set(sleutels), platform


def test_elementen_worden_op_precies_een_plek_geregistreerd():
    bron = (FRONTEND / "registratie.js").read_text(encoding="utf-8")
    assert bron.count("customElements.define") >= 1
    assert not bewaak_frontend.controleer_registratie()


def test_de_strategie_heet_zoals_home_assistant_hem_zoekt():
    """Home Assistant zoekt een dashboardstrategie op ll-strategy-dashboard-<naam>."""
    bron = (FRONTEND / "registratie.js").read_text(encoding="utf-8")
    assert "ll-strategy-dashboard-virtual-ems" in bron


def test_elke_kaart_meldt_zich_aan_bij_de_kaartkiezer():
    bron = (FRONTEND / "registratie.js").read_text(encoding="utf-8")
    for naam in (
        "virtual-ems-pagina",
        "virtual-ems-kop",
        "virtual-ems-kpis",
        "virtual-ems-balken",
        "virtual-ems-bediening",
        "virtual-ems-meter",
        "virtual-ems-scenarios",
    ):
        assert naam in bron


def test_de_zes_stroomkleuren_staan_er_letterlijk_in():
    """Deze kleuren zijn gezocht op OKLCH-scheiding; ze zijn niet na te maken."""
    bron = (FRONTEND / "stijl.js").read_text(encoding="utf-8")
    for kleur in ("#dc7300", "#235efa", "#129be4", "#bc10c8", "#fd0774", "#039580"):
        assert kleur in bron, kleur
    for status in ("#0ca30c", "#fab219", "#d03b3b"):
        assert status in bron, status
    for identiteit in ("#026fa1", "#198fd9", "#0c0c0a", "#12120f", "#e8e4de"):
        assert identiteit in bron, identiteit


def test_de_vier_basisregels_staan_bovenaan():
    bron = (FRONTEND / "stijl.js").read_text(encoding="utf-8")
    assert "box-sizing: border-box" in bron
    assert "pointer: coarse" in bron
    assert "-webkit-touch-callout" in bron
    assert ":focus-visible" in bron
    assert "prefers-reduced-motion" in bron


def test_er_wordt_geen_webfont_geladen():
    """Geen webfonts: het systeemfont, zodat er niets geladen hoeft te worden."""
    for bestand in bewaak_frontend.js_bestanden():
        bron = bestand.read_text(encoding="utf-8")
        assert "fonts.googleapis" not in bron, bestand.name
        assert "@font-face" not in bron, bestand.name
        assert "@import" not in bron, bestand.name
    assert "system-ui" in (FRONTEND / "stijl.js").read_text(encoding="utf-8")


def test_cijfers_staan_stil():
    """In een EMS verandert bijna elk getal, dus tabular-nums is geen luxe."""
    assert "tabular-nums" in (FRONTEND / "stijl.js").read_text(encoding="utf-8")


def test_er_wordt_niets_van_buiten_gehaald():
    verboden = ("http://", "cdn.", "unpkg", "jsdelivr")
    for bestand in bewaak_frontend.js_bestanden():
        for nummer, regel in enumerate(bestand.read_text(encoding="utf-8").splitlines(), start=1):
            if regel.lstrip().startswith("//"):
                continue
            for woord in verboden:
                assert woord not in regel, f"{bestand.name}:{nummer} haalt iets van buiten"


def test_geen_tekst_wordt_met_hoofdletters_geforceerd_behalve_een_eyebrow():
    """Tekst verschijnt zoals hij is ingetypt; op een klein label mag het."""
    toegestaan = {".eyebrow", ".rol", ".label", ".pil", ".stand"}
    for bestand in bewaak_frontend.js_bestanden():
        regels = bestand.read_text(encoding="utf-8").splitlines()
        for nummer, regel in enumerate(regels, start=1):
            if "text-transform: uppercase" not in regel:
                continue
            blok = "\n".join(regels[max(0, nummer - 20) : nummer])
            assert any(naam in blok for naam in toegestaan), f"{bestand.name}:{nummer}"


# --- De versie van de bundel -------------------------------------------------


def _bundelversie():
    import importlib

    return importlib.import_module(f"{PAKKET}.bundelversie")


def test_de_versie_is_een_korte_hash():
    versie = _bundelversie().bereken_versie()
    assert len(versie) == 12
    assert all(teken in "0123456789abcdef" for teken in versie)


def test_de_versie_verandert_zodra_een_bestand_verandert(tmp_path: Path):
    """Een bundelaar gooit commentaar weg, dus een commentaarwijziging kan
    dezelfde bundel geven. Hier wordt over de bestanden zelf gehasht, dus elke
    wijziging telt, ook in de kaarten en niet alleen in de ingang."""
    module = _bundelversie()
    kopie = tmp_path / "frontend"
    shutil.copytree(FRONTEND, kopie)

    voor = module.bereken_versie(kopie)
    doel = kopie / "kaarten.js"
    doel.write_text(doel.read_text(encoding="utf-8") + "\nconst extra = 1;\n", encoding="utf-8")
    na = module.bereken_versie(kopie)

    assert voor != na
    assert module.bereken_versie(kopie) == na


def test_een_lege_map_geeft_geen_hash_maar_het_woord_onbekend(tmp_path: Path):
    module = _bundelversie()
    assert module.bereken_versie(tmp_path / "bestaat-niet") == "onbekend"


def test_de_url_draagt_de_versie():
    module = _bundelversie()
    url = module.bundel_url("abc123")
    assert url == "/virtual_ems_frontend/virtual-ems.js?v=abc123"


@pytest.mark.parametrize("bestandsnaam", ["virtual-ems.js", "registratie.js", "stijl.js"])
def test_de_bundel_bestaat_echt_op_de_plek_die_de_url_belooft(bestandsnaam: str):
    assert (FRONTEND / bestandsnaam).is_file()
