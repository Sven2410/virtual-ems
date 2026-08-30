# Ronde 1: virtual_ems, een virtueel EMS voor het practicum

Datum: 30 augustus 2026
Tak: `ronde-1-virtueel-ems`, samengevoegd in `main`, uitgave `v1.0.0`

---

## 1. Wat er staat

Een complete HACS-custom-repository met vier onderdelen.

**De integratie** in `custom_components/virtual_ems/`, opgesplitst in een
rekenkern en de bedrading eromheen:

| Bestand | Wat het doet | Kent Home Assistant |
| --- | --- | --- |
| `simulation.py` | Zonnestand, straling, PV, batterij, laadpaal, huis, net | nee |
| `scenarios.py` | De vier lessituaties | nee |
| `catalog.py` | De lijst van alle entiteiten, plus de naam-naar-slug | nee |
| `const.py` | Instellingen, apparaten, profielvorm | nee |
| `coordinator.py` | De update-lus, de simulatieklok, de opslag | ja |
| `config_flow.py` | Installatiedialoog en optiesdialoog | ja |
| `sensor.py`, `number.py`, `switch.py`, `entity.py` | De entiteiten | ja |

De rekenkern draait dus zonder Home Assistant, en dat is precies waarom er een
hele gesimuleerde dag tegenaan te draaien valt voordat er iets geschakeld wordt.

**29 entiteiten** onder één apparaat: 19 sensoren, 6 instelbare waarden en
4 schakelaars. Onder die 19 zit per virtueel apparaat een eigen kWh-teller, voor
de sectie Apparaten van het energiedashboard. De volledige tabel staat in de
README.

**Twee services**, `virtual_ems.set_scenario` met vier scenario's en
`virtual_ems.reset`, allebei met Nederlandse teksten in `services.yaml` én in
de vertalingen.

**Twee complete dashboards** in `dashboards/`, klaar om in de ruwe
configuratie-editor te plakken. Het cursist-dashboard heeft het
`kiosk_mode`-blok al aan boord; het docent-dashboard nadrukkelijk niet.

**Een thema** in `themes/domotitech.yaml` met de tokens uit `theme.js`,
inclusief de zes stroomkleuren op de energiedashboard-variabelen en op de
benoemde tegelkleuren.

**Een handleiding** in `README.md`: installatie via HACS op een verse Pi 5,
kiosk-mode, het cursistaccount, het energiedashboard, het entiteitenoverzicht en
drie uitgewerkte oefeningen.

---

## 2. Het bewijs

### 2.1 Alle proeven groen

```
$ python -m pytest -p windows_shim --no-header
........................................................................ [ 72%]
...........................                                              [100%]
99 passed in 3.14s
```

Verdeeld over:

* `tests/kern/` (78 proeven): rekenkern, scenario's, dashboardbewaker,
  verpakkingsbewaker. Draait zonder Home Assistant, dus overal.
* `tests/ha/` (21 proeven): config flow, optiesdialoog, entiteiten, services,
  opslag over een herstart heen. Draait met een echte Home Assistant in het
  geheugen (2026.9.0b3, de versie die
  `pytest-homeassistant-custom-component` vastpint).

De gevraagde controles zitten er allemaal in:

| Gevraagd | Proef |
| --- | --- |
| SoC nooit buiten 0 tot 100 | `test_soc_blijft_altijd_tussen_nul_en_honderd` (een hele dag met willekeurige bediening, elke minuut gecontroleerd) |
| net_vermogen klopt als optelsom | `test_net_vermogen_is_de_optelsom_van_alle_stromen` en `test_de_netsensor_is_de_optelsom_van_de_andere_sensoren` (in echte HA) |
| reset zet de tellers terug | `test_reset_zet_de_tellers_en_de_soc_terug` en `test_de_service_zet_de_tellers_terug` |
| config flow | `tests/ha/test_config_flow.py`, vijf proeven |

Daarbovenop staat er een energiebalansproef over een hele gesimuleerde dag:
`afname - teruglevering` moet exact gelijk zijn aan
`huis + laadpaal + laden - ontladen - zon`, tot op 1e-6 kWh.

### 2.2 De proeven zijn onderscheidend

Een proef die altijd groen is bewijst niets. `scripts/mutatieproef.py` breekt
telkens één ding en verwacht dat de bijbehorende proef valt:

