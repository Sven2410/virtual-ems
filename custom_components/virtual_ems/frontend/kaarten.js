// De kaarten die tonen wat er gebeurt: de kop, de kentallenrij en de balken.

import { Kaart, balkBreedte, stijl, tekst } from "./basis.js";
import { icoon } from "./iconen.js";
import { bekend, energie, getal, kaartCss, procent, vermogen } from "./stijl.js";
import { ids, installatieNaam } from "./entiteiten.js";

const DREMPEL_W = 50; // Onder dit vermogen noemen we het net in balans.

// --- De kop ------------------------------------------------------------------

const KOP_CSS =
  kaartCss +
  `
  .kaart { padding: 22px 24px 20px; overflow: hidden; }

  .accentlijn {
    position: absolute;
    inset: 0 0 auto 0;
    height: 1px;
    background: linear-gradient(90deg, var(--dt-accent-hi), rgba(25, 143, 217, 0));
  }

  .rij {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
  }

  .wie { min-width: 0; }

  .naam {
    font-size: 13px;
    font-weight: 650;
    line-height: 1.2;
    color: var(--dt-ink);
  }

  .rol {
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--dt-ink-3);
    font-weight: 600;
    margin-top: 2px;
  }

  .pil {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 11px;
    border-radius: var(--dt-radius-pill);
    background: var(--dt-accent-soft);
    color: var(--dt-accent-hi);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .pil svg { width: 13px; height: 13px; }

  .kop {
    font-size: 26px;
    line-height: 1.2;
    font-weight: 650;
    letter-spacing: -0.02em;
    margin: 0 0 10px;
  }

  .uitleg {
    font-size: 13.5px;
    line-height: 1.6;
    color: var(--dt-ink-2);
    margin: 0;
    max-width: 62ch;
  }

  .voet {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 13px;
    color: var(--dt-ink-2);
  }

  .voet .ico { color: var(--dt-solar); flex: 0 0 auto; margin-top: 1px; }
  .voet svg { width: 15px; height: 15px; display: block; }

  @media (max-width: 520px) {
    .kaart { padding: 18px 16px; }
    .kop { font-size: 21px; }
    .pil { margin-left: 0; }
    .rij { flex-wrap: wrap; }
  }
`;

export class KopKaart extends Kaart {
  css() {
    return KOP_CSS;
  }

  bouw() {
    const slug = this._config.installatie;
    if (!slug) {
      return (
        "<div class='kaart'><p class='eyebrow'>Virtueel EMS</p>" +
        "<p class='titel'>Nog niet ingesteld</p>" +
        "<p class='onderschrift'>Geef op welke installatie deze kaart moet tonen, " +
        "bijvoorbeeld: installatie: virtueel_ems</p></div>"
      );
    }
    this._ids = ids(slug);
    return (
      "<div class='kaart'>" +
      "<div class='accentlijn'></div>" +
      "<div class='rij'>" +
      "<div class='chip'>" +
      icoon("vonk") +
      "</div>" +
      "<div class='wie'><div class='naam' id='naam'></div>" +
      "<div class='rol'>Virtueel energiesysteem</div></div>" +
      "<div class='pil' id='pil'><span id='pilico'></span><span id='piltekst'></span></div>" +
      "</div>" +
      "<h1 class='kop' id='kop'></h1>" +
      "<p class='uitleg' id='uitleg'></p>" +
      "<hr class='hairline'>" +
      "<div class='voet'><span class='ico'>" +
      icoon("zon", 15) +
      "</span><span id='voet'></span></div>" +
      "</div>"
    );
  }

