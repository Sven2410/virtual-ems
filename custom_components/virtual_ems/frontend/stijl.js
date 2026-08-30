// De huisstijl van DomotiTech, letterlijk overgenomen uit theme.js.
//
// Deze waarden zijn niet opnieuw te bedenken en niet "ongeveer" na te maken.
// De zes stroomkleuren zijn gezocht op OKLCH-scheiding en kleurenblindheids-
// afstand tegen #12120f, in beide netstanden. Vervang ze niet zonder die
// zoektocht opnieuw te draaien.
//
// Let op: in dit bestand staat geen enkel accent grave in een commentaar. Alle
// stijlen staan in een template-literal, en zo een teken sluit die string af.
// Dat is een keer een lege bundel geworden zonder dat er een bouwfout kwam.
// scripts/bewaak_frontend.py controleert het, en die bewaker hangt aan de
// proefronde en aan CI.

export const tokens = `
  --dt-bg: #0c0c0a;
  --dt-bg-raise: #12120f;
  --dt-surface: rgba(255, 255, 255, 0.038);
  --dt-surface-hi: rgba(255, 255, 255, 0.070);
  --dt-border: rgba(232, 228, 222, 0.10);
  --dt-border-hi: rgba(232, 228, 222, 0.20);

  --dt-ink: #e8e4de;
  --dt-ink-2: rgba(232, 228, 222, 0.62);
  --dt-ink-3: rgba(232, 228, 222, 0.38);

  --dt-accent: #026fa1;
  --dt-accent-hi: #198fd9;
  --dt-accent-soft: rgba(2, 111, 161, 0.18);
  --dt-accent-glow: rgba(25, 143, 217, 0.30);

  --dt-solar: #dc7300;
  --dt-house: #235efa;
  --dt-grid-in: #129be4;
  --dt-grid-out: #bc10c8;
  --dt-device-1: #fd0774;
  --dt-device-2: #039580;

  --dt-good: #0ca30c;
  --dt-warn: #fab219;
  --dt-bad: #d03b3b;

  --dt-radius: 20px;
  --dt-radius-sm: 12px;
  --dt-radius-pill: 999px;

  --dt-font: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
`;

// Deze vier regels horen in elk project bovenaan.
export const baseCss = `
  *, *::before, *::after { box-sizing: border-box; }

  /* iOS zoomt in op een invoerveld met tekst kleiner dan 16px, en zoomt daarna
     niet terug. Dat is hoe een dashboard op een telefoon zijwaarts scrollbaar
     wordt. Beide regels zijn nodig: een iPad met trackpad meldt fine. */
  @media (pointer: coarse) { input, select, textarea { font-size: 16px; } }
  @supports (-webkit-touch-callout: none) { input, select, textarea { font-size: 16px; } }

  :focus-visible { outline: 2px solid var(--dt-accent-hi); outline-offset: 2px; border-radius: 6px; }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.001ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.001ms !important;
    }
  }
`;

// Wat elke kaart deelt. Een kaart ligt laag, dus hij krijgt de haarlijn en geen
// slagschaduw: die zou onder een balk van 56px net zo hoog staan als de balk
// zelf en drie eronder geven donkere banden.
export const kaartCss = `
  :host {
    ${tokens}
    display: block;
    font-family: var(--dt-font);
    color: var(--dt-ink);
    font-variant-numeric: tabular-nums;
    -webkit-font-smoothing: antialiased;
  }

  ${baseCss}

  .kaart {
    background: var(--dt-surface);
    border: 1px solid var(--dt-border);
    border-radius: var(--dt-radius);
    padding: 20px;
    position: relative;
  }

  .eyebrow {
    font-size: 11px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--dt-ink-3);
    font-weight: 600;
    margin: 0 0 6px;
  }

  .titel {
    font-size: 19px;
    font-weight: 650;
    letter-spacing: -0.01em;
    margin: 0 0 4px;
    color: var(--dt-ink);
  }

  .onderschrift {
    font-size: 13px;
    line-height: 1.5;
    color: var(--dt-ink-2);
    margin: 0 0 16px;
  }

  .chip {
    width: 34px;
    height: 34px;
    border-radius: var(--dt-radius-sm);
    display: grid;
    place-items: center;
    background: var(--dt-accent-soft);
    color: var(--dt-accent-hi);
    flex: 0 0 auto;
  }

  .chip svg { width: 18px; height: 18px; display: block; }

  .hairline {
    border: 0;
    border-top: 1px solid var(--dt-border);
    margin: 16px 0;
  }

  .waarde {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    color: var(--dt-ink);
  }

  .eenheid {
    color: var(--dt-ink-3);
    font-weight: 500;
  }

  /* Een klasse die display zet wint van het attribuut hidden, dus elke plek
     die iets verbergt heeft deze regel nodig. Dat kostte een keer een ronde:
     el.hidden stond op true terwijl het blok gewoon in beeld stond. */
  [hidden] { display: none !important; }

  .stip {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex: 0 0 auto;
    display: inline-block;
  }
`;

const NUMMER = new Intl.NumberFormat("nl-NL", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const NUMMER_1 = new Intl.NumberFormat("nl-NL", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const NUMMER_0 = new Intl.NumberFormat("nl-NL", {
  maximumFractionDigits: 0,
});
const NUMMER_3 = new Intl.NumberFormat("nl-NL", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

export const ONBEKEND = "onbekend";

/** Is dit een waarde waar we iets mee kunnen, of weet het systeem het niet? */
export function bekend(toestand) {
  if (!toestand) return false;
  const s = toestand.state;
  return s !== undefined && s !== null && s !== "unknown" && s !== "unavailable" && s !== "";
}

export function getal(toestand) {
  if (!bekend(toestand)) return null;
  const n = Number(toestand.state);
  return Number.isFinite(n) ? n : null;
}

/** Vermogen altijd in kW, zodat de getallen in een rij naast elkaar kloppen. */
export function vermogen(watt) {
  if (watt === null || watt === undefined || !Number.isFinite(watt)) {
    return { waarde: ONBEKEND, eenheid: "" };
  }
  return { waarde: NUMMER.format(watt / 1000), eenheid: "kW" };
}

export function energie(kwh, decimalen = 3) {
  if (kwh === null || kwh === undefined || !Number.isFinite(kwh)) {
    return { waarde: ONBEKEND, eenheid: "" };
  }
  const opmaak = decimalen === 1 ? NUMMER_1 : NUMMER_3;
  return { waarde: opmaak.format(kwh), eenheid: "kWh" };
}

export function procent(waarde, decimalen = 0) {
  if (waarde === null || waarde === undefined || !Number.isFinite(waarde)) {
    return { waarde: ONBEKEND, eenheid: "" };
  }
  const opmaak = decimalen === 1 ? NUMMER_1 : NUMMER_0;
  return { waarde: opmaak.format(waarde), eenheid: "%" };
}

export function geheel(waarde) {
  if (waarde === null || waarde === undefined || !Number.isFinite(waarde)) return ONBEKEND;
  return NUMMER_0.format(waarde);
}

/** Een getal met twee decimalen, los van een eenheid. */
export function tweeDecimalen(waarde) {
  if (waarde === null || waarde === undefined || !Number.isFinite(waarde)) return ONBEKEND;
  return NUMMER.format(waarde);
}
