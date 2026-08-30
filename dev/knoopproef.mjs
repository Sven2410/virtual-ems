// Een snelle proef op de bundel zonder browser.
//
// Dit is nadrukkelijk géén nagebouwde browser. Er wordt hier niets beweerd over
// de CSS-cascade, over of een knop een klik aanneemt of over hoe iets eruitziet;
// daar is een echte browser voor, en die metingen staan in de rapporten. Wat
// hier wel te toetsen valt is pure logica: registreren de elementen zich, bouwt
// de strategie de goede configuratie, en klopt de opmaak van de getallen.
//
// Gebruik: node dev/knoopproef.mjs <map met de modules>

import { pathToFileURL } from "node:url";
import path from "node:path";

const map = process.argv[2];
if (!map) {
  console.error("Geef de map met de modules mee.");
  process.exit(2);
}

// De kleinst mogelijke omgeving waarin de modules willen laden. Alleen wat er
// bij het importeren en registreren aangeraakt wordt.
class NepElement {
  attachShadow() {
    // Een echte browser zet shadowRoot op het element zelf; dat doet deze ook,
    // anders schrijft de kaart in het niets.
    this.shadowRoot = {
      innerHTML: "",
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    return this.shadowRoot;
  }

  setAttribute() {}
  removeAttribute() {}
  getAttribute() {
    return null;
  }
  addEventListener() {}
  appendChild() {}
}

const gedefinieerd = new Map();
globalThis.HTMLElement = NepElement;
globalThis.customElements = {
  define(naam, klasse) {
    if (gedefinieerd.has(naam)) throw new Error("dubbel geregistreerd: " + naam);
    gedefinieerd.set(naam, klasse);
  },
  get: (naam) => gedefinieerd.get(naam),
  whenDefined: () => Promise.resolve(),
};
globalThis.window = { customCards: [], location: { reload() {} }, sessionStorage: null };
globalThis.document = {
  visibilityState: "visible",
  addEventListener() {},
  createElement: () => new NepElement(),
};

const fouten = [];
function eis(voorwaarde, wat) {
  if (!voorwaarde) fouten.push(wat);
}

const url = (naam) => pathToFileURL(path.join(map, naam)).href;

const registratie = await import(url("registratie.mjs"));
const entiteiten = await import(url("entiteiten.mjs"));
const stijl = await import(url("stijl.mjs"));

const geregistreerd = await registratie.registreerAlles();

// --- 1. Alles registreert zich, en precies één keer -------------------------

for (const naam of registratie.verwachteElementen()) {
  eis(gedefinieerd.has(naam), "niet geregistreerd: " + naam);
}
eis(
  gedefinieerd.size === registratie.verwachteElementen().length,
  "er zijn andere elementen geregistreerd dan verwacht"
);
eis(geregistreerd.length === gedefinieerd.size, "de teruggave klopt niet met wat er staat");

// Twee keer aanroepen mag geen dubbele registratie geven; Home Assistant laadt
// een module soms meer dan eens.
await registratie.registreerAlles();

// --- 2. De entity_id's ------------------------------------------------------

const ids = entiteiten.ids("lokaal_a");
eis(ids.sensor_regelactie === "sensor.lokaal_a_regelactie", "sensor-id klopt niet");
eis(ids.select_regelmodus === "select.lokaal_a_regelmodus", "select-id klopt niet");
eis(
  ids.binary_sensor_hoofdzekering === "binary_sensor.lokaal_a_hoofdzekering",
  "binary_sensor-id klopt niet"
);
eis(ids.number_piekgrens === "number.lokaal_a_piekgrens", "number-id klopt niet");
eis(ids.switch_aansluitbewaking === "switch.lokaal_a_aansluitbewaking", "switch-id klopt niet");

// --- 3. De opmaak van getallen is Nederlands --------------------------------

eis(stijl.vermogen(3104).waarde === "3,10", "vermogen wordt niet Nederlands opgemaakt");
eis(stijl.vermogen(-618).waarde === "-0,62", "negatief vermogen klopt niet");
eis(stijl.energie(11.42, 1).waarde === "11,4", "energie met één decimaal klopt niet");
eis(stijl.procent(91.8).waarde === "92", "procent wordt niet afgerond");
eis(stijl.vermogen(null).waarde === "onbekend", "onbekend hoort onbekend te heten");
eis(stijl.procent(null).waarde === "onbekend", "onbekend hoort onbekend te heten");
eis(stijl.getal({ state: "unavailable" }) === null, "unavailable is geen getal");
eis(stijl.getal({ state: "12.5" }) === 12.5, "een gewoon getal wordt niet gelezen");

// --- 4. De strategie bouwt de goede configuratie ----------------------------

const hass = {
  states: {
    "sensor.lokaal_a_net_vermogen": { attributes: { friendly_name: "Lokaal A Net vermogen" } },
    "sensor.lokaal_b_net_vermogen": { attributes: { friendly_name: "Lokaal B Net vermogen" } },
    "sensor.iets_anders": { attributes: {} },
  },
  entities: {
    "sensor.lokaal_a_net_vermogen": { platform: "virtual_ems", device_id: "d1" },
    "sensor.lokaal_b_net_vermogen": { platform: "virtual_ems", device_id: "d2" },
  },
  devices: { d1: { name: "Lokaal A" }, d2: { name: "Lokaal B", name_by_user: "Praktijklokaal" } },
};

const Strategie = gedefinieerd.get("ll-strategy-dashboard-virtual-ems");
const cursist = await Strategie.generate({}, hass);
eis(cursist.views.length === 2, "er hoort een weergave per installatie te komen");
eis(cursist.views[0].title === "Lokaal A", "de naam komt niet uit het apparatenregister");
eis(cursist.views[1].title === "Praktijklokaal", "een eigen naam gaat voor");
eis(cursist.views[0].type === "panel", "de weergave hoort een paneel te zijn");
eis(cursist.views[0].cards[0].weergave === "cursist", "de weergave klopt niet");

const docent = await Strategie.generate({ weergave: "docent" }, hass);
eis(docent.title === "EMS docent", "de titel van het docentdashboard klopt niet");
eis(docent.views[0].cards[0].weergave === "docent", "de docentweergave komt niet door");

const een = await Strategie.generate({ installatie: "lokaal_b" }, hass);
eis(een.views.length === 1, "filteren op één installatie werkt niet");

const leeg = await Strategie.generate({}, { states: {} });
eis(leeg.views.length === 1, "zonder installaties hoort er een uitlegweergave te komen");
eis(leeg.views[0].cards[0].installatie === undefined, "de uitlegkaart hoort geen installatie te hebben");

// --- 5. De kaarten gooien niet op een lege of rare configuratie -------------

for (const naam of ["virtual-ems-pagina", "virtual-ems-kop", "virtual-ems-kpis"]) {
  const Klasse = gedefinieerd.get(naam);
  const kaart = new Klasse();
  // Home Assistant roept setConfig aan bij elke toetsaanslag in de editor, en
  // eenmaal met een lege stub. Gooien mag hier dus niet.
  kaart.setConfig({});
  kaart.setConfig(null);
  kaart.setConfig({ installatie: "lokaal_a" });
  eis(typeof kaart.getCardSize() === "number", naam + " geeft geen kaartgrootte");
}

if (fouten.length) {
  for (const fout of fouten) console.error("FOUT: " + fout);
  process.exit(1);
}

console.log(
  JSON.stringify({
    elementen: geregistreerd.length,
    kaartkiezer: globalThis.window.customCards.length,
    weergaven: cursist.views.length,
  })
);