  ververs() {
    if (!this._ids) return;
    const net = getal(this.toestand(this._ids.sensor_net_vermogen));
    const pv = getal(this.toestand(this._ids.sensor_pv_vermogen));
    const huis = getal(this.toestand(this._ids.sensor_huishoudelijk_verbruik));
    const accu = getal(this.toestand(this._ids.sensor_batterij_vermogen_actueel));
    const auto = getal(this.toestand(this._ids.sensor_laadpaal_vermogen));
    const opbrengst = getal(this.toestand(this._ids.sensor_pv_opbrengst));
    const zelf = getal(this.toestand(this._ids.sensor_zelfbenutting));

    const naam =
      this._config.naam ||
      installatieNaam(this.hass, this._config.installatie, this._ids.sensor_net_vermogen);
    tekst(this.zoek("#naam"), naam);

    let stand = "balans";
    if (net !== null && net > DREMPEL_W) stand = "afname";
    else if (net !== null && net < -DREMPEL_W) stand = "teruglevering";

    const pil = this.zoek("#pil");
    const pilIco = this.zoek("#pilico");
    if (stand === "afname") {
      stijl(pil, "background", "rgba(18, 155, 228, 0.18)");
      stijl(pil, "color", "var(--dt-grid-in)");
      tekst(this.zoek("#piltekst"), "Afname van het net");
      pilIco.innerHTML = icoon("omlaag", 13);
    } else if (stand === "teruglevering") {
      stijl(pil, "background", "rgba(188, 16, 200, 0.18)");
      stijl(pil, "color", "var(--dt-grid-out)");
      tekst(this.zoek("#piltekst"), "Teruglevering");
      pilIco.innerHTML = icoon("omhoog", 13);
    } else {
      stijl(pil, "background", "var(--dt-accent-soft)");
      stijl(pil, "color", "var(--dt-accent-hi)");
      tekst(this.zoek("#piltekst"), "In balans");
      pilIco.innerHTML = icoon("balans", 13);
    }

    let kop = "Nog geen meting binnen";
    if (net !== null) {
      const v = vermogen(Math.abs(net));
      if (stand === "afname") kop = "Je haalt " + v.waarde + " kW van het net";
      else if (stand === "teruglevering") kop = "Je levert " + v.waarde + " kW terug";
      else kop = "Je bent in balans met het net";
    }
    tekst(this.zoek("#kop"), kop);

    const delen = [];
    if (pv !== null && huis !== null) {
      delen.push(
        "De zon levert " +
          vermogen(pv).waarde +
          " kW en het huis vraagt " +
          vermogen(huis).waarde +
          " kW."
      );
    }
    if (auto !== null && auto > DREMPEL_W) {
      delen.push("De auto laadt met " + vermogen(auto).waarde + " kW.");
    }
    if (accu !== null && accu > DREMPEL_W) {
      delen.push("De batterij laadt met " + vermogen(accu).waarde + " kW.");
    } else if (accu !== null && accu < -DREMPEL_W) {
      delen.push("De batterij ontlaadt met " + vermogen(Math.abs(accu)).waarde + " kW.");
    } else if (accu !== null) {
      delen.push("De batterij staat stil.");
    }
    tekst(this.zoek("#uitleg"), delen.join(" "));

    let voet = "Er is vandaag nog niets gemeten.";
    if (opbrengst !== null) {
      voet = "Er is " + energie(opbrengst, 1).waarde + " kWh opgewekt.";
      if (bekend(this.toestand(this._ids.sensor_zelfbenutting)) && zelf !== null) {
        voet += " Daarvan gebruik je " + procent(zelf).waarde + " procent zelf.";
      } else {
        voet += " Over zelfbenutting valt nog niets te zeggen.";
      }
    }
    tekst(this.zoek("#voet"), voet);
  }

  getCardSize() {
    return 5;
  }
}

// --- De kentallenrij ---------------------------------------------------------

const KPI_CSS =
  kaartCss +
  `
  :host { display: block; }

  .rij {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
  }

  .tegel {
    background: var(--dt-surface);
    border: 1px solid var(--dt-border);
    border-radius: var(--dt-radius);
    padding: 14px 16px 13px;
    min-width: 0;
  }

  .top {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }

  .chip { width: 30px; height: 30px; }
  .chip svg { width: 16px; height: 16px; }

  .spoor {
    flex: 1 1 auto;
    height: 22px;
    border-radius: 6px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0));
    position: relative;
    overflow: hidden;
    min-width: 0;
  }

  .vulling {
    position: absolute;
    inset: auto 0 0 0;
    height: 100%;
    width: 0%;
    border-top: 1.5px solid currentColor;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0));
    transition: width 240ms ease;
  }

  .label {
    font-size: 10px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--dt-ink-3);
    font-weight: 600;
    margin-bottom: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .cijfer {
    display: flex;
    align-items: baseline;
    gap: 5px;
    margin-bottom: 9px;
  }

  .cijfer .waarde { font-size: 27px; letter-spacing: -0.02em; line-height: 1.1; }
  .cijfer .eenheid { font-size: 12px; }

  .voet {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 11.5px;
    color: var(--dt-ink-2);
    min-width: 0;
  }

  .voet span:last-child {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  @media (max-width: 380px) {
    .rij { grid-template-columns: 1fr; }
  }
`;

