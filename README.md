# Virtueel EMS

Een compleet gesimuleerd thuisenergiesysteem als Home Assistant-integratie,
gemaakt voor een domotica-practicum op mbo- en hbo-niveau.

Cursisten bedienen zonnepanelen, een thuisbatterij, een laadpaal en drie
apparaten, en zien meteen wat er op de netaansluiting gebeurt. Er is geen
hardware voor nodig, geen cloud, geen EMHASS en geen virtuele machine: een
Raspberry Pi 5 met een kale Home Assistant is genoeg.

* Geen externe pakketten. `requirements` in het manifest is leeg.
* Installeerbaar via HACS, zodat elke Pi in het lokaal dezelfde versie draait.
* Volledig in te stellen via de gebruikersomgeving, dus zonder
  `configuration.yaml` te bewerken.
* Alle teksten die een cursist ziet zijn Nederlands.

---

## Inhoud

1. [Wat er gesimuleerd wordt](#wat-er-gesimuleerd-wordt)
2. [Installeren op een verse Raspberry Pi 5](#installeren-op-een-verse-raspberry-pi-5)
3. [De dashboards installeren](#de-dashboards-installeren)
4. [Kioskschermen en het cursistaccount](#kioskschermen-en-het-cursistaccount)
5. [Het energiedashboard koppelen](#het-energiedashboard-koppelen)
6. [Overzicht van alle entiteiten](#overzicht-van-alle-entiteiten)
7. [Services voor de docent](#services-voor-de-docent)
8. [Drie oefeningen voor cursisten](#drie-oefeningen-voor-cursisten)
9. [Hoe de simulatie rekent](#hoe-de-simulatie-rekent)
10. [Proeven draaien](#proeven-draaien)

---

## Wat er gesimuleerd wordt

| Onderdeel | Wat de cursist doet | Wat er gebeurt |
| --- | --- | --- |
| Zonnepanelen | Bewolking verzetten van 0 tot 100 procent | De opbrengst volgt de echte zonnestand op jouw locatie en zakt evenredig met de bewolking |
| Thuisbatterij | Doelvermogen kiezen, van vol ontladen tot vol laden | De laadtoestand loopt op of af, met rendementsverlies, en wordt afgeknepen bij de grenzen |
| Laadpaal | Aanzetten en het laadvermogen kiezen | Het vermogen loopt in ongeveer tien seconden op naar de instelling |
| Apparaten | Wasmachine, boiler en airco aan of uit | Elk apparaat legt zijn vaste vermogen bovenop de basislast |
| Netaansluiting | Niets, dit is het gevolg | Het saldo van alles hierboven, positief bij afname en negatief bij teruglevering |

De basislast van het huis volgt een dagprofiel met een ochtendpiek en een
avondpiek, met een kleine, samenhangende schommeling eroverheen.

---

## Installeren op een verse Raspberry Pi 5

Deze stappen gaan uit van Home Assistant OS of Home Assistant Core op een
Raspberry Pi 5, bereikbaar op bijvoorbeeld `http://192.168.1.50:8123`.

### 1. HACS installeren

Staat HACS er nog niet op, volg dan de installatiehandleiding op
<https://hacs.xyz>. Bij Home Assistant OS is dat de Terminal-add-on met het
installatiescript, gevolgd door een herstart en
**Instellingen** > **Apparaten en diensten** > **Integratie toevoegen** > **HACS**.

### 2. Deze repository als aangepaste repository toevoegen

1. Open **HACS** in de zijbalk.
2. Klik rechtsboven op de drie puntjes en kies **Aangepaste repositories**.
3. Vul de URL van deze repository in en kies als categorie **Integratie**.
4. Klik op **Toevoegen**.

### 3. De integratie downloaden

1. Zoek in HACS op **Virtueel EMS** en open het.
2. Klik op **Download** en bevestig.
3. Start Home Assistant opnieuw op:
   **Instellingen** > **Systeem** > rechtsboven **Opnieuw opstarten**.

### 4. De installatie toevoegen

1. Ga naar **Instellingen** > **Apparaten en diensten** > **Integratie toevoegen**.
2. Zoek op **Virtueel EMS**.
3. Vul in:
   * **Naam van de installatie**, bijvoorbeeld `Virtueel EMS` of `Lokaal A`.
     Deze naam komt in elke entity_id terug: `Virtueel EMS` geeft
     `sensor.virtueel_ems_pv_vermogen`.
   * **Piekvermogen zonnepanelen** in kWp, standaard 4,0.
   * **Capaciteit thuisbatterij** in kWh, standaard 10,0.
   * **Maximaal laadvermogen laadpaal** in kW, standaard 11.
4. Klik op **Verzenden**. Alle entiteiten verschijnen onder één apparaat.

> Draai je meerdere lokalen op één Pi, voeg de integratie dan een tweede keer
> toe met een andere naam. Dezelfde naam twee keer kan niet, want dan zouden de
> entiteiten dezelfde entity_id krijgen.

### 5. Later bijstellen

**Instellingen** > **Apparaten en diensten** > **Virtueel EMS** > **Configureren**.
Daar staan de drie capaciteiten, plus:

* **Jaarverbruik huishouden** in kWh. Dit bepaalt de schaal van de basislast.
  De standaardwaarde van 2900 kWh is een ordegrootte, geen meting: vul hier het
  werkelijke jaarverbruik in van de woning die je in de les gebruikt.
* **Vaste starttijd van de simulatiedag**. Laat dit leeg om de echte klok te
  volgen. Vul bijvoorbeeld 11 in om elke les om 11:00 in de ochtend te
  beginnen. Dat is nuttig bij een avondles, want om 20:00 komt er anders geen
  zonnestraal aan te pas.

De integratie herlaadt zichzelf zodra je opslaat.

### 6. Het DomotiTech-thema (optioneel)

In `themes/domotitech.yaml` staat een thema in de huisstijl, met de zes
gevalideerde stroomkleuren die ook het energiedashboard gebruikt.

1. Kopieer het bestand naar `<config>/themes/domotitech.yaml`.
2. Zet in `configuration.yaml`:

   ```yaml
   frontend:
     themes: !include_dir_merge_named themes
   ```

3. Herstart Home Assistant en kies het thema bij **Profiel** > **Thema**, of
   leg het per dashboard vast bij **Instellingen** > **Dashboards**.

---

## De dashboards installeren

In `dashboards/` staan twee complete dashboards, klaar om te plakken.

Ze gaan uit van de installatienaam `Virtueel EMS`, dus van entiteiten die met
`virtueel_ems_` beginnen. Heet jouw installatie anders, draai dan eerst:

```bash
python scripts/dashboard_naam.py "Lokaal A"
```

De omgezette bestanden komen in `dashboards/uit/` te staan. Met `--toon` komen
ze op het scherm, klaar om te kopiëren.

### Het cursist-dashboard

1. **Instellingen** > **Dashboards** > **Dashboard toevoegen** > **Nieuw dashboard vanaf nul**.
2. Noem het bijvoorbeeld `Energiebeheer`, kies een icoon en klik op **Aanmaken**.
3. Open het dashboard, klik rechtsboven op het potlood, dan opnieuw rechtsboven
   op de drie puntjes en kies **Ruwe configuratie-editor**.
4. Vervang de hele inhoud door `dashboards/cursist-dashboard.yaml` en sla op.

### Het docent-dashboard

Dezelfde stappen met `dashboards/docent-dashboard.yaml`. Zet daarna bij
**Instellingen** > **Dashboards** de schakelaar **Alleen beheerder** aan voor
dit dashboard, zodat cursisten het niet in hun zijbalk zien.

---

## Kioskschermen en het cursistaccount

### 1. De kiosk-mode module installeren

1. Open **HACS**, zoek op **kiosk-mode** en download het.
   Het is een frontendmodule, dus categorie **Dashboard** of **Lovelace**.
2. Herstart Home Assistant en ververs de browser hard (Ctrl+F5).
3. Controleer bij **Instellingen** > **Dashboards** > drie puntjes >
   **Bronnen** dat `/hacsfiles/kiosk-mode/kiosk-mode.js` erbij staat. HACS zet
   die er meestal zelf in.

De instellingen zitten al bovenin `cursist-dashboard.yaml`:

```yaml
kiosk_mode:
  non_admin_settings:
    kiosk: true
  admin_settings:
    hide_header: false
    hide_sidebar: false
```

Een niet-beheerder ziet dus geen zijbalk en geen bovenbalk, en komt daarmee ook
niet bij Instellingen of bij andere dashboards. De docent, die als beheerder
inlogt, houdt de gewone omgeving. Zonder de module werkt het dashboard gewoon,
alleen blijven de balken dan staan.

### 2. Een cursistaccount aanmaken

1. **Instellingen** > **Personen** > **Persoon toevoegen**.
2. Vul een naam in, bijvoorbeeld `Cursist`.
3. Zet **Deze persoon laten inloggen** aan en vul een gebruikersnaam en
   wachtwoord in.
4. Zet **Beheerder** nadrukkelijk **uit**. Dit is de schakelaar waar alles aan
   hangt: kiosk-mode kijkt hiernaar, en zonder beheerdersrechten is Instellingen
   sowieso niet bereikbaar.
5. Zet **Alleen lokale toegang** aan als het account het lokale netwerk niet uit
   hoeft.
6. Klik op **Aanmaken**.

Herhaal dit per lokaal of per groepje, net wat je handig vindt. Eén gedeeld
cursistaccount voor alle kioskschermen werkt prima, want de schermen bedienen
dezelfde simulatie.

### 3. Het kioskscherm op het juiste dashboard laten starten

1. Zet bij **Instellingen** > **Dashboards** voor élk ander dashboard de
   schakelaar **Alleen beheerder** aan, ook voor het standaarddashboard
   **Overzicht**. Er blijft dan precies één dashboard over dat een cursist mag
   zien.
2. Log op het kioskscherm in met het cursistaccount.
3. Open het dashboard `Energiebeheer`, klik op de drie puntjes rechtsboven en
   kies **Instellen als standaard op dit apparaat**. Deze keuze zit in de
   browser van dat scherm, dus doe dit één keer per kioskscherm.
4. Zet de browser in volledig scherm (F11) en laat hem daar staan.

Cursisten gaan daarna gewoon naar `http://192.168.1.50:8123`, loggen in en
komen meteen op hun eigen scherm uit. Een eigen inlogpagina is niet nodig.

---

## Het energiedashboard koppelen

Ga naar **Instellingen** > **Dashboards** > **Energie** en klik op
**Energie configureren**. De namen hieronder gaan uit van de installatienaam
`Virtueel EMS`.

**Elektriciteitsnet**

* **Netverbruik toevoegen** > `sensor.virtueel_ems_net_afname`
* **Teruglevering toevoegen** > `sensor.virtueel_ems_net_teruglevering`

**Zonnepanelen**

* **Zonne-energie toevoegen** > `sensor.virtueel_ems_pv_opbrengst`

**Thuisbatterij**

* **Batterijsysteem toevoegen**
* Energie die de batterij in gaat: `sensor.virtueel_ems_batterij_geladen`
* Energie die de batterij uit komt: `sensor.virtueel_ems_batterij_ontladen`

**Individuele apparaten**

* `sensor.virtueel_ems_laadpaal_verbruik`
* `sensor.virtueel_ems_wasmachine_verbruik`
* `sensor.virtueel_ems_boiler_verbruik`
* `sensor.virtueel_ems_airco_verbruik`

Twee dingen om te weten:

* Voeg `sensor.virtueel_ems_verbruik_totaal` **niet** toe. Die teller is voor
  het overzicht op het docent-dashboard; in het energiedashboard zou hij dubbel
  tellen met de apparaten.
* Het energiedashboard rekent per klokuur en gebruikt de langetermijnstatistiek.
  Reken op ongeveer een uur echte tijd voordat de eerste staaf staat. Zet de
  tijdversnelling hoger dan 1, dan gaat de gesimuleerde dag sneller, maar het
  energiedashboard blijft de echte klok volgen. Voor een les binnen één uur is
  het cursist-dashboard daarom sneller in beeld dan het energiedashboard.

---

## Overzicht van alle entiteiten

De voorvoegsels hieronder gaan uit van de naam `Virtueel EMS`.

### Zonnepanelen

| Entiteit | Eenheid | Wat het is |
| --- | --- | --- |
| `sensor.virtueel_ems_pv_vermogen` | W | Actueel vermogen van de panelen |
| `sensor.virtueel_ems_pv_opbrengst` | kWh | Cumulatieve opbrengst, voor het energiedashboard |
| `number.virtueel_ems_pv_bewolking` | % | Bewolking, door de cursist in te stellen |

### Thuisbatterij

| Entiteit | Eenheid | Wat het is |
| --- | --- | --- |
| `sensor.virtueel_ems_batterij_soc` | % | Laadtoestand |
| `sensor.virtueel_ems_batterij_inhoud` | kWh | Wat er nu in zit |
| `sensor.virtueel_ems_batterij_vermogen_actueel` | W | Wat de batterij werkelijk doet, na afknijpen |
| `sensor.virtueel_ems_batterij_geladen` | kWh | Cumulatief geladen |
| `sensor.virtueel_ems_batterij_ontladen` | kWh | Cumulatief ontladen |
| `number.virtueel_ems_batterij_vermogen` | W | Doelvermogen, negatief is ontladen |
| `number.virtueel_ems_batterij_min_soc` | % | Ondergrens, hieronder wordt niet ontladen |
| `number.virtueel_ems_batterij_max_soc` | % | Bovengrens, hierboven wordt niet geladen |

Let op het verschil tussen `number.virtueel_ems_batterij_vermogen` (wat de
cursist vraagt) en `sensor.virtueel_ems_batterij_vermogen_actueel` (wat de
batterij levert). Zodra een grens in zicht komt lopen die twee uiteen, en juist
dat verschil is de les.

### Laadpaal

| Entiteit | Eenheid | Wat het is |
| --- | --- | --- |
| `switch.virtueel_ems_laadpaal_actief` | | Auto aan de lader |
| `number.virtueel_ems_laadpaal_vermogen` | W | Ingesteld laadvermogen |
| `sensor.virtueel_ems_laadpaal_vermogen` | W | Werkelijk vermogen, met oploop |
| `sensor.virtueel_ems_laadpaal_verbruik` | kWh | Cumulatief in de auto geladen |

### Huishoudelijk verbruik

| Entiteit | Eenheid | Wat het is |
| --- | --- | --- |
| `sensor.virtueel_ems_huishoudelijk_verbruik` | W | Basislast plus de apparaten die aan staan |
| `sensor.virtueel_ems_verbruik_totaal` | kWh | Cumulatief huishoudelijk verbruik, zonder de laadpaal |
| `switch.virtueel_ems_wasmachine` | | 2000 W zolang hij aan staat |
| `switch.virtueel_ems_boiler` | | 2500 W zolang hij aan staat |
| `switch.virtueel_ems_airco` | | 1200 W zolang hij aan staat |
| `sensor.virtueel_ems_wasmachine_verbruik` | kWh | Cumulatief, voor de sectie Apparaten |
| `sensor.virtueel_ems_boiler_verbruik` | kWh | Cumulatief, voor de sectie Apparaten |
| `sensor.virtueel_ems_airco_verbruik` | kWh | Cumulatief, voor de sectie Apparaten |

### Netaansluiting

| Entiteit | Eenheid | Wat het is |
| --- | --- | --- |
| `sensor.virtueel_ems_net_vermogen` | W | Saldo. Positief is afname, negatief is teruglevering |
| `sensor.virtueel_ems_net_afname` | kWh | Alleen het positieve deel, cumulatief |
| `sensor.virtueel_ems_net_teruglevering` | kWh | Alleen het negatieve deel, cumulatief |

### Simulatie

| Entiteit | Eenheid | Wat het is |
| --- | --- | --- |
| `number.virtueel_ems_tijdversnelling` | | 1 tot 60 keer zo snel als de echte klok |
| `sensor.virtueel_ems_simulatietijd` | | Het gesimuleerde tijdstip |
| `sensor.virtueel_ems_zonnehoogte` | ° | Hoogte van de zon boven de horizon |

De laatste twee zijn diagnose-entiteiten en staan daarom niet op het
cursist-dashboard.

---

## Services voor de docent

Beide services zijn ook los aan te roepen via
**Ontwikkelaarstools** > **Acties**.

### `virtual_ems.set_scenario`

Zet in één handeling een complete lessituatie klaar: bewolking, batterijstand,
laadpaal, apparaten en het tijdstip van de gesimuleerde dag. De kWh-tellers
blijven staan.

| Scenario | Wat het klaarzet |
| --- | --- |
| `zonnige_dag` | 12:00, geen bewolking, batterij op 30 procent, alles uit |
| `bewolkte_dag` | 12:00, 85 procent bewolking, batterij op 50 procent |
| `piekbelasting_avond` | 19:00, laadpaal op 11 kW, wasmachine en boiler aan, batterij op 70 procent |
| `lege_batterij` | 09:00, 20 procent bewolking, batterij op 5 procent, ondergrens op 0 |

Elk scenario zet de tijdversnelling op 10, zodat er in een lesuur ongeveer tien
uur gesimuleerde tijd voorbijgaat.

### `virtual_ems.reset`

Zet alle cumulatieve kWh-tellers op nul en de batterij terug op 50 procent.
Met het vinkje **Alleen de tellers** blijven de schuiven en schakelaars staan
zoals ze stonden; zonder dat vinkje gaat ook de bediening terug naar de
beginstand.

Beide services werken op alle installaties die op deze Pi draaien.

---

## Drie oefeningen voor cursisten

### Oefening 1: laad de auto zonder het net te belasten

**Klaarzetten:** docent draait `zonnige_dag`.

De auto moet geladen worden, maar de netafname moet zo klein mogelijk blijven.

1. Kijk eerst wat de panelen leveren en wat het huis vraagt.
2. Zet de laadpaal aan en schuif het laadvermogen omhoog tot
   `sensor.virtueel_ems_net_vermogen` net niet positief wordt.
3. Laat daarna de batterij meehelpen: zet
   `number.virtueel_ems_batterij_vermogen` negatief, dus op ontladen.
4. Hoeveel kun je nu laden voordat het net eraan te pas komt?
5. Schuif de bewolking langzaam omhoog en houd de netafname op nul. Wat moet je
   bijstellen, en wanneer lukt het niet meer?

**Wat je hier ziet:** de zon, de batterij en de auto zijn drie knoppen op één
balans. Het net is het restant, niet iets wat je zelf instelt.

### Oefening 2: houd de batterij boven 20 procent

**Klaarzetten:** docent draait `piekbelasting_avond`.

Het is avond, de auto laadt op 11 kW en er staan twee zware apparaten aan. De
batterij mag niet onder 20 procent komen.

1. Zet `number.virtueel_ems_batterij_min_soc` op 20.
2. Zet de batterij vol op ontladen en kijk naar
   `sensor.virtueel_ems_batterij_vermogen_actueel`.
3. Volg de laadtoestand. Wat gebeurt er met het werkelijke vermogen zodra de
   batterij de 20 procent nadert, en wat doet de netafname op dat moment?
4. Zorg dat de wasmachine en de auto toch allebei klaarkomen. Welke van de twee
   zet je tijdelijk uit, en waarom die?

**Wat je hier ziet:** een grens in een EMS is geen noodstop maar een
begrenzing. Het systeem knijpt het vermogen geleidelijk af, en dat gat valt
onmiddellijk op de netaansluiting.

### Oefening 3: haal de dag door op eigen opslag

**Klaarzetten:** docent draait `lege_batterij` en daarna `virtual_ems.reset`
met **Alleen de tellers** aan, zodat de tellers op nul staan.

Het is ochtend en de batterij is zo goed als leeg. Doel: aan het eind van de
gesimuleerde dag zo min mogelijk op `sensor.virtueel_ems_net_afname`.

1. Laad de batterij overdag met de overtollige zon. Let op: laden kost meer dan
   je er later uit haalt, want het rendement is 90 procent over een hele cyclus.
2. Zet de boiler op het moment dat de panelen het meeste leveren, niet in de
   avond.
3. Laat de batterij in de avondpiek ontladen.
4. Vergelijk aan het eind `net_afname` met `net_teruglevering` en met
   `pv_opbrengst`. Hoeveel van je eigen zon heb je zelf gebruikt?

**Wat je hier ziet:** verschuiven in de tijd is waar een EMS voor bestaat. En
opslaan kost energie, dus rechtstreeks gebruiken is altijd beter dan de omweg
via de batterij.

---

## Hoe de simulatie rekent

De rekenkern staat in `custom_components/virtual_ems/simulation.py` en bevat
geen enkele Home Assistant-import. Daardoor is een hele dag door te rekenen in
een gewone unittest, zonder Home Assistant erbij. Alle koppeling met Home
Assistant zit in `coordinator.py` en in de platformbestanden.

**Zonnestand.** De hoogte en de azimut van de zon volgen de rekenwijze van de
NOAA Solar Calculator, met de Fourierbenadering van Spencer (1971) voor de
declinatie en de tijdsvereffening. De breedtegraad en de lengtegraad komen uit
de instellingen van Home Assistant, dus de simulatie klopt met jouw locatie.

**Straling.** De luchtmassa volgt Kasten en Young (1989), de directe straling
bij heldere hemel volgt Meinel en Meinel (1976):
`I = 1353 * 0,7^(AM^0,678)` W/m². De straling op het hellend vlak komt uit het
isotrope model van Liu en Jordan (1960), met een paneelhelling van 35 graden
pal zuid.

**Opbrengst.** `kWp * straling / 1000 * prestatieverhouding`, met een
prestatieverhouding van 0,85 voor omvormer-, temperatuur- en kabelverlies.
Daarna gaat de bewolking er evenredig af, zoals in de opdracht gevraagd:
50 procent bewolking is precies de helft.

**Batterij.** Het maximale vermogen is 0,5 C, dus 5 kW op een batterij van
10 kWh. Het rendement is 90 procent over een hele cyclus, verdeeld als de
wortel daarvan over laden en ontladen. Zodra een SoC-grens in zicht komt wordt
het vermogen precies zo ver afgeknepen dat de grens geraakt maar niet gepasseerd
wordt.

**Huishouden.** Een uurprofiel met een ochtend- en een avondpiek, genormaliseerd
op gemiddeld 1,0 en geschaald met het ingestelde jaarverbruik, plus een
Ornstein-Uhlenbeck-ruis met een tijdconstante van vijf minuten.

**Netaansluiting.** `net = huis + laadpaal + batterij - zon`, met de batterij
positief bij laden. Er is dus geen aparte instelling voor het net: het is het
restant, en dat is precies wat een EMS probeert te sturen.

**Wat een instelling is en wat een meting.** Er staan geen verzonnen kentallen
in de code. De natuurkundige constanten hebben een bron, de systeemgrootte komt
uit de config flow, en de vormparameters (het uurprofiel, de oplooptijd van de
laadpaal, de ruis) staan met naam en toelichting bovenin het bestand, zodat een
docent ze kan aanpassen. Het standaard jaarverbruik van 2900 kWh is bewust een
instelling en geen kental: vul het echte getal in.

---

## Proeven draaien

De proeven zijn in tweeën gedeeld.

**Kernproeven**, zonder Home Assistant, dus overal te draaien:

```bash
python -m pip install pytest PyYAML tzdata
python -m pytest tests/kern
```

Die rekenen een hele gesimuleerde dag door, controleren de energiebalans, en
bewaken dat de dashboards, de vertalingen en het manifest bij de code passen.
`tzdata` is alleen op Windows nodig: de proeven rekenen met Europe/Amsterdam,
juist om zomertijd en wintertijd mee te nemen, en Windows levert zelf geen
tijdzonedatabase.

`tests/kern/kernlader.py` laadt de rekenkern zonder het Home Assistant-pakket
eromheen. Daarmee is het niet alleen een belofte dat `simulation.py`,
`scenarios.py`, `catalog.py` en `const.py` los te draaien zijn: zodra daar een
Home Assistant-import binnensluipt vallen alle kernproeven meteen om.

**Alle proeven**, met een echte Home Assistant in het geheugen:

```bash
python -m pip install -r requirements-test.txt
python -m pytest
```

Op Windows draait Home Assistant niet uit zichzelf: `homeassistant/runner.py`
importeert de POSIX-modules `fcntl` en `resource`. Daar staat `windows_shim.py`
voor klaar, dat die twee vervangt en de wekkerpijp van de asyncio-lus door het
socketslot laat:

```bash
python -m pytest -p windows_shim
```

Dat hulpstuk hoort bij het harnas en raakt de integratie niet.

**Bewijzen dat de proeven iets bewaken.** `scripts/mutatieproef.py` breekt
telkens één ding (de azimut, de SoC-grens, het teken van de zon in de
netformule, een tikfout in een entity_id op een dashboard) en verwacht dat de
bijbehorende proef rood wordt:

```bash
python scripts/mutatieproef.py
python scripts/mutatieproef.py --pytest-arg=-p --pytest-arg=windows_shim   # Windows
```

In `.github/workflows/proeven.yml` hangen alle proeven, hassfest en de
HACS-controle aan elke duw en elk verzoek tot samenvoegen.
