// De kaarten waar een cursist of docent iets mee doet: schuiven, schakelaars,
// de meterstanden en de scenarioknoppen.

import { Kaart, stijl, tekst, veilig } from "./basis.js";
import { icoon } from "./iconen.js";
import { energie, getal, kaartCss, procent, vermogen } from "./stijl.js";
import { APPARATEN, ids } from "./entiteiten.js";

// Een schuif mag tijdens het slepen niet elke pixel naar de server sturen.
const SMOORTIJD_MS = 250;

const BEDIEN_CSS =
  kaartCss +
  `
  .groep + .groep { margin-top: 22px; }

  .groepkop {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }

  .groepkop .chip { width: 30px; height: 30px; }
  .groepkop .chip svg { width: 16px; height: 16px; }
  .groepkop .titel { margin: 0; font-size: 15px; }

  .schuif { padding: 4px 0 2px; }

  .schuifkop {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 6px;
  }

  .schuifkop .naam { font-size: 13px; color: var(--dt-ink-2); }
  .schuifkop .cijfer { margin-left: auto; font-size: 15px; }
  .schuifkop .eenheid { font-size: 11px; margin-left: 3px; }

  input[type="range"] {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 44px;
    margin: 0;
    background: transparent;
    cursor: pointer;
    display: block;
  }

  input[type="range"]::-webkit-slider-runnable-track {
    height: 8px;
    border-radius: var(--dt-radius-pill);
    background: var(--dt-surface-hi);
    border: 1px solid var(--dt-border);
  }

  input[type="range"]::-moz-range-track {
    height: 8px;
    border-radius: var(--dt-radius-pill);
    background: var(--dt-surface-hi);
    border: 1px solid var(--dt-border);
  }

  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 26px;
    height: 26px;
    margin-top: -10px;
    border-radius: 50%;
    background: var(--dt-accent-hi);
    border: 3px solid var(--dt-bg-raise);
    box-shadow: 0 0 0 1px var(--dt-border-hi);
  }

  input[type="range"]::-moz-range-thumb {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--dt-accent-hi);
    border: 3px solid var(--dt-bg-raise);
  }

  .grenzen {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--dt-ink-3);
    margin-top: -4px;
  }

  .schakelaars { display: grid; gap: 10px; }

  .schakelaar {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 56px;
    padding: 10px 14px;
    border-radius: var(--dt-radius-sm);
    border: 1px solid var(--dt-border);
    background: var(--dt-surface);
    color: var(--dt-ink);
    font-family: inherit;
    font-size: 14px;
    text-align: left;
    cursor: pointer;
  }

  .schakelaar:hover { border-color: var(--dt-border-hi); }

  /* Op een aanraakscherm blijft hover plakken, dus alleen waar echt gehoverd
     kan worden. */
  @media (hover: none) {
    .schakelaar:hover { border-color: var(--dt-border); }
  }

  .schakelaar .chip { width: 32px; height: 32px; }
  .schakelaar .chip svg { width: 17px; height: 17px; }
  .schakelaar .wat { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .schakelaar .watt { font-size: 11.5px; color: var(--dt-ink-3); }

  .stand {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 6px 12px;
    border-radius: var(--dt-radius-pill);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: var(--dt-surface-hi);
    color: var(--dt-ink-3);
    white-space: nowrap;
  }

  .schakelaar[aria-checked="true"] .stand {
    background: var(--dt-accent-soft);
    color: var(--dt-accent-hi);
  }
`;

/** Basis voor kaarten die schuiven en schakelaars tekenen. */
class BedieningBasis extends Kaart {
  css() {
    return BEDIEN_CSS;
  }

  constructor() {
    super();
    this._sleept = {};
    this._laatsteRoep = {};
    this._laatsteWaarde = {};
    this._openstaand = {};
  }