export class KpiKaart extends Kaart {
  css() {
    return KPI_CSS;
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
    this._ids = ids(slug);
    this._items = [
      { sleutel: "zon", label: "Opwek zon", ico: "zon", kleur: "var(--dt-solar)" },
      { sleutel: "huis", label: "Verbruik woning", ico: "huis", kleur: "var(--dt-house)" },
      { sleutel: "net", label: "Van het net", ico: "net", kleur: "var(--dt-grid-in)" },
      { sleutel: "belasting", label: "Belastbaarheid", ico: "meter", kleur: "var(--dt-accent-hi)" },
      { sleutel: "zelf", label: "Zelfbenutting", ico: "blad", kleur: "var(--dt-device-2)" },
      { sleutel: "accu", label: "Thuisbatterij", ico: "batterij", kleur: "var(--dt-device-2)" },
    ];

    const tegels = this._items
      .map(
        (item) =>
          "<div class='tegel' data-sleutel='" +
          item.sleutel +
          "'>" +
          "<div class='top'><div class='chip' data-rol='chip'>" +
          icoon(item.ico, 16) +
          "</div><div class='spoor'><div class='vulling' data-rol='vulling'></div></div></div>" +
          "<div class='label' data-rol='label'></div>" +
          "<div class='cijfer'><span class='waarde' data-rol='waarde'></span>" +
          "<span class='eenheid' data-rol='eenheid'></span></div>" +
          "<div class='voet'><span class='stip' data-rol='stip'></span>" +
          "<span data-rol='voet'></span></div>" +
          "</div>"
      )
      .join("");
    return "<div class='rij'>" + tegels + "</div>";
  }

  _tegel(sleutel) {
    return this.zoek("[data-sleutel='" + sleutel + "']");
  }

  _zet(sleutel, opties) {
    const tegel = this._tegel(sleutel);
    if (!tegel) return;
    const chip = tegel.querySelector("[data-rol='chip']");
    const vulling = tegel.querySelector("[data-rol='vulling']");
    const stip = tegel.querySelector("[data-rol='stip']");
    stijl(chip, "color", opties.kleur);
    stijl(chip, "background", opties.zacht);
    stijl(vulling, "color", opties.kleur);
    stijl(vulling, "width", opties.breedte + "%");
    stijl(stip, "background", opties.kleur);
    tekst(tegel.querySelector("[data-rol='label']"), opties.label);
    tekst(tegel.querySelector("[data-rol='waarde']"), opties.waarde);
    tekst(tegel.querySelector("[data-rol='eenheid']"), opties.eenheid);
    tekst(tegel.querySelector("[data-rol='voet']"), opties.voet);
  }

