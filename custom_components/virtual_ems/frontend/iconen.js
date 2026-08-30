// Iconen, met de hand getekend uit rechte lijnen en bogen.
//
// Ze zitten bewust in dit bestand en komen niet uit een pictogrammenpakket:
// dan hoeft er niets geladen te worden, werken ze in een werkbank zonder Home
// Assistant, en is er geen licentie van een ander in het spel.
//
// Elke stroom draagt een eigen icoon en een geschreven label, zodat kleur nooit
// alleen hoeft te werken.

const VORMEN = {
  zon:
    '<circle cx="12" cy="12" r="4.2"/>' +
    '<path d="M12 2v2.4M12 19.6V22M2 12h2.4M19.6 12H22' +
    'M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M19.1 4.9l-1.7 1.7M6.6 17.4l-1.7 1.7"/>',

  huis: '<path d="M3.5 11.2 12 4.2l8.5 7"/><path d="M6 10.5V20h12v-9.5"/>',

  net:
    '<path d="M12 3.5v17"/><path d="M7 20.5 12 9.5l5 11"/>' +
    '<path d="M8.7 14.5h6.6M9.8 10.5h4.4"/><path d="M5 20.5h14"/>',

  batterij:
    '<rect x="3" y="7.5" width="15" height="9" rx="2.4"/>' +
    '<path d="M20.6 10.6v2.8"/>' +
    '<rect x="5.4" y="9.9" width="6" height="4.2" rx="1" fill="currentColor" stroke="none"/>',

  laadpaal:
    '<rect x="6.4" y="3.4" width="9.2" height="11.4" rx="2.4"/>' +
    '<path d="M9.4 7.1h3.2M9.4 10.3h3.2"/>' +
    '<path d="M11 14.8V20"/><path d="M8.4 20.6h5.2"/>',

  blad:
    '<path d="M5 19c0-7.7 6-12.9 14-12.9C19 13.8 13 19 5 19z"/>' +
    '<path d="M5.4 18.6c2.9-4 5.9-6.2 8.9-7.2"/>',

  meter:
    '<path d="M4 17a8 8 0 1 1 16 0"/>' +
    '<path d="M12 17l4.3-4.7"/>' +
    '<circle cx="12" cy="17" r="1.2" fill="currentColor" stroke="none"/>',

  wolk: '<path d="M7.6 18.4h8.9a4 4 0 0 0 .4-8 5.6 5.6 0 0 0-10.5-1.3 3.7 3.7 0 0 0 1.2 9.3z"/>',

  wasmachine:
    '<rect x="4.5" y="3.5" width="15" height="17" rx="2.4"/>' +
    '<circle cx="12" cy="13.6" r="4.1"/>' +
    '<path d="M7.8 7.2h2.2"/><path d="M15.4 7.2h.8"/>',

  boiler:
    '<rect x="6.5" y="3" width="11" height="13.6" rx="3.2"/>' +
    '<path d="M9.6 16.6V20M14.4 16.6V20M9.6 7.4h4.8"/>',

  airco:
    '<rect x="3.5" y="5" width="17" height="6.8" rx="2.2"/>' +
    '<path d="M6.9 15.4c1.2 1.4 2.4 1.4 3.6 0M13.5 15.4c1.2 1.4 2.4 1.4 3.6 0"/>' +
    '<path d="M6.9 18.9c1.2 1.4 2.4 1.4 3.6 0M13.5 18.9c1.2 1.4 2.4 1.4 3.6 0"/>',

  klok: '<circle cx="12" cy="12" r="8.2"/><path d="M12 7.3V12l3.3 2"/>',

  vonk: '<path d="M13.2 3 6 13.4h5.2L10.8 21 18 10.6h-5.2z"/>',

  omhoog: '<path d="M12 19.5V5.5"/><path d="M6.6 10.9 12 5.5l5.4 5.4"/>',

  omlaag: '<path d="M12 4.5v14"/><path d="M6.6 13.1 12 18.5l5.4-5.4"/>',

  balans: '<path d="M4 12h16"/><path d="M4 7h9.5"/><path d="M10.5 17H20"/>',

  terug: '<path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20.2 3.8v4.8h-4.8"/>',

  schuif:
    '<path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h9M17 17h3"/>' +
    '<circle cx="15" cy="7" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="17" r="2"/>',

  robot:
    '<rect x="4.5" y="7.5" width="15" height="11" rx="3"/>' +
    '<path d="M12 4v3.5"/><circle cx="12" cy="3.2" r="1.2"/>' +
    '<circle cx="9.2" cy="12.4" r="1.3" fill="currentColor" stroke="none"/>' +
    '<circle cx="14.8" cy="12.4" r="1.3" fill="currentColor" stroke="none"/>' +
    '<path d="M9.6 15.8h4.8"/>',

  zekering:
    '<rect x="6.5" y="9" width="11" height="6" rx="1.6"/>' +
    '<path d="M3.5 12h3M17.5 12h3"/><path d="M8.6 12h6.8"/>',

  schild:
    '<path d="M12 3.2l7 2.6v5.4c0 4.2-2.9 7.6-7 9.6-4.1-2-7-5.4-7-9.6V5.8z"/>' +
    '<path d="M9 12.2l2.2 2.2 4-4.2"/>',

  ster: '<path d="M12 3.6l2.5 5.3 5.7.8-4.1 4.1 1 5.8-5.1-2.8-5.1 2.8 1-5.8-4.1-4.1 5.7-.8z"/>',
};

/** Geef de SVG van een icoon. Een onbekende naam geeft een stille stip. */
export function icoon(naam, grootte = 18) {
  const vorm = VORMEN[naam] || '<circle cx="12" cy="12" r="3.4"/>';
  return (
    '<svg viewBox="0 0 24 24" width="' +
    grootte +
    '" height="' +
    grootte +
    '" fill="none" stroke="currentColor" stroke-width="1.7" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    vorm +
    "</svg>"
  );
}

export function icoonNamen() {
  return Object.keys(VORMEN);
}