  schuifHtml(entityId, naam, ico) {
    return (
      "<div class='schuif' data-schuif='" +
      veilig(entityId) +
      "'>" +
      "<div class='schuifkop'>" +
      (ico ? "<span class='ico'>" + icoon(ico, 14) + "</span>" : "") +
      "<span class='naam'>" +
      veilig(naam) +
      "</span>" +
      "<span class='cijfer'><span class='waarde' data-rol='waarde'></span>" +
      "<span class='eenheid' data-rol='eenheid'></span></span></div>" +
      "<input type='range' data-rol='range' aria-label='" +
      veilig(naam) +
      "'>" +
      "<div class='grenzen'><span data-rol='min'></span><span data-rol='max'></span></div>" +
      "</div>"
    );
  }

  schakelaarHtml(entityId, naam, ico, bijschrift) {
    return (
      "<button class='schakelaar' type='button' role='switch' aria-checked='false' " +
      "data-schakelaar='" +
      veilig(entityId) +
      "'>" +
      "<span class='chip'>" +
      icoon(ico, 17) +
      "</span>" +
      "<span class='wat'><span>" +
      veilig(naam) +
      "</span><span class='watt' data-rol='bij'>" +
      veilig(bijschrift || "") +
      "</span></span>" +
      "<span class='stand' data-rol='stand'>uit</span>" +
      "</button>"
    );
  }

  koppel() {
    this.zoekAlle("[data-schuif]").forEach((blok) => {
      const entityId = blok.getAttribute("data-schuif");
      const range = blok.querySelector("[data-rol='range']");
      range.addEventListener("pointerdown", () => {
        this._sleept[entityId] = true;
      });
      const klaar = () => {
        this._sleept[entityId] = false;
        const openstaand = this._openstaand[entityId];
        const waarde = openstaand === undefined ? Number(range.value) : openstaand;
        this._stuur(entityId, waarde, true);
      };
      range.addEventListener("pointerup", klaar);
      range.addEventListener("pointercancel", klaar);
      range.addEventListener("input", () => {
        this._toonSchuif(blok, entityId, Number(range.value));
        this._stuur(entityId, Number(range.value), false);
      });
      range.addEventListener("change", klaar);
      // Het toetsenbord geeft geen pointerup, dus daar hangt change aan vast.
      range.addEventListener("keyup", klaar);
    });

    this.zoekAlle("[data-schakelaar]").forEach((knop) => {
      knop.addEventListener("click", () => {
        const entityId = knop.getAttribute("data-schakelaar");
        this.roep("switch", "toggle", { entity_id: entityId });
        // De focus komt na een tik terug op de knop, en dan matcht
        // :focus-visible ook op een aanraakscherm. Dat leest als een knop die
        // aan blijft staan, dus die halen we hier weg.
        if (typeof knop.blur === "function") knop.blur();
      });
    });
  }

  _stuur(entityId, waarde, meteen) {
    // Dezelfde waarde nog eens sturen heeft geen zin. Zonder deze controle
    // levert één toetsaanslag drie aanroepen op: input, keyup en change vuren
    // alle drie, en op een aanraakscherm komt pointerup daar nog bij. Gemeten
    // in de browser: tien aanroepen voor vier waardes.
    if (this._laatsteWaarde[entityId] === waarde) return;

    const nu = Date.now();
    const vorige = this._laatsteRoep[entityId] || 0;
    if (!meteen && nu - vorige < SMOORTIJD_MS) {
      // Tijdens het slepen wordt niet elke pixel verstuurd, maar de laatste
      // stand mag niet verdwijnen: die gaat alsnog mee zodra de vinger loslaat.
      this._openstaand[entityId] = waarde;
      return;
    }

    this._laatsteRoep[entityId] = nu;
    this._laatsteWaarde[entityId] = waarde;
    delete this._openstaand[entityId];
    this.roep("number", "set_value", { entity_id: entityId, value: waarde });
  }

  _toonSchuif(blok, entityId, waarde) {
    const eenheid = blok.getAttribute("data-eenheid") || "";
    const opmaak =
      eenheid === "W" ? vermogen(waarde) : { waarde: this._rond(waarde), eenheid: eenheid };
    tekst(blok.querySelector("[data-rol='waarde']"), opmaak.waarde);
    tekst(blok.querySelector("[data-rol='eenheid']"), eenheid === "W" ? "kW" : eenheid);
  }

  _rond(waarde) {
    return procent(waarde).waarde;
  }