  ververs() {
    if (!this._ids) return;

    const grens = Number(this.kenmerk(this._ids.sensor_aansluiting_belasting, "grens_w"));
    const piek = Number(this.kenmerk(this._ids.sensor_pv_vermogen, "piek_w"));

    const pv = getal(this.toestand(this._ids.sensor_pv_vermogen));
    const pvOpmaak = vermogen(pv);
    this._zet("zon", {
      kleur: "var(--dt-solar)",
      zacht: "rgba(220, 115, 0, 0.16)",
      breedte: balkBreedte(pv, piek),
      label: "Opwek zon",
      waarde: pvOpmaak.waarde,
      eenheid: pvOpmaak.eenheid,
      voet: pv !== null && pv > DREMPEL_W ? "Panelen leveren nu" : "Geen zon op het dak",
    });

    const huis = getal(this.toestand(this._ids.sensor_huishoudelijk_verbruik));
    const auto = getal(this.toestand(this._ids.sensor_laadpaal_vermogen));
    const huisOpmaak = vermogen(huis);
    this._zet("huis", {
      kleur: "var(--dt-house)",
      zacht: "rgba(35, 94, 250, 0.16)",
      breedte: balkBreedte(huis, grens),
      label: "Verbruik woning",
      waarde: huisOpmaak.waarde,
      eenheid: huisOpmaak.eenheid,
      voet: auto !== null && auto > DREMPEL_W ? "Zonder de auto erbij" : "Huis en apparaten",
    });

    const net = getal(this.toestand(this._ids.sensor_net_vermogen));
    const teruglevering = net !== null && net < -DREMPEL_W;
    const netOpmaak = vermogen(net === null ? null : Math.abs(net));
    this._zet("net", {
      kleur: teruglevering ? "var(--dt-grid-out)" : "var(--dt-grid-in)",
      zacht: teruglevering ? "rgba(188, 16, 200, 0.16)" : "rgba(18, 155, 228, 0.16)",
      breedte: balkBreedte(net, grens),
      label: teruglevering ? "Naar het net" : "Van het net",
      waarde: netOpmaak.waarde,
      eenheid: netOpmaak.eenheid,
      voet: teruglevering
        ? "Je levert terug"
        : net !== null && net > DREMPEL_W
          ? "Je koopt in"
          : "Bijna in balans",
    });

    const belasting = getal(this.toestand(this._ids.sensor_aansluiting_belasting));
    let kleur = "var(--dt-good)";
    let zacht = "rgba(12, 163, 12, 0.16)";
    let woord = "Ruim binnen de grens";
    if (belasting !== null && belasting >= 100) {
      kleur = "var(--dt-bad)";
      zacht = "rgba(208, 59, 59, 0.16)";
      woord = "Boven de grens";
    } else if (belasting !== null && belasting >= 80) {
      kleur = "var(--dt-warn)";
      zacht = "rgba(250, 178, 25, 0.16)";
      woord = "Bijna aan de grens";
    }
    const belastingOpmaak = procent(belasting);
    this._zet("belasting", {
      kleur,
      zacht,
      breedte: balkBreedte(belasting, 100),
      label: "Belastbaarheid",
      waarde: belastingOpmaak.waarde,
      eenheid: belastingOpmaak.eenheid,
      voet: woord,
    });

    const zelf = getal(this.toestand(this._ids.sensor_zelfbenutting));
    const zelfOpmaak = procent(zelf);
    this._zet("zelf", {
      kleur: "var(--dt-device-2)",
      zacht: "rgba(3, 149, 128, 0.16)",
      breedte: balkBreedte(zelf, 100),
      label: "Zelfbenutting",
      waarde: zelfOpmaak.waarde,
      eenheid: zelfOpmaak.eenheid,
      voet: zelf === null ? "Nog niets opgewekt" : "Zelf gebruikt",
    });

    const soc = getal(this.toestand(this._ids.sensor_batterij_soc));
    const accu = getal(this.toestand(this._ids.sensor_batterij_vermogen_actueel));
    const socOpmaak = procent(soc);
    let accuVoet = "Batterij staat stil";
    if (accu !== null && accu > DREMPEL_W) accuVoet = "Laadt met " + vermogen(accu).waarde + " kW";
    else if (accu !== null && accu < -DREMPEL_W)
      accuVoet = "Ontlaadt met " + vermogen(Math.abs(accu)).waarde + " kW";
    this._zet("accu", {
      kleur: "var(--dt-device-2)",
      zacht: "rgba(3, 149, 128, 0.16)",
      breedte: balkBreedte(soc, 100),
      label: "Thuisbatterij",
      waarde: socOpmaak.waarde,
      eenheid: socOpmaak.eenheid,
      voet: accuVoet,
    });
  }

  getCardSize() {
    return 4;
  }
}

// --- De balken ---------------------------------------------------------------

const BALK_CSS =
  kaartCss +
  `
  .regels { display: grid; gap: 11px; }

  .regel {
    display: grid;
    grid-template-columns: 74px 1fr auto auto;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .naam {
    font-size: 12.5px;
    color: var(--dt-ink-2);
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .naam svg { width: 14px; height: 14px; flex: 0 0 auto; }
  .naam span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .spoor {
    height: 8px;
    border-radius: var(--dt-radius-pill);
    background: var(--dt-surface-hi);
    overflow: hidden;
    min-width: 0;
  }

  .vulling {
    height: 100%;
    width: 0%;
    border-radius: var(--dt-radius-pill);
    background: currentColor;
    transition: width 240ms ease;
  }

  .kw { font-size: 12.5px; min-width: 62px; text-align: right; }
  .deel { font-size: 12.5px; min-width: 44px; text-align: right; color: var(--dt-ink-2); }

  .grensregel {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 14px;
    font-size: 12px;
    color: var(--dt-ink-3);
  }

  @media (max-width: 520px) {
    .regel { grid-template-columns: 58px 1fr auto; }
    .deel { display: none; }
  }
`;

