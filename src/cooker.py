import enum
import math
from collections import defaultdict
from typing import List, Optional

import crcmod
from miio.device import Device, DeviceStatus
from miio.exceptions import DeviceException

from logger import cooker_logger

PROFILES = {
    # 60 minutes cooking for tasty rice
    "FineRice": "02010000000001e101000000000000800101050814000000002091827d7800050091822d781c0a0091823c781c1e0091ff827820ffff91828278000500ffff8278ffffff91828278000d00ff828778ff000091827d7800000091827d7800ffff91826078ff0100490366780701086c0078090301af540266780801086c00780a02023c5701667b0e010a71007a0d02ffff5701667b0f010a73007d0d032005000000000000000000000000000000cf53",
    # Quick 40 minutes cooking
    "QuickRice": "02010100000002e100280000000000800101050614000000002091827d7800000091823c7820000091823c781c1e0091ff827820ffff91828278000500ffff8278ffffff91828278000d00ff828778ff000082827d7800000091827d7800ffff91826078ff0164490366780701086c007409030200540266780801086c00760a0202785701667b0e010a7100780a02ffff5701667b0f010a73007b0a032005000000000000000000000000000000ddba",
    # Cooking on slow fire from 40 minutes to 4 hours
    "Gongee": "02010200000003e2011e0400002800800101050614000000002091827d7800000091827d7800000091827d78001e0091ff877820ffff91827d78001e0091ff8278ffffff91828278001e0091828278060f0091827d7804000091827d7800000091827d780001f54e0255261802062a0482030002eb4e0255261802062a04820300032d4e0252261802062c04820501ffff4e0152241802062c0482050120000000000000000000000000000000009ce2",
    # Keeping warm at 73 degrees
    "KeepWarm": "020103000000040c00001800000100800100000000000000002091827d7800000091827d7800000091827d78000000915a7d7820000091827d7800000091826e78ff000091827d7800000091826e7810000091826e7810000091827d7800000091827d780000a082007882140010871478030000eb820078821400108714780300012d8200788214001087147a0501ffff8200788214001087147d0501200000000000000000000000000000000090e5",
}

_LOGGER = cooker_logger

MODEL_MULTI = "chunmi.cooker.eh1"

COOKING_STAGES = {
    1: {
        "name": "Quickly preheat",
        "description": "Increase temperature in a controlled manner to soften rice",
    },
    2: {
        "name": "Absorb water at moderate temp.",
        "description": "Increase temperature steadily and let rice absorb enough water to provide full grains and a taste of fragrance and sweetness.",
    },
    3: {
        "name": "Operate at full load to boil rice",
        "description": "Keep heating at high temperature. Let rice to receive thermal energy uniformly.",
    },
    4: {
        "name": "Operate at full load to boil rice",
        "description": "Keep heating at high temperature. Let rice to receive thermal energy uniformly.",
    },
    5: {
        "name": "Operate at full load to boil rice",
        "description": "Keep heating at high temperature. Let rice to receive thermal energy uniformly.",
    },
    6: {
        "name": "Operate at full load to boil rice",
        "description": "Keep heating at high temperature. Let rice to receive thermal energy uniformly.",
    },
    7: {
        "name": "Ultra high",
        "description": "High-temperature steam generates crystal clear rice grains and saves its original sweet taste.",
    },
    9: {
        "name": "Cook rice over a slow fire",
        "description": "Keep rice warm uniformly to lock lateral heat inside. So the rice will get gelatinized sufficiently.",
    },
    10: {
        "name": "Cook rice over a slow fire",
        "description": "Keep rice warm uniformly to lock lateral heat inside. So the rice will get gelatinized sufficiently.",
    },
}

COOKING_MENUS = {
    "0000000000000000000000000000000000000001": "Fine Rice",
    "0101000000000000000000000000000000000002": "Quick Rice",
    "0202000000000000000000000000000000000003": "Congee",
    "0303000000000000000000000000000000000004": "Keep warm",
}


class CookerException(DeviceException):
    pass


class OperationMode(enum.Enum):
    Waiting = 1
    Running = 2
    AutoKeepWarm = 3
    PreCook = 4

    Unknown = "unknown"

    @classmethod
    def _missing_(cls, _):
        return OperationMode.Unknown