  verversSchuiven() {
    this.zoekAlle("[data-schuif]").forEach((blok) => {
      const entityId = blok.getAttribute("data-schuif");
      const toestand = this.toestand(entityId);
      const range = blok.querySelector("[data-rol='range']");
      if (!toestand) {
        blok.setAttribute("hidden", "");
        // Een klasse die display zet wint van het attribuut hidden, dus die
        // regel staat er expliciet bij in de stijl.
        return;
      }
      blok.removeAttribute("hidden");

      const min = Number(toestand.attributes.min);
      const max = Number(toestand.attributes.max);
      const stap = Number(toestand.attributes.step) || 1;
      const eenheid = toestand.attributes.unit_of_measurement || "";
      blok.setAttribute("data-eenheid", eenheid);
      if (Number.isFinite(min)) range.min = String(min);
      if (Number.isFinite(max)) range.max = String(max);
      range.step = String(stap);

      const waarde = getal(toestand);
      if (!this._sleept[entityId] && waarde !== null && Number(range.value) !== waarde) {
        range.value = String(waarde);
      }
      this._toonSchuif(blok, entityId, this._sleept[entityId] ? Number(range.value) : waarde);

      const grensOpmaak = (getalWaarde) =>
        eenheid === "W" ? vermogen(getalWaarde).waarde + " kW" : this._rond(getalWaarde) + " " + eenheid;
      tekst(blok.querySelector("[data-rol='min']"), Number.isFinite(min) ? grensOpmaak(min) : "");
      tekst(blok.querySelector("[data-rol='max']"), Number.isFinite(max) ? grensOpmaak(max) : "");
    });
  }

  verversSchakelaars() {
    this.zoekAlle("[data-schakelaar]").forEach((knop) => {
      const toestand = this.toestand(knop.getAttribute("data-schakelaar"));
      const aan = !!toestand && toestand.state === "on";
      knop.setAttribute("aria-checked", aan ? "true" : "false");
      tekst(knop.querySelector("[data-rol='stand']"), aan ? "aan" : "uit");
      const chip = knop.querySelector(".chip");
      stijl(chip, "color", aan ? "var(--dt-accent-hi)" : "var(--dt-ink-3)");
      stijl(chip, "background", aan ? "var(--dt-accent-soft)" : "var(--dt-surface-hi)");
    });
  }
}

// --- Bediening voor de cursist -----------------------------------------------

export class BedieningKaart extends BedieningBasis {
  bouw() {
    const slug = this._config.installatie;
    if (!slug) {
      return (
        "<div class='kaart'><p class='eyebrow'>Virtueel EMS</p>" +
        "<p class='titel'>Nog niet ingesteld</p>" +
        "<p class='onderschrift'>Geef op welke installatie deze kaart moet bedienen.</p></div>"
      );
    }
    const e = ids(slug);
    this._ids = e;
    const uitgebreid = this._config.uitgebreid === true;

    const apparaten = APPARATEN.map((naam) =>
      this.schakelaarHtml(
        e["switch_" + naam],
        naam.charAt(0).toUpperCase() + naam.slice(1),
        naam,
        ""
      )
    ).join("");

    return (
      "<div class='kaart'>" +
      "<p class='eyebrow'>Sturing</p>" +
      "<p class='titel'>Wat jij kunt verzetten</p>" +
      "<p class='onderschrift'>Elke wijziging is meteen terug te zien in de rij hierboven.</p>" +
      "<div class='groep'><div class='groepkop'><div class='chip'>" +
      icoon("wolk", 16) +
      "</div><p class='titel'>De zon</p></div>" +
      this.schuifHtml(e.number_pv_bewolking, "Bewolking") +
      "</div>" +
      "<div class='groep'><div class='groepkop'><div class='chip'>" +
      icoon("batterij", 16) +
      "</div><p class='titel'>De thuisbatterij</p></div>" +
      this.schuifHtml(e.number_batterij_vermogen, "Doelvermogen, min is ontladen") +
      this.schuifHtml(e.number_batterij_min_soc, "Niet verder ontladen dan") +
      (uitgebreid ? this.schuifHtml(e.number_batterij_max_soc, "Niet verder laden dan") : "") +
      "</div>" +
      "<div class='groep'><div class='groepkop'><div class='chip'>" +
      icoon("laadpaal", 16) +
      "</div><p class='titel'>De laadpaal</p></div>" +
      "<div class='schakelaars'>" +
      this.schakelaarHtml(e.switch_laadpaal_actief, "Auto aan de lader", "laadpaal", "") +
      "</div>" +
      this.schuifHtml(e.number_laadpaal_vermogen, "Laadvermogen") +
      "</div>" +
      "<div class='groep'><div class='groepkop'><div class='chip'>" +
      icoon("vonk", 16) +
      "</div><p class='titel'>Apparaten in huis</p></div>" +
      "<div class='schakelaars'>" +
      apparaten +
      "</div></div>" +
      (uitgebreid
        ? "<div class='groep'><div class='groepkop'><div class='chip'>" +
          icoon("klok", 16) +
          "</div><p class='titel'>De simulatieklok</p></div>" +
          this.schuifHtml(e.number_tijdversnelling, "Tijdversnelling") +
          "</div>"
        : "") +
      "</div>"
    );
  }

