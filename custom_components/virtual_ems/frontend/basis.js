// Wat alle kaarten delen. Eén hand, geen verzameling: de stijl staat hier en
// wordt niet per kaart opnieuw geschreven.

import { kaartCss } from "./stijl.js";

export class Kaart extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._opgebouwd = false;
  }

  /**
   * Home Assistant roept dit bij élke toetsaanslag in de editor aan, en eenmaal
   * met een lege stub. Gooien mag hier dus niet: een lege configuratie levert
   * een uitlegkaart op.
   */
  setConfig(config) {
    this._config = config && typeof config === "object" ? config : {};
    this._opgebouwd = false;
    this._bouwOpnieuw();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._opgebouwd) {
      this._bouwOpnieuw();
    }
    if (this._opgebouwd) {
      try {
        this.ververs();
      } catch (fout) {
        this._toonFout(fout);
      }
    }
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    if (!this._opgebouwd) this._bouwOpnieuw();
  }

  _bouwOpnieuw() {
    if (!this._config) return;
    try {
      const html = this.bouw();
      if (html === null) return;
      this.shadowRoot.innerHTML = "<style>" + this.css() + "</style>" + html;
      this._opgebouwd = true;
      if (this._hass) this.ververs();
    } catch (fout) {
      this._toonFout(fout);
    }
  }

  _toonFout(fout) {
    // Een kapotte kaart hoort te zeggen wat er mis is, niet leeg te blijven.
    const tekst = fout && fout.message ? fout.message : String(fout);
    this.shadowRoot.innerHTML =
      "<style>" +
      this.css() +
      "</style><div class='kaart'><p class='eyebrow'>Virtueel EMS</p>" +
      "<p class='titel'>Deze kaart kan niet getekend worden</p>" +
      "<p class='onderschrift'></p></div>";
    const uitleg = this.shadowRoot.querySelector(".onderschrift");
    if (uitleg) uitleg.textContent = tekst;
    this._opgebouwd = false;
  }

  css() {
    return kaartCss;
  }

  /** Bouw de opzet van de kaart. Geef null om nog niets te tekenen. */
  bouw() {
    return "<div class='kaart'></div>";
  }

  /** Zet de waarden erin. Wordt bij elke toestandswijziging aangeroepen. */
  ververs() {}

  toestand(entityId) {
    if (!this._hass || !this._hass.states || !entityId) return undefined;
    return this._hass.states[entityId];
  }

  kenmerk(entityId, naam) {
    const toestand = this.toestand(entityId);
    if (!toestand || !toestand.attributes) return undefined;
    return toestand.attributes[naam];
  }

  roep(domein, dienst, gegevens) {
    if (!this._hass || typeof this._hass.callService !== "function") return;
    this._hass.callService(domein, dienst, gegevens);
  }

  zoek(selector) {
    return this.shadowRoot.querySelector(selector);
  }

  zoekAlle(selector) {
    return Array.prototype.slice.call(this.shadowRoot.querySelectorAll(selector));
  }

  getCardSize() {
    return 4;
  }
}

/** Zet tekst zonder de knoop opnieuw op te bouwen; scheelt geflikker. */
export function tekst(element, waarde) {
  if (!element) return;
  const nieuw = waarde === null || waarde === undefined ? "" : String(waarde);
  if (element.textContent !== nieuw) element.textContent = nieuw;
}

/** Zet een stijlwaarde alleen als hij verandert. */
export function stijl(element, naam, waarde) {
  if (!element) return;
  if (element.style.getPropertyValue(naam) !== waarde) {
    element.style.setProperty(naam, waarde);
  }
}

/** Begrens een fractie op 0 tot 100 procent, zodat een balk niet uitloopt. */
export function balkBreedte(waarde, grens) {
  if (!Number.isFinite(waarde) || !Number.isFinite(grens) || grens <= 0) return 0;
  return Math.max(0, Math.min(100, (Math.abs(waarde) / grens) * 100));
}

/** Een korte, veilige tekst voor in HTML. */
export function veilig(waarde) {
  return String(waarde === null || waarde === undefined ? "" : waarde)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
