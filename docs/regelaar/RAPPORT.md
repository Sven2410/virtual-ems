# Ronde 3: er zit nu een systeem in het energiemanagementsysteem

Datum: 30 augustus 2026
Repository: <https://github.com/Sven2410/virtual-ems>
Tak: `ronde-3-de-regelaar`

---

## 1. Je had gelijk

De vraag was: wat is hier EMS aan, wat wordt er gestuurd, en waarom wordt er
niets teruggerekend als de belastbaarheid boven de honderd procent komt.

Het antwoord op alle drie was hetzelfde: er zat geen regelaar in. Wat er stond
was de installatie, niet het systeem. Elk setpoint kwam van de hand van de
cursist, er zat niets tussen dat besliste, en een overbelaste aansluiting had
geen enkel gevolg. Een percentage boven de honderd was een getal op een scherm
en verder niets.

Deze ronde zit er wel een systeem in.

---

## 2. Wat er nu gebeurt

### 2.1 Er is een regelaar, en die beslist elke ronde opnieuw

`regelaar.py` draait elke vijf seconden, vóór de natuurkunde:

1. kijk wat de zon levert, wat het huis vraagt en wat de laadpaal wil,
2. bepaal aan de hand van de **regelmodus** wat de batterij moet doen,
3. leg daar het **vangnet** overheen: past dit binnen de aansluiting,
4. schrijf op wat er besloten is en waarom.

Pas daarna komt de natuurkunde: de batterij kan niet meer geven dan erin zit en
de laadpaal loopt in tien seconden op. Het verschil tussen
`sensor.<naam>_batterij_opdracht` en `sensor.<naam>_batterij_vermogen_actueel` is
nu zichtbaar, en dat verschil is precies waar het over gaat.

### 2.2 Drie standen om te vergelijken

| Stand | Waar hij op stuurt |
| --- | --- |
| Handmatig | Nergens op. Zo merkt een cursist hoe lastig het met de hand is. |
| Zelfconsumptie | Zo min mogelijk over de meter. |
| Piekscheren | De afname onder een grens houden die de docent instelt. |

Gemeten over dezelfde gesimuleerde avond, met dezelfde beginstand:

```
handmatig    hoogste piek 3,31 kW
piekscheren  hoogste piek 2,00 kW   (grens stond op 2,00 kW)
```

Dat is `test_piekscheren_verlaagt_de_hoogste_piek_werkelijk`, en die proef valt
zodra de regelaar zijn werk niet meer doet.

### 2.3 Het vangnet regelt terug, in een volgorde die uitlegbaar is

`switch.<naam>_aansluitbewaking` staat standaard aan en werkt in elke stand:

1. **het laden van de batterij** gaat als eerste weg, dat kan wachten,
2. **de laadpaal** wordt teruggeregeld, een auto laadt gewoon langzamer,
3. **de batterij springt bij** en ontlaadt om het net te ontlasten,
4. lukt het dan nog niet, dan **zegt hij dat**: een wasmachine kun je niet
   halverwege afknijpen.

Precies jouw scenario, alle schuiven omhoog en alle apparaten aan, nagerekend:

```
zonder vangnet:  22,27 kW gevraagd op een aansluiting van 17,25 kW  =  129 procent
met vangnet:     17,25 kW, precies vol, en op het scherm staat waarom:
                 "Het laden van de batterij is 4,78 kW teruggeregeld voor de aansluiting."
                 "De laadpaal is teruggeregeld van 11,00 naar 10,98 kW om binnen de
                  aansluiting te blijven."
```

Bij te veel teruglevering gaat het andersom: eerst de batterij vullen, en pas als
laatste de omvormer terugregelen, want die opbrengst ben je kwijt.

### 2.4 En als je het vangnet uitzet, smelt de zekering

`zekering.py` is een warmtemodel dat geijkt is op IEC 60269-1 voor een
gG-smeltveiligheid tot en met 63 A: bij 1,25 keer de nominale stroom smelt hij
binnen de conventionele tijd van een uur niet, bij 1,6 keer wel. Nagemeten:

```
1,00 In gedurende vier uur   niet gesmolten, warmte 0
1,25 In gedurende een uur    niet gesmolten
1,60 In                      gesmolten na 3600 s, binnen 2 procent van het ijkpunt
1,80 / 2,50 / 4,00 In        steeds sneller, in die volgorde
```

Smelt hij door, dan staat er geen spanning meer op de installatie: de panelen
leveren niets, de batterij doet niets, de laadpaal stopt en geen enkele teller
loopt. Alleen de docent kan hem vervangen.