  ververs() {
    if (!this._ids) return;
    if (!this._gekoppeld) {
      this.koppel();
      this._gekoppeld = true;
    }
    this.verversSchuiven();
    this.verversSchakelaars();

    APPARATEN.forEach((naam) => {
      const knop = this.zoek("[data-schakelaar='" + this._ids["switch_" + naam] + "']");
      if (!knop) return;
      const watt = this.kenmerk(this._ids["switch_" + naam], "vermogen_w");
      tekst(
        knop.querySelector("[data-rol='bij']"),
        watt === undefined ? "" : vermogen(Number(watt)).waarde + " kW zolang hij aan staat"
      );
    });
  }

  _bouwOpnieuw() {
    this._gekoppeld = false;
    super._bouwOpnieuw();
  }

  getCardSize() {
    return 12;
  }
}

// --- De meterstanden ---------------------------------------------------------

const METER_CSS =
  kaartCss +
  `
  .vakken {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 10px;
  }

  .vak {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    border: 1px solid var(--dt-border);
    border-radius: var(--dt-radius-sm);
    background: var(--dt-surface);
    min-width: 0;
  }

  .vak .label {
    font-size: 12.5px;
    color: var(--dt-ink-2);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .vak .cijfer { margin-left: auto; font-size: 14px; white-space: nowrap; }
  .vak .eenheid { font-size: 11px; margin-left: 4px; }
`;

export class MeterKaart extends Kaart {
  css() {
    return METER_CSS;
  }

  bouw() {
    const slug = this._config.installatie;
    if (!slug) {
      return (
        "<div class='kaart'><p class='eyebrow'>Virtueel EMS</p>" +
        "<p class='titel'>Nog niet ingesteld</p>" +
        "<p class='onderschrift'>Geef op welke installatie deze kaart moet tonen.</p></div>"
      );
    }
    const e = ids(slug);
    this._vakken = [
      { id: e.sensor_pv_opbrengst, label: "Opgewekt" },
      { id: e.sensor_verbruik_totaal, label: "Verbruikt in huis" },
      { id: e.sensor_laadpaal_verbruik, label: "In de auto" },
      { id: e.sensor_batterij_geladen, label: "Batterij in" },
      { id: e.sensor_batterij_ontladen, label: "Batterij uit" },
      { id: e.sensor_net_afname, label: "Van het net" },
      { id: e.sensor_net_teruglevering, label: "Naar het net" },
    ];

    const vakken = this._vakken
      .map(
        (vak) =>
          "<div class='vak' data-id='" +
          veilig(vak.id) +
          "'><span class='label'>" +
          veilig(vak.label) +
          "</span><span class='cijfer'><span class='waarde' data-rol='waarde'></span>" +
          "<span class='eenheid'>kWh</span></span></div>"
      )
      .join("");

    return (
      "<div class='kaart'><p class='eyebrow'>Standen</p>" +
      "<p class='titel'>Je meter</p>" +
      "<p class='onderschrift'>De tellers zoals ze op je meter zouden staan.</p>" +
      "<div class='vakken'>" +
      vakken +
      "</div></div>"
    );
  }

