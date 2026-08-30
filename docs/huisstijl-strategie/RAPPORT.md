# Ronde 2: een dashboard dat zichzelf opbouwt, in de huisstijl

Datum: 30 augustus 2026
Repository: <https://github.com/Sven2410/virtual-ems>
Tak: `ronde-2-huisstijl-strategie`

---

## 1. Wat er staat

**Een Lovelace-strategie.** De docent maakt een leeg dashboard aan en zet er
drie regels in:

```yaml
strategy:
  type: custom:virtual-ems
```

De strategie zoekt zelf welke installaties er draaien, haalt de naam uit het
apparatenregister en bouwt per installatie een weergave. Er valt niets te
hernoemen en niets te kopieren. Met `weergave: docent` komt er een tweede
dashboard met de scenarioknoppen erbij.

**Zeven eigen kaarten**, in de huisstijl, met de tokens letterlijk uit
`theme.js`:

| Element | Wat het toont |
| --- | --- |
| `virtual-ems-pagina` | De hele pagina, gebruikt door de strategie |
| `virtual-ems-kop` | Wat er nu gebeurt, in één zin, met de netstand als pil |
| `virtual-ems-kpis` | De rij van zes: zon, woning, net, belastbaarheid, zelfbenutting, batterij |
| `virtual-ems-balken` | Waar het vermogen heen gaat, tegen de aansluitwaarde |
| `virtual-ems-bediening` | De schuiven en de schakelaars |
| `virtual-ems-meter` | De cumulatieve tellers |
| `virtual-ems-scenarios` | De knoppenrij voor de docent |

**De integratie levert zijn eigen frontend.** Hij zet de bundel op een eigen
URL, meldt hem aan bij de frontend en probeert hem ook als Lovelace-resource te
registreren. De URL draagt de hash van de frontendmap, en diezelfde hash staat
als kenmerk op `sensor.<naam>_simulatietijd`. Zo kan een scherm zien dat het
oude code draait en zich eenmalig herladen.

**Twee kentallen erbij**, omdat de balken en de percentages uit die
schermafdruk een echte schaal nodig hebben en niet een verzonnen maximum:

* `sensor.<naam>_aansluiting_belasting`, in procent van wat de aansluiting
  aankan, met de grens als kenmerk erbij. Teruglevering belast de aansluiting
  net zo goed als afname, dus de absolute waarde telt.
* `sensor.<naam>_zelfbenutting`, welk deel van de eigen opwek ook zelf gebruikt
  is. Zolang er niets opgewekt is geeft die sensor `onbekend`: dan valt er niets
  te verdelen, en elk getal zou verzonnen zijn.

En twee instellingen in de optiesdialoog: **aansluiting per fase** (standaard
25 A) en **aantal fasen** (standaard 3). Samen 17,25 kW, en dat is waar elke
balk tegenaan ligt.

---

## 2. Gemeten in een echte browser

Een synthetisch event bewijst de handler, niet de knop. Alles hieronder is
gemeten in Chrome, op `dev/werkbank.html`, dat de echte kaarten draait tegen een
nagemaakte Home Assistant. De werkbank bootst niets na: het zijn dezelfde
bestanden die de integratie serveert.

### 2.1 Eerst: draai ik wel verse code

De werkbank haalt elk bestand op en telt de tekens, zodat het naast het bestand
op schijf te leggen is. Alle elf komen tot op het teken overeen:

| Bestand | Browser | Op schijf |
| --- | --- | --- |
| virtual-ems.js | 900 | 900 |
| registratie.js | 2894 | 2894 |
| stijl.js | 6742 | 6742 |
| kaarten.js | 20632 | 20632 |
| bediening.js | 18583 | 18583 |
| basis.js | 4000 | 4000 |
| iconen.js | 3226 | 3226 |
| entiteiten.js | 2599 | 2599 |
| pagina.js | 3795 | 3795 |
| strategie.js | 1731 | 1731 |
| versie.js | 2198 | 2198 |

Bij de eerste vergelijking liep `stijl.js` 225 tekens uit de pas. Dat bleek geen
oude code maar het regeleinde: dat ene bestand stond nog op CRLF en Python telde
die niet mee. Nagemeten op de ruwe bytes klopte het wel. De bestanden staan nu
allemaal op enkele regeleindes.

Alle acht elementen zijn geregistreerd, de strategie inbegrepen, en de console
geeft één regel en geen enkele fout:

```
VIRTUEEL EMS frontend geladen, versie 1788090152147, 8 onderdelen
```

### 2.2 De rij van zes staat gelijk

Gemeten met `getBoundingClientRect`, niet op het oog:

