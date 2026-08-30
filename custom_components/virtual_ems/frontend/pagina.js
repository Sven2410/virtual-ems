// De hele pagina in één kaart.
//
// De strategie zet één kaart in een paneelweergave neer, en die bouwt de
// pagina op. Zo bepaalt de huisstijl de opbouw, de breedte en de tussenruimte,
// in plaats van het raster van Home Assistant.

import { Kaart, tekst } from "./basis.js";
import { kaartCss } from "./stijl.js";
import { ids, installatieNaam } from "./entiteiten.js";
import { controleerVersie, huidigeVersie } from "./versie.js";

const PAGINA_CSS =
  kaartCss +
  `
  :host {
    display: block;
    background: var(--dt-bg);
    min-height: 100%;
  }

  .pagina {
    max-width: 1080px;
    margin: 0 auto;
    padding: 18px 16px 44px;
    display: grid;
    gap: 14px;
  }

  .voettekst {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 4px 6px 0;
    font-size: 11px;
    color: var(--dt-ink-3);
  }

  .voettekst .scheiding { opacity: 0.5; }

  .waarschuwing {
    color: var(--dt-warn);
  }

  @media (max-width: 520px) {
    .pagina { padding: 12px 10px 32px; gap: 12px; }
  }
`;

export class PaginaKaart extends Kaart {
  css() {
    return PAGINA_CSS;
  }

  bouw() {
    const slug = this._config.installatie;
    if (!slug) {
      return (
        "<div class='pagina'><div class='kaart'><p class='eyebrow'>Virtueel EMS</p>" +
        "<p class='titel'>Nog niet ingesteld</p>" +
        "<p class='onderschrift'>Deze kaart hoort te weten om welke installatie het gaat. " +
        "Gebruik de strategie, of zet er zelf installatie: virtueel_ems bij.</p></div></div>"
      );
    }
    this._ids = ids(slug);
    const docent = this._config.weergave === "docent";

    const onderdelen = [];
    onderdelen.push("<virtual-ems-kop></virtual-ems-kop>");
    onderdelen.push("<virtual-ems-kpis></virtual-ems-kpis>");
    if (docent) onderdelen.push("<virtual-ems-scenarios></virtual-ems-scenarios>");
    onderdelen.push("<virtual-ems-balken></virtual-ems-balken>");
    onderdelen.push("<virtual-ems-bediening></virtual-ems-bediening>");
    onderdelen.push("<virtual-ems-meter></virtual-ems-meter>");

    return (
      "<div class='pagina'>" +
      onderdelen.join("") +
      "<div class='voettekst'><span id='wie'></span><span class='scheiding'>|</span>" +
      "<span id='versie'></span><span id='melding' class='waarschuwing'></span></div>" +
      "</div>"
    );
  }

  ververs() {
    if (!this._ids) return;
    const slug = this._config.installatie;
    const docent = this._config.weergave === "docent";

    const kinderen = this.zoekAlle("virtual-ems-kop, virtual-ems-kpis, virtual-ems-balken, virtual-ems-bediening, virtual-ems-meter, virtual-ems-scenarios");
    kinderen.forEach((kind) => {
      if (!kind._configGezet) {
        if (typeof kind.setConfig === "function") {
          kind.setConfig({ installatie: slug, uitgebreid: docent, weergave: this._config.weergave });
          kind._configGezet = true;
        }
      }
      kind.hass = this.hass;
    });

    const naam = installatieNaam(this.hass, slug, this._ids.sensor_net_vermogen);
    tekst(this.zoek("#wie"), naam + (docent ? ", docentweergave" : ""));

    const serverVersie = this.kenmerk(this._ids.sensor_simulatietijd, "frontend_versie");
    const integratie = this.kenmerk(this._ids.sensor_simulatietijd, "integratie_versie");
    tekst(
      this.zoek("#versie"),
      "Virtueel EMS " + (integratie || "") + ", scherm " + huidigeVersie()
    );

    const stand = controleerVersie(serverVersie);
    tekst(
      this.zoek("#melding"),
      stand === "achter" ? "Dit scherm draait oude code en laadt zichzelf opnieuw." : ""
    );
  }

  getCardSize() {
    return 30;
  }
}