  ververs() {
    if (!this._vakken) return;
    this._vakken.forEach((vak) => {
      const knoop = this.zoek("[data-id='" + vak.id + "']");
      if (!knoop) return;
      tekst(knoop.querySelector("[data-rol='waarde']"), energie(getal(this.toestand(vak.id))).waarde);
    });
  }
}

// --- De scenarioknoppen voor de docent ---------------------------------------

const SCENARIO_CSS =
  kaartCss +
  `
  .knoppen {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 10px;
  }

  .knop {
    display: flex;
    align-items: center;
    gap: 11px;
    min-height: 56px;
    padding: 10px 14px;
    border-radius: var(--dt-radius-sm);
    border: 1px solid var(--dt-border);
    background: var(--dt-surface);
    color: var(--dt-ink);
    font-family: inherit;
    font-size: 13.5px;
    text-align: left;
    cursor: pointer;
  }

  .knop:hover { border-color: var(--dt-border-hi); }
  @media (hover: none) { .knop:hover { border-color: var(--dt-border); } }

  .knop .chip { width: 30px; height: 30px; }
  .knop .chip svg { width: 16px; height: 16px; }

  .knop[data-soort="terug"] .chip { color: var(--dt-warn); background: rgba(250, 178, 25, 0.16); }
`;

const SCENARIOS = [
  { sleutel: "zonnige_dag", naam: "Zonnige dag", ico: "zon" },
  { sleutel: "bewolkte_dag", naam: "Bewolkte dag", ico: "wolk" },
  { sleutel: "piekbelasting_avond", naam: "Piek in de avond", ico: "vonk" },
  { sleutel: "lege_batterij", naam: "Lege batterij", ico: "batterij" },
];

export class ScenarioKaart extends Kaart {
  css() {
    return SCENARIO_CSS;
  }

  bouw() {
    const knoppen = SCENARIOS.map(
      (scenario) =>
        "<button class='knop' type='button' data-scenario='" +
        scenario.sleutel +
        "'><span class='chip'>" +
        icoon(scenario.ico, 16) +
        "</span><span>" +
        veilig(scenario.naam) +
        "</span></button>"
    ).join("");

    return (
      "<div class='kaart'><p class='eyebrow'>Lessituatie</p>" +
      "<p class='titel'>Zet in één druk een situatie klaar</p>" +
      "<p class='onderschrift'>Bewolking, batterijstand, laadpaal, apparaten en het tijdstip van " +
      "de gesimuleerde dag gaan in één keer goed voor de hele klas. De tellers blijven staan.</p>" +
      "<div class='knoppen'>" +
      knoppen +
      "</div>" +
      "<hr class='hairline'>" +
      "<div class='knoppen'>" +
      "<button class='knop' type='button' data-soort='terug' data-reset='alles'>" +
      "<span class='chip'>" +
      icoon("terug", 16) +
      "</span><span>Alles terugzetten</span></button>" +
      "<button class='knop' type='button' data-soort='terug' data-reset='tellers'>" +
      "<span class='chip'>" +
      icoon("meter", 16) +
      "</span><span>Alleen de tellers</span></button>" +
      "</div></div>"
    );
  }

  ververs() {
    if (this._gekoppeld) return;
    this._gekoppeld = true;
    this.zoekAlle("[data-scenario]").forEach((knop) => {
      knop.addEventListener("click", () => {
        this.roep("virtual_ems", "set_scenario", { scenario: knop.getAttribute("data-scenario") });
        if (typeof knop.blur === "function") knop.blur();
      });
    });
    this.zoekAlle("[data-reset]").forEach((knop) => {
      knop.addEventListener("click", () => {
        this.roep("virtual_ems", "reset", {
          alleen_tellers: knop.getAttribute("data-reset") === "tellers",
        });
        if (typeof knop.blur === "function") knop.blur();
      });
    });
  }

  _bouwOpnieuw() {
    this._gekoppeld = false;
    super._bouwOpnieuw();
  }
}