```
zon        x=429  b=165  h=144
huis       x=605  b=165  h=144
net        x=782  b=165  h=144
belasting  x=959  b=165  h=144
zelf       x=1135 b=165  h=144
accu       x=1312 b=165  h=144
rijen: 1   tussenruimte: 11, 12, 12, 11, 12
```

Zes tegels, één rij, gelijke breedte en hoogte, en een tussenruimte van 12px die
door afronding op subpixels soms als 11 uitkomt. Bij de eerste meting stonden er
vijf op de eerste rij en één op de tweede: de ondergrens van de kolommen stond
op 168px en dat past net niet in 1048px. Nu op 150px.

Ook de bijschriften zijn nagemeten: bij de eerste versie werden er drie afgekapt
met een beletselteken. De teksten zijn ingekort tot ze passen, en gemeten
`scrollWidth == clientWidth` voor alle zes.

### 2.3 De kleuren zijn de kleuren

`getComputedStyle` op de icoonchips en de balken:

| Onderdeel | Gemeten | Token |
| --- | --- | --- |
| Zon | rgb(220, 115, 0) | `--solar` #dc7300 |
| Woning | rgb(35, 94, 250) | `--house` #235efa |
| Net, terugleverend | rgb(188, 16, 200) | `--grid-out` #bc10c8 |
| Laadpaal | rgb(253, 7, 116) | `--device-1` #fd0774 |
| Batterij | rgb(3, 149, 128) | `--device-2` #039580 |
| Belastbaarheid, ruim | rgb(12, 163, 12) | `--good` #0ca30c |

Het net staat op `--grid-out` omdat er op dat moment teruggeleverd wordt; bij
afname wisselt hij naar `--grid-in`. Import en export komen nooit samen voor,
dus dat is geen dubbel gebruik van een kleur.

Het getal zelf draagt geen kleur: gemeten `rgb(232, 228, 222)`, de gewone inkt,
met `font-variant-numeric: tabular-nums`. De identiteit zit in de icoonchip en in
de stip ernaast, en elke stroom draagt bovendien een geschreven label.

### 2.4 De regels die je niet ziet

| Gemeten | Uitkomst |
| --- | --- |
| `box-shadow` op een kaart | `none`, alleen de haarlijn |
| `border-radius` op een kaart | `20px` |
| `font-family` | begint met `system-ui`, geen webfont |
| `transition-duration` van een balk | `1e-06s`, want deze Chrome staat op reduced motion |
| Hoogte van een schuif | 44px |
| Hoogte van een schakelaarregel | 56px, de rasterhoogte van Home Assistant |
| Breedte van de pagina | 1080px, gecentreerd |

### 2.5 Echte kliks, echte toetsaanslagen

Een capture-luisteraar op `window` legt vast wat er werkelijk aankomt. De
browsertool klikt in schermafdruk-coördinaten; de factor was in deze sessie
1568/1920 = 0,8167, afgelezen van een verse schermafdruk.

Klik op de schakelaar van de boiler, omgerekend naar schermafdruk (778, 386):

```
kliks:     [{ op: "BUTTON", klasse: "schakelaar", x: 953, y: 473, echt: true }]
aanroepen: [{ domein: "switch", dienst: "toggle",
              gegevens: { entity_id: "switch.lokaal_a_boiler" } }]
stand na de klik: aria-checked=false, tekst "uit"
focus binnen de kaart na de klik: geen
```

`echt: true` is `isTrusted`. De klik landde op precies de plek die
`getBoundingClientRect` opgaf, de juiste service ging eruit, en er bleef geen
focus achter in de kaart. Dat laatste is met opzet: een dialoog of een tik geeft
de focus programmatisch terug, en dan matcht `:focus-visible` ook na een tik met
een vinger. Repareer je alleen de hover, dan blijft de helft van die klacht
staan.

Daarna een echte klik op de bewolkingsschuif plus drie echte pijltjestoetsen:

```
kliks:   [{ op: "INPUT", x: 802, y: 463, echt: true }]
toetsen: [ArrowRight echt=true, ArrowRight echt=true, ArrowRight echt=true]
```

### 2.6 Wat die meting aan het licht bracht

Eén klik en drie toetsaanslagen leverden **tien** serviceaanroepen op voor vier
waardes:

```
35, 35, 35, 36, 36, 36, 37, 37, 38, 38
```

De oorzaak: `input`, `keyup`, `change` en op een aanraakscherm ook `pointerup`
vuren alle vier, en elk daarvan stuurde. Op een dashboard met dertig cursisten is
dat drie keer zoveel verkeer als nodig. De schuif onthoudt nu de laatst
verstuurde waarde en slaat een herhaling over. Zelfde handeling, opnieuw
gemeten:

```
35, 36, 37, 38     vier aanroepen, één per waarde
```