```
$ python scripts/mutatieproef.py --pytest-arg=-p --pytest-arg=windows_shim
GEVANGEN      azimut via een enkele acos (de fout die op 21 juni de zon in het noorden zette)
              FAILED tests/kern/test_simulation.py::test_zon_staat_s_ochtends_in_het_oosten_en_s_avonds_in_het_westen
              De zonnehoogte blijft kloppen, dus een schermafdruk verraadt dit niet.
GEVANGEN      batterij laadt zonder te kijken hoeveel er nog in past
              FAILED tests/kern/test_simulation.py::test_batterij_laadt_niet_boven_de_ingestelde_bovengrens
GEVANGEN      batterij ontlaadt zonder ondergrens
              FAILED tests/kern/test_simulation.py::test_batterij_ontlaadt_niet_onder_de_ingestelde_ondergrens
GEVANGEN      netvermogen telt de zon erbij op in plaats van eraf
              FAILED tests/kern/test_simulation.py::test_teruglevering_krijgt_een_negatief_netvermogen
GEVANGEN      terugzetten laat de tellers staan
              FAILED tests/kern/test_simulation.py::test_reset_met_alleen_tellers_laat_de_bediening_staan
GEVANGEN      laadpaal springt in een stap naar zijn eindvermogen
              FAILED tests/kern/test_simulation.py::test_laadpaal_loopt_op_in_plaats_van_te_springen
GEVANGEN      bewolking werkt niet meer door in de opbrengst
              FAILED tests/kern/test_scenarios.py::test_bewolkte_dag_levert_veel_minder_dan_een_zonnige_dag
GEVANGEN      een tikfout in een entity_id op het cursist-dashboard
              FAILED tests/kern/test_dashboards.py::test_elke_entiteit_op_het_dashboard_bestaat_ook_echt[cursist-dashboard.yaml]
              Home Assistant meldt zoiets niet; de kaart wordt gewoon grijs.
GEVANGEN      een scenarioknop die naar een niet-bestaand scenario wijst
              FAILED tests/kern/test_dashboards.py::test_alle_scenarios_staan_op_het_docentdashboard
GEVANGEN      een ontbrekende Nederlandse naam voor een entiteit
              FAILED tests/kern/test_repo.py::test_beide_talen_hebben_dezelfde_sleutels
GEVANGEN      een entiteit die wel bestaat maar niet in de catalogus staat
              FAILED tests/ha/test_entiteiten.py::test_alle_entiteiten_uit_de_catalogus_bestaan_ook_echt

Alle 11 mutaties werden gevangen.
```

Het script zet elk bestand daarna weer terug; na afloop is `git status` schoon.

### 2.3 Een echte fout, gevonden door een proef

`test_zon_staat_op_zijn_hoogst_pal_in_het_zuiden` was bij de eerste run rood:

```
>       assert azimut == pytest.approx(180.0, abs=1.0)
E       assert 359.8916935053236 == 180.0 +- 1
```

Op het hoogste punt van 21 juni gaf de azimut 359,9 graden, dus pal noord. De
oorzaak zat in de NOAA-formule met één `acos`: die mist een minteken in de
teller, en geeft bovendien 's ochtends en 's avonds dezelfde uitkomst. De
zonnehoogte klopte wel, dus een schermafdruk van de PV-curve had dit nooit
verraden, terwijl de fout wel degelijk doorwerkte: de azimut gaat via de
invalshoek rechtstreeks in de opbrengst van het hellend paneelvlak.

De reparatie rekent de azimut uit de oost- en noordcomponent van de
zonnevector met `atan2`, waardoor elk kwadrant vanzelf klopt. Er staat nu een
tweede proef bij die de ochtend en de avond apart controleert, want de
middagproef alleen zou de acos-versie op een halve dag niet betrappen. De
mutatieproef hierboven draait precies die oude code terug en toont dat beide
proeven dan vallen.

### 2.4 De entity_id's zijn wat de opdracht vroeg

Uit het opzetlog van de proef met installatienaam `Lokaal A`:

```
Registered new sensor.virtual_ems entity: sensor.lokaal_a_pv_vermogen
Registered new sensor.virtual_ems entity: sensor.lokaal_a_pv_opbrengst
Registered new sensor.virtual_ems entity: sensor.lokaal_a_batterij_soc
...
Registered new switch.virtual_ems entity: switch.lokaal_a_wasmachine
```

Dat is geen toeval: de entity_id wordt in `entity.py` vastgelegd op
`<naam>_<sleutel>`. Zouden we dat aan Home Assistant overlaten, dan leidt hij
hem af uit de vertaalde naam, en dan heet dezelfde sensor op een Engelstalige
installatie `sensor.lokaal_a_pv_power` en wijzen de dashboards naar niets. In
het log hierboven staat de weergavenaam ook echt als `Lokaal A Grid import`,
want die proef draait in het Engels: het bewijs dat de vastlegging nodig was.