**Wat dit model niet is**, en dat staat ook in het bestand zelf: bij een zware
overbelasting is een echte zekering veel sneller dan dit model. Bij vijf keer de
nominale stroom smelt een echte in de orde van seconden en dit model in minuten.
Voor het practicum gaat het om het principe, en wie een selectiviteitsberekening
wil doen heeft de curve van de fabrikant nodig.

**Met 3 maal 25 A krijg je hem niet stuk, en dat klopt.** Alles aan is 22 kW op
17,25 kW, dus 1,3 keer de nominale stroom, en dat houdt een echte zekering uren
vol. Wie hem wil zien smelten zet de aansluiting op 1 fase van 25 A; dan is
dezelfde belasting bijna vier keer de nominale stroom en is het binnen een paar
minuten gesimuleerde tijd voorbij. Dat staat als oefening 3 in de README, met de
uitleg erbij dat dit een echte les over aansluitwaarde is.

### 2.5 Op het scherm

De kop van het dashboard zegt nu niet alleen wat er gebeurt maar ook wat het
systeem besloot en waarom, in een eigen blok met de accentkleur. Ligt de zekering
eruit, dan wordt dat blok rood en zegt de kop dat er geen spanning meer staat, in
plaats van overal nullen te tonen.

Daaronder staat een nieuwe kaart, `virtual-ems-regelaar`: de drie standen als
knoppen, de piekgrens, het vangnet, de warmte van de zekering met de tijd die hij
nog volhoudt, en de hoogste piek sinds de laatste keer terugzetten. Op het
docentscherm staat daar de knop bij om een nieuwe zekering te plaatsen.

---

## 3. Wat er nieuw is aan entiteiten

Vijf sensoren, een keuzelijst, een schuif, een schakelaar en een binaire sensor:

| Entiteit | Wat het is |
| --- | --- |
| `select.<naam>_regelmodus` | Handmatig, zelfconsumptie of piekscheren |
| `number.<naam>_piekgrens` | De grens waar piekscheren op stuurt |
| `switch.<naam>_aansluitbewaking` | Het vangnet |
| `sensor.<naam>_regelactie` | Wat de regelaar deed, in gewone taal |
| `sensor.<naam>_batterij_opdracht` | Wat hij de batterij opdroeg |
| `sensor.<naam>_laadpaal_limiet` | Wat de laadpaal van hem mag |
| `sensor.<naam>_hoogste_piek` | De hoogste afname sinds terugzetten |
| `binary_sensor.<naam>_hoofdzekering` | Aan betekent doorgesmolten |
| `sensor.<naam>_zekering_warmte` | Hoe warm hij is, met de resterende tijd als kenmerk |

Plus de service `virtual_ems.zekering_herstellen` en een vijfde scenario,
`piek_met_regelaar`: dezelfde avondpiek als `piekbelasting_avond` maar met
piekscheren aan. Die twee knoppen achter elkaar zijn de les.

---

## 4. Het bewijs

```
$ python -m pytest -p windows_shim --no-header
181 passed
```

Verdeeld over 160 kernproeven zonder Home Assistant en 21 met een echte Home
Assistant in het geheugen. Nieuw daarin: 23 proeven op de regelaar, 12 op de
zekering, en 13 die de twee in de hele simulatie doorrekenen.

**Tweeentwintig mutaties, tweeentwintig keer gevangen**, waaronder vijf nieuwe die
precies jouw klacht nabootsen:

```
GEVANGEN      het vangnet doet niets meer
              Precies de klacht: je zet alles aan en er wordt niets teruggeregeld.
GEVANGEN      zelfconsumptie met het teken de verkeerde kant op
GEVANGEN      de laadpaal wordt teruggeregeld voordat het laden stopt
              De volgorde is de les: eerst wat niemand mist.
GEVANGEN      de hoofdzekering smelt nooit door
GEVANGEN      een gesprongen zekering laat de installatie gewoon doordraaien
```

### Drie dingen die het meten aan het licht bracht

**De kop las de verkeerde ingreep voor.** Bij jouw scenario, alles aan, regelt
het vangnet twee dingen terug: 4,78 kW aan laden en daarna nog 20 W van de
laadpaal. Bovenaan het scherm stond die 20 W, want de redenen werden vooraan
ingevoegd en de laatste ingreep kwam dus als eerste. Ze staan nu in de volgorde
waarin er is ingegrepen, met een knelpunt altijd vooraan. Gevonden door de
uitvoer van een echte doorrekening te lezen in plaats van de proef te
vertrouwen.