En een tweede vondst: de strategie noemde de weergave eerst
`Lokaal A net vermogen`. Hij haalde de naam uit de weergavenaam van de netsensor,
en die is het apparaat plus de naam van de entiteit, in de taal van de
installatie. Nu komt de naam uit het apparatenregister, met de oude route als
terugval. Gemeten met en zonder apparatenregister: beide keren `Lokaal A`.

### 2.7 Smalle schermen, echt gemeten

Het venster liet zich in deze sessie niet verkleinen: na `resize_window` bleef
`window.innerWidth` gewoon 1920. Een popup werd geblokkeerd. Wat wél werkt is een
iframe: dat krijgt zijn eigen viewport, dus de mediaqueries op breedte gelden
daar tegen de breedte van het frame.

| Viewport | Zijwaarts scrollbaar | Elementen breder dan de viewport |
| --- | --- | --- |
| 390 px | nee | 0 |
| 320 px | nee | 0 |
| 280 px | nee | 0 |

280 px hoort erbij omdat iOS inzoomt zodra een invoerveld kleiner dan 16px de
focus krijgt, en de viewport dan smaller wordt dan de 320 waar iedereen op test.

### 2.8 Het scherm weet welke versie het draait

Onderaan staat: `Lokaal A | Virtueel EMS 1.1.0, scherm 1788090032743`.

Zolang de versie van de bundel gelijk is aan wat de integratie meldt, staat er
verder niets. Zodra de server een andere versie meldt:

```
melding: "Dit scherm draait oude code en laadt zichzelf opnieuw."
vlag in sessionStorage: "nieuwer-1234"
```

De vlag zorgt dat dit precies één keer gebeurt per serverversie, zodat een
toestel dat om een andere reden oude code houdt niet in een herlaadlus komt.

### 2.9 De strategie zelf

Aangeroepen zoals Home Assistant hem aanroept:

```
{"title":"Energiebeheer","views":[{"title":"Lokaal A","path":"lokaal_a",
 "type":"panel","icon":"mdi:home-lightning-bolt",
 "cards":[{"type":"custom:virtual-ems-pagina","installatie":"lokaal_a",
           "weergave":"cursist"}]}]}
```

Met `weergave: docent` wordt de titel `EMS docent` en krijgt de kaart
`weergave: docent`. Zonder installaties komt er een uitlegweergave in plaats van
een leeg scherm.

---

## 3. De bewakers

`scripts/bewaak_frontend.py` draait mee in de proefronde en in CI, en hij draait
op een machine zonder Home Assistant. Hij vangt zes dingen:

1. **Een stijlblok dat middenin een commentaar ophoudt.** Niet de accent grave
   zelf wordt gezocht maar het gevolg ervan, want `node --check` gaf daar ooit
   groen op terwijl de browser de bundel weigerde.
2. **Een `customElements.define` buiten `registratie.js`.** Home Assistant draait
   scoped-custom-element-registry; win je de race met zijn eigen `import()`, dan
   is je element daarna onzichtbaar, zonder fout en zonder logregel.
3. **`position: fixed`**, dat niet vast aan het scherm zit zodra een voorouder
   een transform of filter heeft. Er zweeft hier niets, dus het hoort er niet in
   te staan.
4. **Verbergen met `hidden` zonder de bijbehorende CSS-regel**, want elke
   `display` in je eigen stijlen wint van dat attribuut.
5. **Een entiteitenlijst die uit de pas loopt met `catalog.py`.**
6. **Gedachtestreepjes** in tekst die een cursist leest.

Daar komen de proeven in `tests/kern/test_frontend.py` bovenop: de zes
stroomkleuren staan er letterlijk in, de vier basisregels staan bovenaan, er
wordt geen webfont geladen, er wordt niets van buiten gehaald, cijfers staan
stil, en `text-transform: uppercase` staat alleen op kleine labels.

**Zestien mutaties, zestien keer gevangen.** `scripts/mutatieproef.py` breekt nu
ook de frontend:

```
GEVANGEN      een accent grave in een CSS-commentaar in de frontend
GEVANGEN      een element dat buiten registratie.js geregistreerd wordt
GEVANGEN      een entiteit die de frontend kent maar de integratie niet
GEVANGEN      een stroomkleur die net iets anders is
GEVANGEN      een webfont in de frontend

Alle 16 mutaties werden gevangen.
```

---

## 3b. En wat CI erbij vond

hassfest, de controle van Home Assistant zelf, viel over het manifest, twee keer
achter elkaar:

1. **"Using component http but it's not in dependencies or after_dependencies".**
   De integratie serveert zijn eigen bundel via `homeassistant.components.http`
   en meldt hem aan via `homeassistant.components.frontend`, en dat hoort in het
   manifest te staan. De eerste reparatie zette ze als harde afhankelijkheid, en
   dat brak alle proeven met Home Assistant: het pakket `hass_frontend` staat
   niet in een proefomgeving, dus `frontend` kan daar niet opgezet worden en de
   integratie kwam niet meer van de grond. Het werd `after_dependencies`, en dat
   klopt ook beter: zonder http of frontend draaien de entiteiten en de services
   gewoon door, er is dan alleen geen eigen bundel.
