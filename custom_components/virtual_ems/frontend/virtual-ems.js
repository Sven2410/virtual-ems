// De ingang van de bundel. Home Assistant laadt dit bestand met een ?v= erachter
// waarin de hash van de frontend staat, zodat een nieuwe uitgave ook echt een
// nieuw bestand is en niet uit een cache komt.

import { registreerAlles } from "./registratie.js";
import { zetEigenVersie } from "./versie.js";

zetEigenVersie(import.meta.url);

registreerAlles().then(
  (elementen) => {
    // Eén regel in de console, zodat bij een melding meteen te zien is welke
    // versie dat toestel draait.
    console.info(
      "%cVIRTUEEL EMS%c frontend geladen, versie " +
        new URL(import.meta.url).searchParams.get("v") +
        ", " +
        elementen.length +
        " onderdelen",
      "background:#026fa1;color:#e8e4de;padding:2px 6px;border-radius:4px",
      "color:#8a8a85"
    );
  },
  (fout) => {
    console.error("Virtueel EMS: de frontend kon niet geladen worden", fout);
  }
);
