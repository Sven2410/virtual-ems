// De kaart waarmee je het systeem een doel geeft.
//
// Hier zit het verschil tussen een huis met knoppen en een energiemanagement-
// systeem: je kiest waar de regelaar op stuurt, en je ziet wat dat met de
// aansluiting en met de hoofdzekering doet.

import { stijl, tekst, veilig } from "./basis.js";
import { BEDIEN_CSS, BedieningBasis } from "./bediening.js";
import { icoon } from "./iconen.js";
import { getal, vermogen } from "./stijl.js";
import { MODUSSEN, ids } from "./entiteiten.js";

const REGELAAR_CSS =
  BEDIEN_CSS +
  `
  .modussen {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 10px;
    margin-bottom: 18px;
  }

  .modus {
    display: flex;
    align-items: center;
    gap: 11px;
    min-height: 56px;
    padding: 10px 13px;
    border-radius: var(--dt-radius-sm);
    border: 1px solid var(--dt-border);
    background: var(--dt-surface);
    color: var(--dt-ink);
    font-family: inherit;
    font-size: 13.5px;
    text-align: left;
    cursor: pointer;
  }

  .modus .chip {
    width: 30px;
    height: 30px;
    background: var(--dt-surface-hi);
    color: var(--dt-ink-3);
  }

  .modus .chip svg { width: 16px; height: 16px; }
  .modus .wat { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .modus .uitleg { font-size: 11.5px; color: var(--dt-ink-3); }

  .modus[aria-pressed="true"] {
    border-color: var(--dt-accent-hi);
    background: var(--dt-accent-soft);
  }

  .modus[aria-pressed="true"] .chip {
    background: rgba(25, 143, 217, 0.18);
    color: var(--dt-accent-hi);
  }

  .zekeringblok { display: grid; gap: 10px; }

  .zekeringkop { display: flex; align-items: center; gap: 11px; }
  .zekeringkop .chip { width: 32px; height: 32px; }
  .zekeringkop .naam { font-size: 14px; }

  .zekeringstand {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: var(--dt-radius-pill);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: rgba(12, 163, 12, 0.16);
    color: var(--dt-good);
    white-space: nowrap;
  }

  .zekeringblok[data-stand="warm"] .zekeringstand {
    background: rgba(250, 178, 25, 0.16);
    color: var(--dt-warn);
  }

  .zekeringblok[data-stand="weg"] .zekeringstand {
    background: rgba(208, 59, 59, 0.16);
    color: var(--dt-bad);
  }

  .spoor {
    height: 8px;
    border-radius: var(--dt-radius-pill);
    background: var(--dt-surface-hi);
    overflow: hidden;
  }

  .vulling {
    height: 100%;
    width: 0%;
    border-radius: var(--dt-radius-pill);
    background: var(--dt-good);
    transition: width 240ms ease;
  }

  .zekeringblok[data-stand="warm"] .vulling { background: var(--dt-warn); }
  .zekeringblok[data-stand="weg"] .vulling { background: var(--dt-bad); }

  .zekeringtekst { font-size: 12.5px; color: var(--dt-ink-2); line-height: 1.5; }

  .piekregel {
    display: flex;
    align-items: center;
    gap: 9px;
    font-size: 12.5px;
    color: var(--dt-ink-2);
    margin-top: 14px;
  }

  .piekregel svg { flex: 0 0 auto; }
  .piekregel .waarde { color: var(--dt-ink); margin-left: auto; }
`;

export class RegelaarKaart extends BedieningBasis {
  css() {
    return REGELAAR_CSS;
  }