class TemperatureHistory(DeviceStatus):
    def __init__(self, data: str):
        """Container of temperatures recorded every 10-15 seconds while cooking.

        Example values:

        Status waiting:
        0

        2 minutes:
        161515161c242a3031302f2eaa2f2f2e2f

        12 minutes:
        161515161c242a3031302f2eaa2f2f2e2f2e302f2e2d302f2f2e2f2f2f2f343a3f3f3d3e3c3d3c3f3d3d3d3f3d3d3d3d3e3d3e3c3f3f3d3e3d3e3e3d3f3d3c3e3d3d3e3d3f3e3d3f3e3d3c

        32 minutes:
        161515161c242a3031302f2eaa2f2f2e2f2e302f2e2d302f2f2e2f2f2f2f343a3f3f3d3e3c3d3c3f3d3d3d3f3d3d3d3d3e3d3e3c3f3f3d3e3d3e3e3d3f3d3c3e3d3d3e3d3f3e3d3f3e3d3c3f3e3d3c3f3e3d3c3f3f3d3d3e3d3d3f3f3d3d3f3f3e3d3d3d3e3e3d3daa3f3f3f3f3f414446474a4e53575e5c5c5b59585755555353545454555554555555565656575757575858585859595b5b5c5c5c5c5d5daa5d5e5f5f606061

        55 minutes:
        161515161c242a3031302f2eaa2f2f2e2f2e302f2e2d302f2f2e2f2f2f2f343a3f3f3d3e3c3d3c3f3d3d3d3f3d3d3d3d3e3d3e3c3f3f3d3e3d3e3e3d3f3d3c3e3d3d3e3d3f3e3d3f3e3d3c3f3e3d3c3f3e3d3c3f3f3d3d3e3d3d3f3f3d3d3f3f3e3d3d3d3e3e3d3daa3f3f3f3f3f414446474a4e53575e5c5c5b59585755555353545454555554555555565656575757575858585859595b5b5c5c5c5c5d5daa5d5e5f5f60606161616162626263636363646464646464646464646464646464646464646364646464646464646464646464646464646464646464646464646464aa5a59585756555554545453535352525252525151515151

        Data structure:

        Octet 1 (16): First temperature measurement in hex (22 °C)
        Octet 2 (15): Second temperature measurement in hex (21 °C)
        Octet 3 (15): Third temperature measurement in hex (21 °C)
        ...
        """
        if not len(data) % 2:
            self.data = [int(data[i : i + 2], 16) for i in range(0, len(data), 2)]
        else:
            self.data = []

    @property
    def temperatures(self) -> List[int]:
        return self.data

    @property
    def raw(self) -> str:
        return "".join([f"{value:02x}" for value in self.data])

    def __str__(self) -> str:
        return str(self.data)


class MultiCookerProfile:
    """This class can be used to modify and validate an existing cooking profile."""

    def __init__(
        self,
        profile_hex: str,
        duration: int = None,
        schedule: int = None,
        akw: bool = None,
    ):
        if len(profile_hex) < 5:
            raise CookerException("Invalid profile")
        else:
            self.checksum = bytearray.fromhex(profile_hex)[-2:]
            self.profile_bytes = bytearray.fromhex(profile_hex)[:-2]

            if not self.is_valid():
                raise CookerException("Profile checksum error")

            self.set_schedule_enabled(False)

            if duration is not None:
                self.set_duration(duration)
            if schedule is not None and schedule > 0 and schedule <= 1440:
                self.set_schedule_enabled(True)
                self.set_schedule_duration(schedule)
            if akw is not None:
                self.set_akw_enabled(akw)

    def is_set_duration_allowed(self):
        return (
            self.profile_bytes[10] != self.profile_bytes[12]
            or self.profile_bytes[11] != self.profile_bytes[13]
        )

    def get_duration(self):
        """Get the duration in minutes."""
        return (self.profile_bytes[8] * 60) + self.profile_bytes[9]

    def set_duration(self, minutes):
        """Set the duration in minutes if the profile allows it."""
        if not self.is_set_duration_allowed():
            return

        max_minutes = (self.profile_bytes[10] * 60) + self.profile_bytes[11]
        min_minutes = (self.profile_bytes[12] * 60) + self.profile_bytes[13]

        if minutes < min_minutes or minutes > max_minutes:
            return

        self.profile_bytes[8] = math.floor(minutes / 60)
        self.profile_bytes[9] = minutes % 60

        self.update_checksum()

    def is_schedule_enabled(self):
        return (self.profile_bytes[14] & 0x80) == 0x80

    def set_schedule_enabled(self, enabled):
        if enabled:
            self.profile_bytes[14] |= 0x80
        else:
            self.profile_bytes[14] &= 0x7F

        self.update_checksum()

    def set_schedule_duration(self, duration):
        """Set the schedule time (delay before cooking) in minutes."""
        schedule_flag = self.profile_bytes[14] & 0x80
        self.profile_bytes[14] = math.floor(duration / 60) & 0xFF
        self.profile_bytes[14] |= schedule_flag
        self.profile_bytes[15] = (duration % 60 | self.profile_bytes[15] & 0x80) & 0xFF

        self.update_checksum()

    def is_akw_enabled(self):
        return (self.profile_bytes[15] & 0x80) == 0x80

    def set_akw_enabled(self, enabled):
        if enabled:
            self.profile_bytes[15] |= 0x80
        else:
            self.profile_bytes[15] &= 0x7F

        self.update_checksum()

    def calc_checksum(self):
        crc = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0, xorOut=0x0)(
            self.profile_bytes
        )
        checksum = bytearray(2)
        checksum[0] = (crc >> 8) & 0xFF
        checksum[1] = crc & 0xFF
        return checksum

    def update_checksum(self):
        self.checksum = self.calc_checksum()

    def is_valid(self):
        return len(self.profile_bytes) == 174 and self.checksum == self.calc_checksum()

    def get_profile_hex(self):
        return (self.profile_bytes + self.checksum).hex()