export class BalkKaart extends Kaart {
  css() {
    return BALK_CSS;
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
    this._ids = ids(slug);
    this._regels = [
      { sleutel: "zon", naam: "Zon", ico: "zon", kleur: "var(--dt-solar)" },
      { sleutel: "huis", naam: "Woning", ico: "huis", kleur: "var(--dt-house)" },
      { sleutel: "auto", naam: "Laadpaal", ico: "laadpaal", kleur: "var(--dt-device-1)" },
      { sleutel: "accu", naam: "Batterij", ico: "batterij", kleur: "var(--dt-device-2)" },
      { sleutel: "net", naam: "Net", ico: "net", kleur: "var(--dt-grid-in)" },
    ];

    const regels = this._regels
      .map(
        (regel) =>
          "<div class='regel' data-sleutel='" +
          regel.sleutel +
          "'><div class='naam'>" +
          icoon(regel.ico, 14) +
          "<span>" +
          regel.naam +
          "</span></div>" +
          "<div class='spoor' data-rol='spoor'><div class='vulling' data-rol='vulling'></div></div>" +
          "<div class='kw'><span class='waarde' data-rol='kw'></span> " +
          "<span class='eenheid'>kW</span></div>" +
          "<div class='deel' data-rol='deel'></div></div>"
      )
      .join("");

    return (
      "<div class='kaart'><p class='eyebrow'>Vermogen</p>" +
      "<p class='titel'>Waar het vermogen heen gaat</p>" +
      "<p class='onderschrift' id='onderschrift'></p>" +
      "<div class='regels'>" +
      regels +
      "</div>" +
      "<div class='grensregel'>" +
      icoon("meter", 14) +
      "<span id='grensregel'></span></div></div>"
    );
  }

  ververs() {
    if (!this._ids) return;
    const grensRuw = Number(this.kenmerk(this._ids.sensor_aansluiting_belasting, "grens_w"));
    const grens = Number.isFinite(grensRuw) && grensRuw > 0 ? grensRuw : null;
    const fasen = this.kenmerk(this._ids.sensor_aansluiting_belasting, "fasen");
    const ampere = this.kenmerk(this._ids.sensor_aansluiting_belasting, "ampere_per_fase");

    tekst(
      this.zoek("#onderschrift"),
      "Elke balk staat tegen wat de aansluiting aankan, dus je ziet meteen hoeveel ruimte er nog is."
    );

    if (grens && fasen !== undefined && ampere !== undefined) {
      tekst(
        this.zoek("#grensregel"),
        "De aansluiting is " +
          fasen +
          " maal " +
          ampere +
          " A, samen " +
          vermogen(grens).waarde +
          " kW. De simulatie rekent met het totaal, niet per fase."
      );
    } else {
      tekst(this.zoek("#grensregel"), "De aansluitwaarde is nog niet bekend.");
    }

    const waarden = {
      zon: getal(this.toestand(this._ids.sensor_pv_vermogen)),
      huis: getal(this.toestand(this._ids.sensor_huishoudelijk_verbruik)),
      auto: getal(this.toestand(this._ids.sensor_laadpaal_vermogen)),
      accu: getal(this.toestand(this._ids.sensor_batterij_vermogen_actueel)),
      net: getal(this.toestand(this._ids.sensor_net_vermogen)),
    };

    this._regels.forEach((regel) => {
      const knoop = this.zoek("[data-sleutel='" + regel.sleutel + "']");
      if (!knoop) return;
      const waarde = waarden[regel.sleutel];
      let kleur = regel.kleur;
      if (regel.sleutel === "net" && waarde !== null && waarde < -DREMPEL_W) {
        kleur = "var(--dt-grid-out)";
      }
      const vulling = knoop.querySelector("[data-rol='vulling']");
      stijl(vulling, "color", kleur);
      stijl(vulling, "width", balkBreedte(waarde, grens) + "%");
      tekst(
        knoop.querySelector("[data-rol='kw']"),
        waarde === null ? "onbekend" : vermogen(Math.abs(waarde)).waarde
      );
      tekst(
        knoop.querySelector("[data-rol='deel']"),
        waarde === null || !grens ? "" : procent(balkBreedte(waarde, grens)).waarde + " %"
      );
    });
  }
}