  bouw() {
    const slug = this._config.installatie;
    if (!slug) {
      return (
        "<div class='kaart'><p class='eyebrow'>Virtueel EMS</p>" +
        "<p class='titel'>Nog niet ingesteld</p>" +
        "<p class='onderschrift'>Geef op welke installatie deze kaart moet sturen.</p></div>"
      );
    }
    const e = ids(slug);
    this._ids = e;
    const docent = this._config.weergave === "docent";

    const knoppen = MODUSSEN.map(
      (modus) =>
        "<button class='modus' type='button' aria-pressed='false' data-modus='" +
        veilig(modus.sleutel) +
        "'><span class='chip'>" +
        icoon(modus.ico, 16) +
        "</span><span class='wat'><span>" +
        veilig(modus.naam) +
        "</span><span class='uitleg'>" +
        veilig(modus.uitleg) +
        "</span></span></button>"
    ).join("");

    const vervangknop = docent
      ? "<div class='schakelaars'><button class='schakelaar' type='button' id='vervang'>" +
        "<span class='chip'>" +
        icoon("terug", 17) +
        "</span><span class='wat'><span>Nieuwe zekering plaatsen</span>" +
        "<span class='watt'>Dit doet de docent</span></span></button></div>"
      : "";

    return (
      "<div class='kaart'>" +
      "<p class='eyebrow'>De regelaar</p>" +
      "<p class='titel'>Waar het systeem op stuurt</p>" +
      "<p class='onderschrift'>In handmatig bepaal jij wat de batterij doet. In de andere " +
      "standen neemt de regelaar dat over, en zie je bovenaan wat hij besloot en waarom.</p>" +
      "<div class='modussen'>" +
      knoppen +
      "</div>" +
      this.schuifHtml(e.number_piekgrens, "Piekgrens, waar piekscheren op stuurt") +
      "<div class='schakelaars'>" +
      this.schakelaarHtml(
        e.switch_aansluitbewaking,
        "Aansluitbewaking",
        "schild",
        "Houdt de installatie binnen wat de aansluiting aankan"
      ) +
      "</div>" +
      "<hr class='hairline'>" +
      "<div class='zekeringblok' id='zekeringblok' data-stand='koud'>" +
      "<div class='zekeringkop'><span class='chip'>" +
      icoon("zekering", 17) +
      "</span><span class='naam'>Hoofdzekering</span>" +
      "<span class='zekeringstand' id='zekeringstand'>in orde</span></div>" +
      "<div class='spoor'><div class='vulling' id='zekeringvulling'></div></div>" +
      "<div class='zekeringtekst' id='zekeringtekst'></div>" +
      vervangknop +
      "</div>" +
      "<div class='piekregel'>" +
      icoon("meter", 14) +
      "<span>Hoogste afname sinds terugzetten</span>" +
      "<span class='waarde' id='piek'></span><span class='eenheid'>kW</span></div>" +
      "</div>"
    );
  }

  ververs() {
    if (!this._ids) return;
    if (!this._gekoppeld) {
      this.koppel();
      this._koppelModussen();
      this._gekoppeld = true;
    }
    this.verversSchuiven();
    this.verversSchakelaars();

    const modusToestand = this.toestand(this._ids.select_regelmodus);
    const modus = modusToestand ? modusToestand.state : "handmatig";
    this.zoekAlle("[data-modus]").forEach((knop) => {
      const actief = knop.getAttribute("data-modus") === modus;
      knop.setAttribute("aria-pressed", actief ? "true" : "false");
    });

    const zekering = this.toestand(this._ids.binary_sensor_hoofdzekering);
    const warmte = getal(this.toestand(this._ids.sensor_zekering_warmte));
    const blok = this.zoek("#zekeringblok");
    const gesprongen = !!zekering && zekering.state === "on";
    const warm = warmte !== null && warmte > 0;

    blok.setAttribute("data-stand", gesprongen ? "weg" : warm ? "warm" : "koud");
    tekst(this.zoek("#zekeringstand"), gesprongen ? "gesprongen" : warm ? "wordt warm" : "in orde");
    stijl(this.zoek("#zekeringvulling"), "width", (warmte === null ? 0 : warmte) + "%");

    const resterend =
      zekering && zekering.attributes ? zekering.attributes.smelt_over_s : undefined;
    let uitleg;
    if (gesprongen) {
      uitleg =
        "De zekering is doorgesmolten en komt niet vanzelf terug. Er staat geen spanning op " +
        "de installatie tot er een nieuwe in zit.";
    } else if (resterend === null || resterend === undefined) {
      uitleg = "Bij deze belasting houdt de zekering het onbeperkt vol.";
    } else {
      uitleg =
        "Bij deze belasting smelt de zekering over ongeveer " +
        this._duur(Number(resterend)) +
        " gesimuleerde tijd.";
    }
    tekst(this.zoek("#zekeringtekst"), uitleg);

    tekst(this.zoek("#piek"), vermogen(getal(this.toestand(this._ids.sensor_hoogste_piek))).waarde);
  }

  _duur(seconden) {
    if (!Number.isFinite(seconden)) return "onbekende tijd";
    if (seconden < 90) return Math.round(seconden) + " seconden";
    if (seconden < 5400) return Math.round(seconden / 60) + " minuten";
    return Math.round(seconden / 360) / 10 + " uur";
  }

  _koppelModussen() {
    this.zoekAlle("[data-modus]").forEach((knop) => {
      knop.addEventListener("click", () => {
        this.roep("select", "select_option", {
          entity_id: this._ids.select_regelmodus,
          option: knop.getAttribute("data-modus"),
        });
        if (typeof knop.blur === "function") knop.blur();
      });
    });

    const vervang = this.zoek("#vervang");
    if (vervang) {
      vervang.addEventListener("click", () => {
        this.roep("virtual_ems", "zekering_herstellen", {});
        if (typeof vervang.blur === "function") vervang.blur();
      });
    }
  }

  _bouwOpnieuw() {
    this._gekoppeld = false;
    super._bouwOpnieuw();
  }

  getCardSize() {
    return 8;
  }
}
