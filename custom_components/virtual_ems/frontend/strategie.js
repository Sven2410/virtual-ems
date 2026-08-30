// De strategie: een dashboard dat zichzelf opbouwt.
//
// De docent maakt een leeg dashboard aan en zet er dit in:
//
//   strategy:
//     type: custom:virtual-ems
//
// Meer is het niet. De strategie zoekt zelf welke installaties er draaien en
// zet per installatie een weergave neer, met de juiste entiteitsnamen, hoe de
// installatie ook heet.

import { vindInstallaties } from "./entiteiten.js";

function bouwWeergave(installatie, weergave) {
  return {
    title: installatie.naam,
    path: installatie.slug,
    type: "panel",
    icon: weergave === "docent" ? "mdi:teach" : "mdi:home-lightning-bolt",
    cards: [
      {
        type: "custom:virtual-ems-pagina",
        installatie: installatie.slug,
        weergave: weergave,
      },
    ],
  };
}

export class VirtualEmsStrategie extends HTMLElement {
  static async generate(config, hass) {
    const weergave = config && config.weergave === "docent" ? "docent" : "cursist";
    let installaties = vindInstallaties(hass);

    if (config && config.installatie) {
      installaties = installaties.filter((installatie) => installatie.slug === config.installatie);
    }

    if (!installaties.length) {
      // Niets gevonden is iets anders dan stuk. De uitlegkaart zegt wat er
      // moet gebeuren in plaats van een leeg scherm te tonen.
      return {
        title: "Virtueel EMS",
        views: [
          {
            title: "Virtueel EMS",
            type: "panel",
            cards: [{ type: "custom:virtual-ems-pagina" }],
          },
        ],
      };
    }

    return {
      title: weergave === "docent" ? "EMS docent" : "Energiebeheer",
      views: installaties.map((installatie) => bouwWeergave(installatie, weergave)),
    };
  }
}
