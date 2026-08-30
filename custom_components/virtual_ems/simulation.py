"""Rekenkern van het virtuele EMS.

Dit bestand kent zijn omgeving niet: er staat geen enkele Home Assistant import
in. Alles hier is losse Python en daardoor los te draaien tegen een hele
gesimuleerde dag, zonder Home Assistant, zonder broker en zonder browser. De
bedrading naar Home Assistant zit in coordinator.py en de platformbestanden.

Bronnen van de gebruikte formules (geen enkel kental is verzonnen):

* Zonnestand: NOAA Solar Calculator, gebaseerd op de Fourierbenadering van
  Spencer (1971) voor declinatie en tijdsvereffening.
* Luchtmassa: Kasten & Young (1989), "Revised optical air mass tables and
  approximation formula", Applied Optics 28(22):4735.
* Heldere-hemel directe straling: Meinel & Meinel (1976), "Applied Solar
  Energy", I_b = 1353 * 0.7^(AM^0.678) W/m2.
* Diffuse straling en grondreflectie: het gangbare isotrope hellingsvlakmodel
  (Liu & Jordan, 1960).

Alles wat daarna volgt (systeemgrootte, rendement, profielvorm) is een
instelling die de docent kan wijzigen, niet een aangenomen meetwaarde.
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

from .regelaar import MODUS_HANDMATIG, Besluit, Situatie, bepaal
from .zekering import Zekering

# --- Natuurkundige constanten met bron ---------------------------------------

#: Zonneconstante zoals gebruikt in de formule van Meinel & Meinel (1976), W/m2.
MEINEL_I0: float = 1353.0

#: Aandeel diffuse straling t.o.v. de directe horizontale component in het
#: eenvoudige heldere-hemelmodel van Meinel & Meinel (1976).
MEINEL_DIFFUSE_FRACTION: float = 0.10

STC_IRRADIANCE: float = 1000.0  # W/m2, standaardtestcondities van een paneel

# Tijdconstante van de ruis op de basislast (Ornstein-Uhlenbeck), in seconden.
# Dit is een vormparameter van de simulatie, geen meting.
NOISE_TAU_SECONDS: float = 300.0
NOISE_SIGMA_RELATIVE: float = 0.15

# Oplooptijd van de laadpaal van 0 naar het maximale vermogen, in seconden.
# Een echte laadpaal springt niet in één stap naar zijn eindvermogen; deze
# oplooptijd maakt dat zichtbaar op het dashboard.
EV_RAMP_SECONDS: float = 10.0

MAX_STEP_SECONDS: float = 900.0


# --- Configuratie ------------------------------------------------------------


@dataclass(frozen=True)
class PlantConfig:
    """De vaste eigenschappen van de gesimuleerde installatie."""

    pv_peak_kwp: float = 4.0
    battery_capacity_kwh: float = 10.0
    ev_max_power_w: float = 11000.0
    annual_consumption_kwh: float = 2900.0

    # Locatie. Home Assistant levert deze aan vanuit de instellingen van de
    # installatie; de default is het geografische midden van Nederland.
    latitude: float = 52.156
    longitude: float = 5.388

    # Paneelopstelling: hellingshoek en azimut (180 graden = pal zuid).
    panel_tilt_deg: float = 35.0
    panel_azimuth_deg: float = 180.0
    albedo: float = 0.20

    # Verhouding tussen opgewekte gelijkstroom en wat er na omvormer-,
    # temperatuur- en kabelverlies overblijft. Instelling, geen meting.
    performance_ratio: float = 0.85

    # Maximaal laad-/ontlaadvermogen als fractie van de capaciteit per uur.
    # 0,5 C op 10 kWh geeft 5 kW.
    battery_c_rate: float = 0.5

    # Retourrendement over een volledige laad- en ontlaadcyclus.
    round_trip_efficiency: float = 0.90

    household_profile: tuple[float, ...] = (
        0.55, 0.50, 0.48, 0.47, 0.48, 0.55, 0.80, 1.30,
        1.35, 1.05, 0.90, 0.85, 0.95, 0.90, 0.85, 0.90,
        1.10, 1.55, 1.85, 1.70, 1.45, 1.25, 0.95, 0.70,
    )

    appliances: tuple[tuple[str, float], ...] = (
        ("wasmachine", 2000.0),
        ("boiler", 2500.0),
        ("airco", 1200.0),
    )

    # De netaansluiting. Een gangbare Nederlandse woningaansluiting is 3 fasen
    # van 25 A; de waarden zijn een instelling, want een oudere woning heeft er
    # vaak 1 van 35 A. Hier hangt de schaal van de balken op het dashboard aan,
    # dus zonder deze twee zou een balk een verzonnen maximum tonen.
    connection_current_a: float = 25.0
    connection_phases: int = 3
    grid_voltage_v: float = 230.0

    @property
    def connection_power_w(self) -> float:
        """Wat de aansluiting aankan, in W: fasen maal ampère maal spanning."""
        return self.connection_phases * self.connection_current_a * self.grid_voltage_v

    @property
    def battery_max_power_w(self) -> float:
        """Maximaal laad- of ontlaadvermogen in W, uit capaciteit en C-rate."""
        return self.battery_capacity_kwh * self.battery_c_rate * 1000.0

    @property
    def one_way_efficiency(self) -> float:
        """Rendement van één richting, zodat heen en terug het retour geeft."""
        return math.sqrt(self.round_trip_efficiency)

    def appliance_power(self, key: str) -> float:
        for name, power in self.appliances:
            if name == key:
                return power
        raise KeyError(key)


# --- Instelbare grootheden (wat een cursist bedient) -------------------------


@dataclass
class Setpoints:
    """Alles wat een cursist of de docent kan verzetten."""

    cloud_pct: float = 0.0
    battery_setpoint_w: float = 0.0
    soc_min_pct: float = 10.0
    soc_max_pct: float = 100.0
    ev_enabled: bool = False
    ev_setpoint_w: float = 3700.0
    time_factor: float = 1.0
    #: Wat de regelaar probeert te bereiken. Zie regelaar.py.
    modus: str = MODUS_HANDMATIG
    #: Het vangnet dat de installatie binnen de aansluiting houdt.
    bewaking: bool = True
    #: De grens waar piekscheren op stuurt, in W.
    peak_limit_w: float = 3000.0
    appliances: dict[str, bool] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Setpoints":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Totals:
    """Cumulatieve energietellers in kWh. Alle waarden zijn AC-zijdig."""

    pv_kwh: float = 0.0
    battery_charged_kwh: float = 0.0
    battery_discharged_kwh: float = 0.0
    ev_kwh: float = 0.0
    household_kwh: float = 0.0
    grid_import_kwh: float = 0.0
    grid_export_kwh: float = 0.0
    #: De hoogste afname sinds de laatste keer terugzetten, in W. Dit is geen
    #: teller maar een record, en hij hoort wel bij de andere: hij gaat met een
    #: reset mee terug naar nul.
    peak_import_w: float = 0.0
    appliance_kwh: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Totals":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass(frozen=True)
class Snapshot:
    """Het resultaat van één simulatiestap."""

    moment: datetime
    elapsed_s: float

    solar_elevation_deg: float
    poa_irradiance: float
    pv_power_w: float

    household_power_w: float
    appliance_power_w: dict[str, float]
    ev_power_w: float

    battery_power_w: float  # positief = laden, negatief = ontladen (AC-zijde)
    battery_soc_pct: float
    battery_energy_kwh: float

    grid_power_w: float  # positief = afname, negatief = teruglevering

    #: Wat de regelaar besloten heeft en waarom.
    control_reason: str
    control_reasons: tuple[str, ...]
    control_intervened: bool
    control_bottleneck: bool
    #: Wat de regelaar de laadpaal en de batterij opdroeg, voor de natuurkunde
    #: er nog iets van afknijpt. Het verschil met wat er werkelijk gebeurt is de
    #: les.
    ev_allowed_w: float
    battery_command_w: float
    #: Wat de omvormer had kunnen leveren maar niet mocht.
    pv_curtailed_w: float

    #: De hoofdzekering.
    fuse_heat_pct: float
    fuse_blown: bool

    #: Hoe vol de aansluiting zit, in procent van wat hij aankan.
    connection_load_pct: float
    #: Welk deel van de eigen opwek ook zelf gebruikt is, in procent. None
    #: zolang er nog niets opgewekt is, want dan is er niets te delen en zou
    #: elk getal verzonnen zijn.
    self_consumption_pct: float | None
    totals: Totals


# --- Zonnestand en straling --------------------------------------------------


def solar_position(moment: datetime, latitude: float, longitude: float) -> tuple[float, float]:
    """Geef (hoogte, azimut) van de zon in graden.

    Volgt de rekenwijze van de NOAA Solar Calculator. `moment` moet
    tijdzone-bewust zijn; er wordt intern met UTC gerekend, dus zomertijd en
    wintertijd komen vanzelf goed.
    """
    utc = moment.astimezone(timezone.utc)
    day_of_year = int(utc.strftime("%j"))
    hour = utc.hour + utc.minute / 60.0 + utc.second / 3600.0

    # Fractionele jaarhoek in radialen.
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (hour - 12.0) / 24.0)

    # Tijdsvereffening in minuten (Spencer 1971).
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

    # Declinatie in radialen (Spencer 1971).
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    # Ware zonnetijd in minuten en de bijbehorende uurhoek in graden.
    true_solar_time = (hour * 60.0) + eqtime + 4.0 * longitude
    hour_angle = (true_solar_time / 4.0) - 180.0
    ha_rad = math.radians(hour_angle)
    lat_rad = math.radians(latitude)

    cos_zenith = math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.acos(cos_zenith)
    elevation = 90.0 - math.degrees(zenith)

    # Azimut via de componenten van de zonnevector in het plaatselijke vlak
    # (x naar het oosten, y naar het noorden). Met atan2 klopt elk kwadrant
    # vanzelf; een acos op één noemer geeft in de ochtend en de avond dezelfde
    # uitkomst en zet de zon dan aan de verkeerde kant van de hemel.
    east = -math.cos(decl) * math.sin(ha_rad)
    north = math.sin(decl) * math.cos(lat_rad) - math.cos(decl) * math.sin(lat_rad) * math.cos(ha_rad)
    azimuth = math.degrees(math.atan2(east, north)) % 360.0

    return elevation, azimuth


def clear_sky_dni(elevation_deg: float) -> float:
    """Directe normale straling bij heldere hemel, in W/m2.

    Luchtmassa volgens Kasten & Young (1989), verzwakking volgens
    Meinel & Meinel (1976).
    """
    if elevation_deg <= 0.0:
        return 0.0
    zenith_deg = 90.0 - elevation_deg
    denominator = math.cos(math.radians(zenith_deg)) + 0.50572 * (96.07995 - zenith_deg) ** -1.6364
    if denominator <= 0.0:
        return 0.0
    air_mass = 1.0 / denominator
    return MEINEL_I0 * 0.7 ** (air_mass**0.678)


def plane_of_array_irradiance(
    elevation_deg: float,
    azimuth_deg: float,
    tilt_deg: float,
    panel_azimuth_deg: float,
    albedo: float,
) -> float:
    """Straling op het hellend paneelvlak, in W/m2 (isotroop model)."""
    if elevation_deg <= 0.0:
        return 0.0

    dni = clear_sky_dni(elevation_deg)
    sin_elev = math.sin(math.radians(elevation_deg))
    dhi = MEINEL_DIFFUSE_FRACTION * dni * sin_elev
    ghi = dni * sin_elev + dhi

    tilt = math.radians(tilt_deg)
    cos_aoi = math.cos(math.radians(elevation_deg)) * math.sin(tilt) * math.cos(
        math.radians(azimuth_deg - panel_azimuth_deg)
    ) + sin_elev * math.cos(tilt)

    direct = dni * max(0.0, cos_aoi)
    diffuse = dhi * (1.0 + math.cos(tilt)) / 2.0
    reflected = ghi * albedo * (1.0 - math.cos(tilt)) / 2.0
    return direct + diffuse + reflected


# --- De simulatie zelf -------------------------------------------------------


class Simulation:
    """Stapsgewijze simulatie van PV, batterij, laadpaal, huis en netaansluiting."""

    def __init__(
        self,
        config: PlantConfig,
        setpoints: Setpoints | None = None,
        *,
        seed: int = 0,
    ) -> None:
        self.config = config
        self.setpoints = setpoints or Setpoints()
        for name, _power in config.appliances:
            self.setpoints.appliances.setdefault(name, False)

        self._random = random.Random(seed)
        self._seed = seed

        self.totals = Totals()
        for name, _power in config.appliances:
            self.totals.appliance_kwh.setdefault(name, 0.0)

        self.battery_energy_kwh = config.battery_capacity_kwh * 0.5
        self.ev_power_w = 0.0
        self.zekering = Zekering(nominaal_w=config.connection_power_w)
        self._noise = 0.0
        self.last_snapshot: Snapshot | None = None

    # -- afgeleide grootheden ------------------------------------------------

    @property
    def soc_pct(self) -> float:
        if self.config.battery_capacity_kwh <= 0:
            return 0.0
        return 100.0 * self.battery_energy_kwh / self.config.battery_capacity_kwh

    def set_soc_pct(self, value: float) -> None:
        value = max(0.0, min(100.0, value))
        self.battery_energy_kwh = self.config.battery_capacity_kwh * value / 100.0

    # -- deelberekeningen ----------------------------------------------------

    def pv_power(self, moment: datetime) -> tuple[float, float, float]:
        """Geef (vermogen in W, straling op het vlak in W/m2, zonnehoogte)."""
        elevation, azimuth = solar_position(moment, self.config.latitude, self.config.longitude)
        poa = plane_of_array_irradiance(
            elevation,
            azimuth,
            self.config.panel_tilt_deg,
            self.config.panel_azimuth_deg,
            self.config.albedo,
        )
        peak_w = self.config.pv_peak_kwp * 1000.0
        power = peak_w * (poa / STC_IRRADIANCE) * self.config.performance_ratio

        # Bewolking verlaagt de opbrengst evenredig, zoals in de opdracht
        # gevraagd: 100 % bewolking geeft nul opbrengst.
        cloud = max(0.0, min(100.0, self.setpoints.cloud_pct))
        power *= 1.0 - cloud / 100.0

        # De omvormer levert nooit meer dan het piekvermogen van de installatie.
        power = max(0.0, min(power, peak_w))
        return power, poa, elevation

    def base_load(self, moment: datetime) -> float:
        """Huishoudelijke basislast in W, zonder de losse apparaten."""
        profile = self.config.household_profile
        mean = sum(profile) / len(profile)
        if mean <= 0:
            return 0.0

        hour = moment.hour + moment.minute / 60.0 + moment.second / 3600.0
        low = int(hour) % 24
        high = (low + 1) % 24
        fraction = hour - int(hour)
        shape = profile[low] * (1.0 - fraction) + profile[high] * fraction

        average_w = self.config.annual_consumption_kwh * 1000.0 / 8760.0
        return max(0.0, average_w * (shape / mean) * (1.0 + self._noise))

    def _advance_noise(self, elapsed_s: float) -> None:
        """Ornstein-Uhlenbeck ruis: kleine, samenhangende schommelingen."""
        if elapsed_s <= 0:
            return
        decay = math.exp(-elapsed_s / NOISE_TAU_SECONDS)
        self._noise = decay * self._noise + NOISE_SIGMA_RELATIVE * math.sqrt(
            max(0.0, 1.0 - decay**2)
        ) * self._random.gauss(0.0, 1.0)
        # Begrens de ruis zodat de basislast nooit negatief of absurd wordt.
        self._noise = max(-0.6, min(0.6, self._noise))

    def appliance_powers(self) -> dict[str, float]:
        return {
            name: (power if self.setpoints.appliances.get(name) else 0.0)
            for name, power in self.config.appliances
        }

    def ev_request_w(self) -> float:
        """Wat de laadpaal zou vragen als niemand hem terugregelt."""
        if not self.setpoints.ev_enabled:
            return 0.0
        return max(0.0, min(self.setpoints.ev_setpoint_w, self.config.ev_max_power_w))

    def _advance_ev(self, target: float, elapsed_s: float) -> float:
        """Laat het laadvermogen oplopen of teruglopen naar wat mag."""
        target = max(0.0, min(target, self.config.ev_max_power_w))

        if elapsed_s <= 0:
            return self.ev_power_w

        rate = self.config.ev_max_power_w / EV_RAMP_SECONDS  # W per seconde
        step = rate * elapsed_s
        if target > self.ev_power_w:
            self.ev_power_w = min(target, self.ev_power_w + step)
        else:
            self.ev_power_w = max(target, self.ev_power_w - step)
        return self.ev_power_w

    def _soc_grenzen_kwh(self) -> tuple[float, float]:
        """De onder- en bovengrens in kWh, met omgedraaide grenzen verwisseld."""
        soc_min = max(0.0, min(100.0, self.setpoints.soc_min_pct))
        soc_max = max(0.0, min(100.0, self.setpoints.soc_max_pct))
        if soc_max < soc_min:
            soc_min, soc_max = soc_max, soc_min
        capaciteit = self.config.battery_capacity_kwh
        return capaciteit * soc_min / 100.0, capaciteit * soc_max / 100.0

    def max_charge_w(self, hours: float) -> float:
        """Wat er nu werkelijk in de batterij past, in W."""
        cfg = self.config
        _onder, boven = self._soc_grenzen_kwh()
        ruimte_kwh = max(0.0, boven - self.battery_energy_kwh)
        if hours <= 0:
            return cfg.battery_max_power_w if ruimte_kwh > 0 else 0.0
        eta = cfg.one_way_efficiency
        past_w = (ruimte_kwh / hours) * 1000.0 / eta if eta > 0 else 0.0
        return max(0.0, min(cfg.battery_max_power_w, past_w))

    def max_discharge_w(self, hours: float) -> float:
        """Wat er nu werkelijk uit de batterij kan, in W."""
        cfg = self.config
        onder, _boven = self._soc_grenzen_kwh()
        beschikbaar_kwh = max(0.0, self.battery_energy_kwh - onder)
        if hours <= 0:
            return cfg.battery_max_power_w if beschikbaar_kwh > 0 else 0.0
        kan_w = (beschikbaar_kwh / hours) * 1000.0 * cfg.one_way_efficiency
        return max(0.0, min(cfg.battery_max_power_w, kan_w))

    def _battery_step(self, gevraagd_w: float, hours: float) -> float:
        """Werk de batterij bij en geef het werkelijke AC-vermogen terug.

        Positief is laden, negatief is ontladen. Het gevraagde vermogen wordt
        afgeknepen door de C-rate en door de SoC-grenzen, zodat de batterij
        nooit boven de bovengrens laadt of onder de ondergrens ontlaadt.
        """
        cfg = self.config
        max_power = cfg.battery_max_power_w
        request = max(-max_power, min(max_power, gevraagd_w))

        soc_min = max(0.0, min(100.0, self.setpoints.soc_min_pct))
        soc_max = max(0.0, min(100.0, self.setpoints.soc_max_pct))
        if soc_max < soc_min:
            soc_min, soc_max = soc_max, soc_min

        upper_kwh = cfg.battery_capacity_kwh * soc_max / 100.0
        lower_kwh = cfg.battery_capacity_kwh * soc_min / 100.0
        eta = cfg.one_way_efficiency

        if hours <= 0 or request == 0.0:
            return 0.0

        if request > 0:
            room_kwh = max(0.0, upper_kwh - self.battery_energy_kwh)
            # Wat er aan AC-vermogen nog in past voordat de grens geraakt wordt.
            allowed_w = (room_kwh / hours) * 1000.0 / eta if eta > 0 else 0.0
            power = min(request, max(0.0, allowed_w))
            self.battery_energy_kwh += power * hours / 1000.0 * eta
            self.totals.battery_charged_kwh += power * hours / 1000.0
        else:
            available_kwh = max(0.0, self.battery_energy_kwh - lower_kwh)
            allowed_w = (available_kwh / hours) * 1000.0 * eta
            power = -min(-request, max(0.0, allowed_w))
            self.battery_energy_kwh -= (-power) * hours / 1000.0 / eta
            self.totals.battery_discharged_kwh += (-power) * hours / 1000.0

        # Numerieke afronding mag de harde grenzen nooit passeren.
        self.battery_energy_kwh = max(0.0, min(cfg.battery_capacity_kwh, self.battery_energy_kwh))
        return power

    def connection_load_pct(self, grid_power_w: float) -> float:
        """Hoe vol de aansluiting zit, in procent.

        De aansluiting draagt het saldo, en die draagt het in beide richtingen
        even zwaar: teruglevering belast hem net zo goed als afname.
        """
        grens = self.config.connection_power_w
        if grens <= 0:
            return 0.0
        return abs(grid_power_w) / grens * 100.0

    def self_consumption_pct(self) -> float | None:
        """Welk deel van de eigen opwek ook zelf gebruikt is, in procent.

        Is er nog niets opgewekt, dan valt er niets te verdelen en geeft deze
        som None: het systeem zegt dan dat het het niet weet, in plaats van nul
        of honderd te verzinnen.

        De batterij kan meer terugleveren dan er die dag is opgewekt. Dan zou de
        breuk onder nul zakken; hij wordt daarom op nul afgekapt.
        """
        opgewekt = self.totals.pv_kwh
        if opgewekt <= 0:
            return None
        zelf = opgewekt - self.totals.grid_export_kwh
        return max(0.0, min(100.0, zelf / opgewekt * 100.0))

    # -- de stap zelf --------------------------------------------------------

    def step(self, moment: datetime, elapsed_s: float) -> Snapshot:
        """Reken één stap door en geef het resultaat.

        `moment` is het gesimuleerde tijdstip (tijdzone-bewust), `elapsed_s` het
        aantal gesimuleerde seconden sinds de vorige stap.
        """
        elapsed_s = max(0.0, min(MAX_STEP_SECONDS, elapsed_s))
        hours = elapsed_s / 3600.0

        self._advance_noise(elapsed_s)

        pv_mogelijk, poa, elevation = self.pv_power(moment)
        appliances = self.appliance_powers()
        household_w = self.base_load(moment) + sum(appliances.values())

        if self.zekering.gesprongen:
            # Een doorgesmolten hoofdzekering betekent geen spanning in huis.
            # De omvormer valt uit, de laadpaal stopt, de batterij doet niets en
            # de apparaten staan wel aan maar krijgen niets. Alles nul dus, en
            # er loopt geen enkele teller door.
            besluit = Besluit(battery_w=0.0, ev_w=0.0, pv_w=0.0)
            besluit.redenen.append(
                "De hoofdzekering is doorgesmolten. Er staat geen spanning meer op de "
                "installatie; de docent moet hem vervangen."
            )
            pv_w = 0.0
            household_w = 0.0
            appliances = {naam: 0.0 for naam in appliances}
            ev_w = 0.0
            self.ev_power_w = 0.0
            battery_w = 0.0
            grid_w = 0.0
        else:
            # Hier zit het verschil tussen een installatie en een systeem: de
            # regelaar beslist eerst wat er moet gebeuren, daarna doet de
            # natuurkunde wat er kan.
            besluit = bepaal(
                Situatie(
                    pv_w=pv_mogelijk,
                    household_w=household_w,
                    ev_request_w=self.ev_request_w(),
                    battery_request_w=self.setpoints.battery_setpoint_w,
                    max_charge_w=self.max_charge_w(hours),
                    max_discharge_w=self.max_discharge_w(hours),
                    connection_w=self.config.connection_power_w,
                ),
                modus=self.setpoints.modus,
                bewaking=self.setpoints.bewaking,
                piekgrens_w=self.setpoints.peak_limit_w,
            )

            pv_w = besluit.pv_w
            ev_w = self._advance_ev(besluit.ev_w, elapsed_s)
            battery_w = self._battery_step(besluit.battery_w, hours)

            # Saldo op de netaansluiting: alles wat het huis vraagt minus alles
            # wat er lokaal geproduceerd of ontladen wordt. Positief is afname.
            grid_w = household_w + ev_w + battery_w - pv_w

            if self.zekering.stap(grid_w, elapsed_s):
                besluit.redenen.insert(
                    0,
                    "De hoofdzekering is zojuist doorgesmolten: te veel, te lang.",
                )

        if hours > 0:
            self.totals.pv_kwh += pv_w * hours / 1000.0
            self.totals.ev_kwh += ev_w * hours / 1000.0
            self.totals.household_kwh += household_w * hours / 1000.0
            self.totals.grid_import_kwh += max(0.0, grid_w) * hours / 1000.0
            self.totals.grid_export_kwh += max(0.0, -grid_w) * hours / 1000.0
            for name, power in appliances.items():
                self.totals.appliance_kwh[name] = (
                    self.totals.appliance_kwh.get(name, 0.0) + power * hours / 1000.0
                )

        # De hoogste afname is geen teller maar een record, en die telt ook mee
        # als er geen tijd verstreken is.
        self.totals.peak_import_w = max(self.totals.peak_import_w, grid_w)

        snapshot = Snapshot(
            moment=moment,
            elapsed_s=elapsed_s,
            connection_load_pct=self.connection_load_pct(grid_w),
            self_consumption_pct=self.self_consumption_pct(),
            solar_elevation_deg=elevation,
            poa_irradiance=poa,
            pv_power_w=pv_w,
            household_power_w=household_w,
            appliance_power_w=appliances,
            ev_power_w=ev_w,
            battery_power_w=battery_w,
            battery_soc_pct=self.soc_pct,
            battery_energy_kwh=self.battery_energy_kwh,
            grid_power_w=grid_w,
            control_reason=besluit.reden,
            control_reasons=tuple(besluit.redenen),
            control_intervened=besluit.ingegrepen,
            control_bottleneck=besluit.knelpunt,
            ev_allowed_w=besluit.ev_w,
            battery_command_w=besluit.battery_w,
            pv_curtailed_w=max(0.0, pv_mogelijk - pv_w) if not self.zekering.gesprongen else 0.0,
            fuse_heat_pct=self.zekering.warmte_pct,
            fuse_blown=self.zekering.gesprongen,
            totals=replace(self.totals, appliance_kwh=dict(self.totals.appliance_kwh)),
        )
        self.last_snapshot = snapshot
        return snapshot

    # -- beheer --------------------------------------------------------------

    def reset(self, *, only_counters: bool = False, start_soc_pct: float = 50.0) -> None:
        """Zet de tellers terug, en desgewenst ook de bediening."""
        self.totals = Totals()
        for name, _power in self.config.appliances:
            self.totals.appliance_kwh[name] = 0.0

        self.set_soc_pct(start_soc_pct)
        # Een nieuwe lesgroep begint met een hele zekering.
        self.zekering.herstel()

        if not only_counters:
            self.setpoints = Setpoints()
            for name, _power in self.config.appliances:
                self.setpoints.appliances[name] = False
            self.ev_power_w = 0.0
            self._noise = 0.0
            self._random = random.Random(self._seed)

    def as_dict(self) -> dict[str, Any]:
        """Toestand voor opslag, zodat een herstart de tellers niet wist."""
        return {
            "battery_energy_kwh": self.battery_energy_kwh,
            "ev_power_w": self.ev_power_w,
            "noise": self._noise,
            "totals": self.totals.as_dict(),
            "setpoints": self.setpoints.as_dict(),
            "zekering": self.zekering.as_dict(),
        }

    def restore(self, data: dict[str, Any]) -> None:
        """Lees een eerder opgeslagen toestand terug."""
        if not data:
            return
        self.battery_energy_kwh = max(
            0.0,
            min(self.config.battery_capacity_kwh, float(data.get("battery_energy_kwh", self.battery_energy_kwh))),
        )
        self.ev_power_w = float(data.get("ev_power_w", 0.0))
        self._noise = float(data.get("noise", 0.0))
        if isinstance(data.get("totals"), dict):
            self.totals = Totals.from_dict(data["totals"])
        if isinstance(data.get("setpoints"), dict):
            self.setpoints = Setpoints.from_dict(data["setpoints"])
        if isinstance(data.get("zekering"), dict):
            self.zekering.restore(data["zekering"])
        for name, _power in self.config.appliances:
            self.setpoints.appliances.setdefault(name, False)
            self.totals.appliance_kwh.setdefault(name, 0.0)