class CookerStatus(DeviceStatus):
    def __init__(self, data):
        self.data = data

    @property
    def mode(self) -> OperationMode:
        """Current operation mode."""
        return OperationMode(self.data["status"])

    @property
    def menu(self) -> str:
        """Selected menu id."""
        try:
            return COOKING_MENUS[self.data["menu"]]
        except KeyError:
            return "Unknown menu"

    @property
    def stage(self) -> str:
        """Current stage if cooking."""
        try:
            return COOKING_STAGES[self.data["phase"]]["name"]
        except KeyError:
            return "Unknown stage"

    @property
    def temperature(self) -> Optional[int]:
        """Current temperature, if idle.

        Example values: 29
        """
        return self.data["temp"]

    @property
    def start_time(self) -> int:
        """Start time of cooking?"""
        return int(self.data["t_start"])

    @property
    def remaining(self) -> int:
        """Remaining minutes of the cooking process."""
        return int(int(self.data["t_left"]) / 60)

    @property
    def cooking_delayed(self) -> Optional[int]:
        """Wait n minutes before cooking / scheduled cooking."""
        delay = int(self.data["t_pre"])

        if delay >= 0:
            return delay

        return None

    @property
    def duration(self) -> int:
        """Duration of the cooking process."""
        return int(self.data["t_cook"])

    @property
    def keep_warm(self) -> bool:
        """Keep warm after cooking?"""
        return self.data["akw"] == 1

    @property
    def settings(self) -> None:
        """Settings of the cooker."""
        return None

    @property
    def hardware_version(self) -> None:
        """Hardware version."""
        return None

    @property
    def firmware_version(self) -> None:
        """Firmware version."""
        return None

    @property
    def taste(self) -> None:
        """Taste id."""
        return self.data["taste"]

    @property
    def rice(self) -> None:
        """Rice id."""
        return self.data["rice"]

    @property
    def favorite(self) -> None:
        """Favored recipe id."""
        return self.data["favs"]


class MultiCooker(Device):
    """Main class representing the multi cooker."""

    _supported_models = [MODEL_MULTI]

    def status(self) -> CookerStatus:
        """Retrieve properties."""
        properties = [
            "status",
            "phase",
            "menu",
            "t_cook",
            "t_left",
            "t_pre",
            "t_kw",
            "taste",
            "temp",
            "rice",
            "favs",
            "akw",
            "t_start",
            "t_finish",
            "version",
            "setting",
            "code",
            "en_warm",
            "t_congee",
            "t_love",
            "boil",
        ]

        values = []
        for prop in properties:
            values.append(self.send("get_prop", [prop])[0])

        properties_count = len(properties)
        values_count = len(values)
        if properties_count != values_count:
            _LOGGER.debug(
                "Count (%s) of requested properties does not match the "
                "count (%s) of received values.",
                properties_count,
                values_count,
            )

        return CookerStatus(defaultdict(lambda: None, zip(properties, values)))

    def start(
        self, profile: str, duration: int = None, schedule: int = None, akw: bool = None
    ):
        """Start cooking a profile."""
        cookerProfile = MultiCookerProfile(profile, duration, schedule, akw)
        self.send("set_start", [cookerProfile.get_profile_hex()])
        cooker_logger.info(
            "启动烹饪：profile=%s duration=%s schedule=%s akw=%s",
            profile,
            duration,
            schedule,
            akw,
        )

    def stop(self):
        """Stop cooking."""
        self.send("cancel_cooking", [])
        cooker_logger.info("停止烹饪")

    def menu(self, profile: str, duration: int, schedule: int, akw: bool):
        """Select one of the default(?) cooking profiles."""
        cookerProfile = MultiCookerProfile(profile, duration, schedule, akw)
        self.send("set_menu", [cookerProfile.get_profile_hex()])

    def get_temperature_history(self) -> TemperatureHistory:
        """Retrieves a temperature history.

        The temperature is only available while cooking. Approx. six data points per
        minute.
        """
        return TemperatureHistory(self.send("get_temp_history")[0])

    def is_online(self):
        """Is Online?"""
        try:
            [status] = self.send("get_prop", ["status"])
            return status > 0
        except Exception:
            return False

    def get_mode(self):
        """mode"""
        [mode] = self.send("get_prop", ["status"])
        return OperationMode(mode)