### 2.5 Automatische bewakers, niet goede voornemens

Drie fouten die een script kan vangen hangen nu aan de proefronde en aan CI, en
niet aan of iemand eraan denkt:

1. **Dashboard tegen werkelijkheid.** `tests/kern/test_dashboards.py` haalt elke
   `entity` uit beide dashboards en legt hem naast `catalog.py`. Een tikfout in
   een entity_id levert in Home Assistant geen fout en geen logregel op, alleen
   een grijze kaart midden in de les.
2. **Catalogus tegen werkelijkheid.** Die catalogus mag zelf niet gaan liegen,
   dus `tests/ha/test_entiteiten.py` zet de integratie echt op en vergelijkt de
   aangemaakte entiteiten één op één met de catalogus.
3. **Verpakking tegen code.** `tests/kern/test_repo.py` controleert manifest,
   hacs.json, beide vertalingen (compleet, gelijk van structuur, en gelijk aan
   `strings.json`), de scenariolijst in `services.yaml`, en dat er geen
   gedachtestreepjes in de Nederlandse teksten staan.

In `.github/workflows/proeven.yml` draaien daarnaast hassfest en de
HACS-controle bij elke duw en elk verzoek tot samenvoegen.

---

## 3. Beslissingen die uitleg verdienen

**De simulatieklok is niet de wandklok.** De opdracht vraagt om een dagcurve op
systeemtijd, maar bij een avondles is de zon dan al uren onder en gebeurt er
niets. Er is daarom `number.<naam>_tijdversnelling` (1 tot 60 keer) en een
optionele vaste starttijd van de simulatiedag. Staat de versnelling op 1 en de
starttijd leeg, dan is de simulatietijd exact de systeemtijd, precies zoals
gevraagd. Elk scenario zet de versnelling op 10 en de dag op het uur dat bij de
lessituatie hoort.

**Er staat een sensor naast de schuif voor het batterijvermogen.**
`number.<naam>_batterij_vermogen` is wat de cursist vráágt,
`sensor.<naam>_batterij_vermogen_actueel` is wat de batterij dóét. Zodra een
grens in zicht komt lopen die twee uiteen, en dat verschil is de kern van
oefening 2.

**`verbruik_totaal` telt de laadpaal niet mee.** In het energiedashboard staat
de laadpaal onder Individuele apparaten; zou de totaalteller hem meenemen, dan
telt hij dubbel. De teller volgt daarom precies wat
`sensor.<naam>_huishoudelijk_verbruik` levert: basislast plus apparaten.

**Kleurtoedeling.** De zes stroomkleuren zijn onaangeroerd overgenomen. Er zijn
alleen zeven stromen te benoemen (zon, huis, netafname, teruglevering, laadpaal,
batterij laden, batterij ontladen) en zes kleuren. De toedeling is: zon
`--solar`, huis `--house`, netafname `--grid-in`, teruglevering `--grid-out`,
laadpaal `--device-1`, batterij `--device-2`. In het energiedashboard staan
laden en ontladen naast elkaar in één grafiek en moeten ze uit elkaar te houden
zijn; daar krijgt laden `--device-2` en ontladen `--device-1`. Dat is de enige
plek waar een kleur dubbel dienst doet, en elke stroom draagt daar hoe dan ook
een eigen icoon en een geschreven label.

**Elk getal komt ergens vandaan.** De zonnestand volgt NOAA en Spencer (1971),
de luchtmassa Kasten en Young (1989), de heldere-hemelstraling Meinel en Meinel
(1976), het hellend vlak Liu en Jordan (1960). Alle bronnen staan bovenin
`simulation.py`. Wat geen natuurkundige constante is, is een instelling met een
naam: systeemgrootte uit de config flow, prestatieverhouding, C-rate,
retourrendement, paneelhelling, oplooptijd en ruisparameters als benoemde
velden in `PlantConfig`. Het uurprofiel van de basislast staat als vorm in
`const.py`, met de opmerking erbij dat de vorm een didactische keuze is en de
schaal uit het ingestelde jaarverbruik komt.

---

## 4. Samenvatting

Er staat een werkende, via HACS installeerbare Home Assistant-integratie die een
compleet thuisenergiesysteem simuleert: zonnepanelen op de echte zonnestand van
de opgegeven locatie, een thuisbatterij met C-rate, SoC-grenzen en
retourrendement, een laadpaal met oploop, een huishouden met dagprofiel en drie
schakelbare apparaten, en een netaansluiting die het restant is. Alles is via de
gebruikersomgeving in te stellen, alle teksten zijn Nederlands, en er zijn twee
kant-en-klare dashboards, een thema in de huisstijl, en een handleiding met drie
uitgewerkte oefeningen. 99 proeven zijn groen, en 11 mutaties tonen dat die
proeven ook echt iets bewaken. Onderweg vond de zonnestandproef een fout in de
azimutberekening die op het scherm niet te zien zou zijn geweest.

