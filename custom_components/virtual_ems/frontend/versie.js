// Welke versie draait dit toestel eigenlijk?
//
// "De server is bij" zegt niets over wat een toestel draait. Een webview in een
// app blijft dagen in leven en er komt geen paginalading aan te pas. Daarom:
// de bundel leest zijn eigen versie uit de URL waarmee hij geladen is, de
// integratie zet dezelfde versie in een kenmerk van een entiteit, en zodra die
// twee uiteenlopen laadt de pagina zich eenmalig opnieuw. En de versie staat
// gewoon in beeld, onderaan het dashboard.

let eigenVersie = "onbekend";
let alGeladen = false;

const SLEUTEL = "virtual_ems_herladen";

export function zetEigenVersie(moduleUrl) {
  try {
    const url = new URL(moduleUrl);
    eigenVersie = url.searchParams.get("v") || "onbekend";
  } catch (fout) {
    eigenVersie = "onbekend";
  }
  return eigenVersie;
}

export function huidigeVersie() {
  return eigenVersie;
}

/**
 * Vergelijk de eigen versie met wat de server zegt en laad eenmalig opnieuw.
 *
 * Eenmalig: de vlag in sessionStorage voorkomt dat een toestel dat om een
 * andere reden oude code houdt in een herlaadlus terechtkomt.
 */
export function controleerVersie(serverVersie) {
  if (!serverVersie || serverVersie === "onbekend") return "onbekend";
  if (eigenVersie === "onbekend") return "onbekend";
  if (serverVersie === eigenVersie) {
    try {
      window.sessionStorage.removeItem(SLEUTEL);
    } catch (fout) {
      // Een browser die opslag weigert is geen reden om te stoppen.
    }
    return "bij";
  }

  let alGeprobeerd = false;
  try {
    alGeprobeerd = window.sessionStorage.getItem(SLEUTEL) === serverVersie;
  } catch (fout) {
    alGeprobeerd = alGeladen;
  }
  if (alGeprobeerd || alGeladen) return "achter";

  alGeladen = true;
  try {
    window.sessionStorage.setItem(SLEUTEL, serverVersie);
  } catch (fout) {
    // Zonder opslag blijft de vlag in het geheugen van deze pagina staan.
  }

  const herlaad = () => {
    if (document.visibilityState === "visible") {
      window.location.reload();
    }
  };
  if (document.visibilityState === "visible") {
    window.setTimeout(herlaad, 400);
  } else {
    document.addEventListener("visibilitychange", herlaad, { once: true });
  }
  return "achter";
}
