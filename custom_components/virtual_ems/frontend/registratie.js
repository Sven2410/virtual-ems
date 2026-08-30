// De enige plek waar een custom element geregistreerd wordt.
//
// Home Assistant draait scoped-custom-element-registry. Win je de race met zijn
// eigen import(), dan is je element daarna onzichtbaar: geen fout, geen
// logregel, en "Configuratiefout" op elke kaart. Daarom staat hier één plek die
// wacht tot de frontend zelf klaar is, en daarna pas registreert.
//
// scripts/bewaak_frontend.py controleert dat er nergens anders een
// customElements.define staat. Kennis in één bestand is geen bewaking.

import { BalkKaart, KopKaart, KpiKaart } from "./kaarten.js";
import { BedieningKaart, MeterKaart, ScenarioKaart } from "./bediening.js";
import { PaginaKaart } from "./pagina.js";
import { VirtualEmsStrategie } from "./strategie.js";

const ELEMENTEN = [
  ["virtual-ems-pagina", PaginaKaart, "Virtueel EMS pagina", "Het hele dashboard in één kaart"],
  ["virtual-ems-kop", KopKaart, "Virtueel EMS kop", "Wat er nu gebeurt, in één zin"],
  ["virtual-ems-kpis", KpiKaart, "Virtueel EMS kentallen", "De rij met opwek, verbruik en net"],
  ["virtual-ems-balken", BalkKaart, "Virtueel EMS balken", "Waar het vermogen heen gaat"],
  ["virtual-ems-bediening", BedieningKaart, "Virtueel EMS bediening", "De schuiven en schakelaars"],
  ["virtual-ems-meter", MeterKaart, "Virtueel EMS meterstanden", "De cumulatieve tellers"],
  ["virtual-ems-scenarios", ScenarioKaart, "Virtueel EMS scenario's", "Knoppen voor de docent"],
];

const STRATEGIE = ["ll-strategy-dashboard-virtual-ems", VirtualEmsStrategie];

async function wachtOpDeFrontend() {
  if (typeof customElements === "undefined") return;
  if (customElements.get("home-assistant")) return;
  // In een werkbank zonder Home Assistant komt home-assistant nooit, dus er
  // staat een wekker naast.
  await Promise.race([
    customElements.whenDefined("home-assistant"),
    new Promise((klaar) => {
      setTimeout(klaar, 2000);
    }),
  ]);
}

function meldAan(naam, omschrijving) {
  window.customCards = window.customCards || [];
  const bestaat = window.customCards.some((kaart) => kaart.type === naam);
  if (bestaat) return;
  window.customCards.push({
    type: naam,
    name: omschrijving.naam,
    description: omschrijving.uitleg,
    preview: false,
    documentationURL: "https://github.com/Sven2410/virtual-ems",
  });
}

export async function registreerAlles() {
  await wachtOpDeFrontend();

  ELEMENTEN.forEach((regel) => {
    const naam = regel[0];
    const klasse = regel[1];
    if (!customElements.get(naam)) {
      customElements.define(naam, klasse);
    }
    meldAan(naam, { naam: regel[2], uitleg: regel[3] });
  });

  if (!customElements.get(STRATEGIE[0])) {
    customElements.define(STRATEGIE[0], STRATEGIE[1]);
  }

  return ELEMENTEN.map((regel) => regel[0]).concat([STRATEGIE[0]]);
}

export function verwachteElementen() {
  return ELEMENTEN.map((regel) => regel[0]).concat([STRATEGIE[0]]);
}