## 5. Wat niet lukte

* **Niet op een echte Raspberry Pi met echte Home Assistant gedraaid.** Er staat
  hier geen Pi en geen draaiende Home Assistant. De integratie is getoetst tegen
  een echte Home Assistant in het geheugen (2026.9.0b3): opzetten, entiteiten,
  bediening, services, opties, herstart. Wat dus níet is aangetoond: dat HACS de
  repository accepteert, en dat de installatie op HAOS op een Pi 5 zonder
  hobbels verloopt.
* **De dashboards zijn niet in een browser bekeken.** Wat wel getoetst is: dat
  het geldige YAML is, dat elke entiteit die erin staat ook echt bestaat, dat
  elke serviceaanroep bestaat en elk scenario klopt. Wat niet getoetst is: hoe
  het eruitziet, of de tegels met een `numeric-input`-feature op de HA-versie op
  de Pi al bestaan, en of de kaart `energy-distribution` het doet. Dat is een
  ronde waarin je een HA-instantie draait, en die is er nu niet.
* **kiosk-mode is niet geïnstalleerd of geprobeerd.** Dat is een externe
  HACS-module. De configuratie staat in het dashboard en in de README volgens de
  documentatie van die module, maar ik heb hem niet aan het werk gezien.
* **Het energiedashboard is niet daadwerkelijk gekoppeld.** De proeven
  controleren wél dat alle tien de kWh-sensoren `device_class: energy`,
  `state_class: total_increasing` en eenheid kWh hebben, wat de eis van het
  energiedashboard is. Het doorklikken van het stappenplan zelf staat open.
* **Geen PR.** Er is geen remote: de repository is hier aangemaakt. De tak is
  lokaal samengevoegd met `--no-ff` en getagd. Zeg het even als je wilt dat ik
  een GitHub-repository aanmaak en er een PR van maak; dat is een handeling naar
  buiten, dus daar wacht ik je akkoord op.
* **Docker Desktop wilde niet starten** toen ik een Linux-omgeving voor de
  HA-proeven zocht. Dat bleek niet nodig: `windows_shim.py` vervangt de twee
  POSIX-modules die Home Assistant op modulehoogte importeert, en daarmee
  draaien de HA-proeven gewoon op Windows.

## 6. Aannames

* **De repository-URL in `manifest.json`** staat op
  `https://github.com/Sven2410/virtual-ems`. Die repository bestaat nog niet.
  Pas hem aan zodra je weet waar hij komt te staan, want HACS toont hem als
  documentatielink.
* **Standaard jaarverbruik 2900 kWh.** Bewust een instelling met een
  ordegrootte-default, geen kental. In de optiesdialoog en in de README staat er
  expliciet bij dat het echte jaarverbruik ingevuld hoort te worden.
* **Vormparameters van de simulatie**, allemaal als benoemd veld aanpasbaar:
  prestatieverhouding 0,85, C-rate 0,5, retourrendement 0,90, paneelhelling 35
  graden pal zuid, albedo 0,20, diffuus aandeel 0,10, oplooptijd laadpaal 10 s,
  ruis met tijdconstante 300 s en 15 procent spreiding. De vorm van het
  uurprofiel is een didactische keuze en staat als zodanig gedocumenteerd.
* **Minimaal Home Assistant 2025.1.0** in `hacs.json`. De integratie gebruikt
  `entry.runtime_data` en geeft de config entry expliciet aan de coordinator
  mee; beide bestaan vanaf ruim voor die versie. Onder 2025.1 is niet getoetst.
* **De menuteksten in de README** (bijvoorbeeld "Instellen als standaard op dit
  apparaat") komen uit de Nederlandse vertaling van Home Assistant en kunnen per
  versie iets anders luiden. De route klopt, de exacte woorden kunnen schuiven.
* **De standaarddashboardkeuze zit per browser, niet per gebruiker.** De README
  beschrijft daarom de route die wél waterdicht is: alle andere dashboards op
  "Alleen beheerder" zetten, en op het kioskscherm eenmalig het cursistdashboard
  als standaard instellen.

## 7. `git status --porcelain`

```
$ git status --porcelain
(leeg)
```

Alles zit in één commit op `ronde-1-virtueel-ems`, samengevoegd in `main` met
`--no-ff` en getagd als `v1.0.0`.