**De regelaar loog over de piek.** Kon de batterij het gat niet helemaal dichten,
dan meldde hij toch "om de afname onder 3,00 kW te houden", terwijl de afname
gewoon boven de grens bleef. Nu staat er wat er werkelijk gebeurt: "De batterij
ontlaadt met 1,00 kW, maar de afname blijft met 8,00 kW boven de grens van
3,00 kW." Gevonden door een proef die de verkeerde tekst verwachtte.

**De SoC-grens zat na deze ronde op twee plekken en werd nog maar op één plek
getoetst.** De regelaar knijpt een verzoek af zodat hij geen reden op het scherm
zet over vermogen dat er niet is, en de natuurkunde knijpt het daarna nog een
keer af omdat die nooit een grens mag passeren. Daardoor bleven twee bestaande
mutaties in de natuurkundige laag onopgemerkt: de regelaar ving ze al af. De
mutatieproef zag dat, en er staan nu twee proeven bij die de onderste laag
rechtstreeks aanspreken.

---

## 5. Samenvatting

Er zit nu een regelaar in die elke vijf seconden beslist, drie standen om te
vergelijken, een vangnet dat in een uitlegbare volgorde terugregelt, en een
hoofdzekering die doorsmelt als je het vangnet uitzet. Alles wat het systeem doet
staat in gewone taal op het scherm en in een entiteit. De vier oefeningen in de
README gaan nu over het systeem: doe het eerst zelf, laat het daarna doen,
vergelijk de hoogste piek, en kijk waar het ophoudt. 181 proeven groen,
22 mutaties gevangen.

## 6. Wat niet lukte

* **Geen browsermeting deze ronde.** Chrome startte hier niet meer op en de
  extensie was niet verbonden, dus de nieuwe kaart `virtual-ems-regelaar` en het
  regelblok in de kop zijn **niet** in een echte browser bekeken of aangeklikt.
  Wat er wel is: alle statische bewakers zijn groen, `node --check` op alle
  twaalf modules, en een nieuwe proef die de hele bundel in Node laadt met een
  minimale omgeving. Die toetst pure logica, dus registratie, de configuratie die
  de strategie bouwt en de Nederlandse opmaak van getallen; over de CSS-cascade
  en over of een knop een klik aanneemt zegt hij niets. De kaarten uit ronde 2
  zijn ongewijzigd en die metingen staan nog.
* **Nog steeds niet in een echte Home Assistant gedraaid.** Dat blijft de
  eerstvolgende stap, en daar heb jij de installatie voor.
* **De regelaar kent geen tarieven.** Er is dus geen stand die op de prijs
  stuurt, terwijl dat in de praktijk vaak de derde reden is om een batterij te
  hebben. Dat is een ronde op zich: er moet dan een prijsreeks bij, en die moet
  ergens vandaan komen.
* **De regelaar kijkt niet vooruit.** Hij beslist op wat hij nu ziet. Een echt
  EMS kijkt naar de weersverwachting en naar het verwachte verbruik. Dat is
  bewust: vooruitkijken zonder voorspelling is verzinnen, en dat hoort niet in
  lesmateriaal.

## 7. Aannames

* **De volgorde van terugregelen** (eerst het laden van de batterij, dan de
  laadpaal, dan de batterij laten bijspringen) is een ontwerpkeuze, geen norm.
  Hij is gekozen op wat een cursist kan uitleggen: eerst gaat weg wat niemand
  mist. Hij staat op één plek in `regelaar.py` en er staat een proef op.
* **De hoofdzekering is één warmtemodel**, geijkt op twee punten uit
  IEC 60269-1, en hij is te traag bij zware overbelasting. Dat staat in het
  bestand, in de README en hierboven.
* **Het vangnet staat standaard aan.** Een cursist die niets weet kan de zekering
  dus niet meteen opblazen; dat moet je expres doen. Dat leek me de goede kant om
  op te vergissen.
* **De zekering rekent met vermogen en niet met stroom.** De simulatie kent één
  spanning, dus die twee lopen recht evenredig en de verhouding tot de nominale
  waarde is wat telt. Per fase wordt er niet gerekend, en dat staat ook op de
  kaart zelf.
* **Zelfconsumptie en piekscheren negeren de SoC-grenzen niet**, maar ze houden er
  ook geen strategie op na: ze vragen wat er nodig is en krijgen wat er kan. Een
  echte regelaar zou reserveren voor later.

## 8. `git status --porcelain`

```
$ git status --porcelain
(leeg)
```

Eén commit op `ronde-3-de-regelaar`, via een PR samengevoegd in `main`, en
getagd als `v1.2.0`.