2. **"Manifest keys are not sorted correctly".** Domain, name, en daarna
   alfabetisch.

Bij allebei staat nu een proef in `tests/kern/test_repo.py`, zodat het niet nog
een keer pas in CI opvalt.

---

## 4. Samenvatting

De docent zet voortaan drie regels in een leeg dashboard en heeft een compleet
scherm in de huisstijl: een kop die in één zin zegt wat er gebeurt, een rij van
zes kentallen, balken tegen de aansluitwaarde, de schuiven en schakelaars, en de
meterstanden. Alles komt uit de eigen bundel van de integratie, zonder resource
in te tikken, zonder webfont, zonder iets van buiten. De kaarten zijn in een
echte browser aangeklikt en opgemeten: `isTrusted` op elke klik, de kleuren tot
op de token, geen zijwaartse overloop op 280, 320 en 390 px, en de juiste service
aan de andere kant. Twee fouten kwamen uit die metingen: een schuif die drie keer
te veel verstuurde, en een weergavetitel die de naam van de entiteit meenam.
Beide zijn gerepareerd en opnieuw gemeten. 132 proeven groen, ook op Linux in CI met
een echte Home Assistant, en zestien mutaties tonen dat die proeven iets
bewaken.

## 5. Wat niet lukte

* **Nog niet in een echte Home Assistant gedraaid.** De kaarten en de strategie
  zijn gemeten in een browser tegen een nagemaakte `hass`, en de integratie is
  getoetst tegen een echte Home Assistant in het geheugen. Wat níet is
  aangetoond: dat Home Assistant de strategie ook echt vindt en aanroept, dat de
  bundel via `add_extra_js_url` in een echte pagina geladen wordt, en dat de
  Lovelace-resource geregistreerd wordt. Dat is de eerstvolgende ronde, op jouw
  eigen installatie.
* **Het venster liet zich niet verkleinen.** `resize_window` meldde succes maar
  `window.innerWidth` bleef 1920, en een popup werd geblokkeerd. De smalle
  metingen zijn daarom in een iframe gedaan. Dat is een echte viewport met echte
  mediaqueries, maar het is niet hetzelfde als een telefoon in de hand.
* **De iconen zijn met de hand getekend uit lijnen en bogen**, om niets te hoeven
  laden en geen licentie van een ander in het spel te brengen. Op 16px is het
  batterijtje wat mager; als je dat op het kioskscherm ziet, zeg het, dan teken ik
  hem opnieuw.
* **Geen unittests op de javascript.** De logica in de kaarten is gemeten in de
  browser en de vorm wordt bewaakt door de scripts. Een testrunner voor
  javascript zou een bouwstap en een pakketbeheerder meebrengen, en die staan er
  bewust niet.
* **De kiosk-mode module is nog steeds niet geprobeerd.**

## 6. Aannames

* **De aansluiting is standaard 3 maal 25 A bij 230 V, samen 17,25 kW.** Dat is
  de gangbare Nederlandse woningaansluiting en het is een instelling, geen
  meting. De simulatie rekent met het totaal en niet per fase; dat staat ook op
  de kaart zelf, zodat een cursist niet denkt dat er drie fasen doorgerekend
  worden.
* **Zelfbenutting is (opwek min teruglevering) gedeeld door opwek.** De batterij
  kan meer terugleveren dan er die dag is opgewekt; dan zou de breuk onder nul
  zakken en wordt hij op nul afgekapt. Zolang er niets opgewekt is geeft de
  sensor `onbekend`.
* **De strategie heet `ll-strategy-dashboard-virtual-ems`.** Dat is de naam
  waarop Home Assistant een dashboardstrategie zoekt. Verandert die afspraak,
  dan wordt de strategie niet meer gevonden; de naam staat op één plek en er
  staat een proef op.
* **`add_extra_js_url` laadt de bundel op elke pagina.** De registratie als
  Lovelace-resource gebeurt daarnaast, best effort: in YAML-modus is die lijst
  niet te bewerken en dan is er niets aan de hand.
* **De naam van de installatie komt uit het apparatenregister**, met de
  weergavenaam als terugval. Beide routes zijn gemeten.

## 7. `git status --porcelain`

```
$ git status --porcelain
(leeg)
```

De tak `ronde-2-huisstijl-strategie` telde vier commits: de strategie zelf en
drie reparaties van wat CI vond. Via PR #3 als één commit samengevoegd in `main`
en getagd als `v1.1.0`.
