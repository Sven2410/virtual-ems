// De lijst van entiteiten die de integratie aanmaakt, in dezelfde volgorde als
// catalog.py. tests/kern/test_frontend.py legt de twee naast elkaar, zodat een
// entiteit die aan de ene kant bijkomt niet aan de andere kant blijft ontbreken.

export const SENSOREN = [
  "pv_vermogen",
  "pv_opbrengst",
  "batterij_soc",
  "batterij_vermogen_actueel",
  "batterij_inhoud",
  "batterij_geladen",
  "batterij_ontladen",
  "laadpaal_vermogen",
  "laadpaal_verbruik",
  "huishoudelijk_verbruik",
  "verbruik_totaal",
  "net_vermogen",
  "net_afname",
  "net_teruglevering",
  "aansluiting_belasting",
  "zelfbenutting",
  "hoogste_piek",
  "regelactie",
  "laadpaal_limiet",
  "batterij_opdracht",
  "zekering_warmte",
  "zonnehoogte",
  "simulatietijd",
  "wasmachine_verbruik",
  "boiler_verbruik",
  "airco_verbruik",
];

export const NUMMERS = [
  "pv_bewolking",
  "batterij_vermogen",
  "batterij_min_soc",
  "batterij_max_soc",
  "laadpaal_vermogen",
  "piekgrens",
  "tijdversnelling",
];

export const SCHAKELAARS = [
  "laadpaal_actief",
  "aansluitbewaking",
  "wasmachine",
  "boiler",
  "airco",
];

export const KEUZES = ["regelmodus"];

export const BINAIRE = ["hoofdzekering"];

//: De standen van de regelmodus, in dezelfde volgorde als regelaar.py.
export const MODUSSEN = [
  { sleutel: "handmatig", naam: "Handmatig", uitleg: "Jij stuurt", ico: "schuif" },
  {
    sleutel: "zelfconsumptie",
    naam: "Zelfconsumptie",
    uitleg: "Zo min mogelijk over de meter",
    ico: "blad",
  },
  {
    sleutel: "piekscheren",
    naam: "Piekscheren",
    uitleg: "Afname onder een grens",
    ico: "meter",
  },
];

export const APPARATEN = ["wasmachine", "boiler", "airco"];

/**
 * De naam van de installatie zoals de docent hem heeft ingevuld.
 *
 * Het apparaat in het apparatenregister draagt die naam. De weergavenaam van
 * een entiteit is het apparaat plus de naam van de entiteit erachter, en die
 * staat er in de taal van de installatie bij, dus daar valt niet betrouwbaar
 * op te knippen. Vandaar eerst het apparaat, en pas daarna een terugval.
 */
export function installatieNaam(hass, slug, entityId) {
  const registratie = hass && hass.entities ? hass.entities[entityId] : undefined;
  const apparaatId = registratie ? registratie.device_id : undefined;
  const apparaat = apparaatId && hass.devices ? hass.devices[apparaatId] : undefined;
  if (apparaat) {
    const naam = apparaat.name_by_user || apparaat.name;
    if (naam) return naam;
  }

  const toestand = hass && hass.states ? hass.states[entityId] : undefined;
  const weergavenaam = toestand && toestand.attributes ? toestand.attributes.friendly_name : "";
  if (weergavenaam) {
    // Terugval: haal de naam van de entiteit er in de twee talen die deze
    // integratie levert vanaf.
    const gestript = String(weergavenaam).replace(/\s*(net vermogen|grid power)$/i, "").trim();
    if (gestript) return gestript;
  }

  return slug;
}

/** Alle entity_id's van één installatie, op sleutel. */
export function ids(slug) {
  const kaart = {};
  SENSOREN.forEach((sleutel) => {
    kaart["sensor_" + sleutel] = "sensor." + slug + "_" + sleutel;
  });
  NUMMERS.forEach((sleutel) => {
    kaart["number_" + sleutel] = "number." + slug + "_" + sleutel;
  });
  SCHAKELAARS.forEach((sleutel) => {
    kaart["switch_" + sleutel] = "switch." + slug + "_" + sleutel;
  });
  KEUZES.forEach((sleutel) => {
    kaart["select_" + sleutel] = "select." + slug + "_" + sleutel;
  });
  BINAIRE.forEach((sleutel) => {
    kaart["binary_sensor_" + sleutel] = "binary_sensor." + slug + "_" + sleutel;
  });
  return kaart;
}

/**
 * Zoek de installaties die op deze Home Assistant draaien.
 *
 * De netsensor bestaat bij elke installatie precies één keer, dus daar is de
 * naam-slug uit af te leiden. Waar het kan wordt de entiteitenlijst gebruikt om
 * te toetsen dat hij ook echt van virtual_ems komt; die lijst bestaat niet in
 * elke versie, en dan is het achtervoegsel alleen genoeg.
 */
export function vindInstallaties(hass) {
  if (!hass || !hass.states) return [];
  const achtervoegsel = "_net_vermogen";
  const gevonden = [];
  Object.keys(hass.states).forEach((entityId) => {
    if (!entityId.startsWith("sensor.") || !entityId.endsWith(achtervoegsel)) return;
    const registratie = hass.entities ? hass.entities[entityId] : undefined;
    if (registratie && registratie.platform && registratie.platform !== "virtual_ems") return;
    const slug = entityId.slice("sensor.".length, entityId.length - achtervoegsel.length);
    if (!slug) return;
    gevonden.push({ slug, naam: installatieNaam(hass, slug, entityId) });
  });
  gevonden.sort((a, b) => a.slug.localeCompare(b.slug));
  return gevonden;
}
