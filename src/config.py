import os
import re
from datetime import datetime
from typing import List

import yaml


class Time(tuple):
    def __new__(cls, hour, minutes):
        return super().__new__(cls, (hour, minutes))

    def __repr__(self) -> str:
        return "Time(%s,%s)" % self

    def to_today_time(self):
        now = datetime.now()
        hour, minutes = self
        return now.replace(hour=hour, minute=minutes)


def time_representer(dumper: yaml.Dumper, data: Time):
    return dumper.represent_scalar("!time", "%s:%s" % data)


def time_constructor(loader: yaml.Loader, node: yaml.Node):
    value = loader.construct_scalar(node)
    hour, minutes = map(int, value.split(":"))
    return Time(hour, minutes)


yaml.add_representer(Time, time_representer)
yaml.add_constructor("!time", time_constructor)

# see: https://dev.to/mkaranasou/python-yaml-configuration-with-environment-variables-parsing-2ha6

# pattern for global vars: look for ${word}
pattern = re.compile(".*?\${(\w+)}.*?")
# the tag will be used to mark where to start searching for the pattern
# e.g. somekey: !ENV somestring${MYENVVAR}blah blah blah
yaml.add_implicit_resolver("!env", pattern, None)


def env_constructor(loader: yaml.Loader, node: yaml.Node):
    value = loader.construct_scalar(node)
    match = pattern.findall(value)  # to find all env variables in line
    if match:
        full_value = value
        for g in match:
            full_value = full_value.replace(f"${{{g}}}", os.environ.get(g, g))
        return full_value
    return value


yaml.add_constructor("!env", env_constructor)


class Mealtime(yaml.YAMLObject):
    yaml_tag = "!Mealtime"

    def __init__(
        self, usual_time: Time, earliest_time: Time, latest_time: Time
    ) -> None:
        self.usual_time = usual_time
        self.earliest_time = earliest_time
        self.latest_time = latest_time
        super().__init__()


class MealProfile(yaml.YAMLObject):
    yaml_tag = "!MealProfile"

    def __init__(self, type: str, time: Mealtime) -> None:
        self.type = type
        self.time = time
        super().__init__()


class CookerConfig(yaml.YAMLObject):
    yaml_tag = "!CookerConfig"

    def __init__(
        self,
        name: str,
        ip: str,
        token: str,
        akw: bool,
        unpluggedCheck: bool,
        unpluggedMaxDuration: int,
        unpluggedMaxReminderCount: int,
        unpluggedAutoStopAkw: bool,
        meal_profile_list: List[MealProfile],
    ) -> None:
        self.name = name
        self.ip = ip
        self.token = token
        self.akw = akw
        self.meal_profile_list = meal_profile_list
        self.unpluggedCheck = unpluggedCheck
        self.unpluggedMaxDuration = unpluggedMaxDuration
        self.unpluggedAutoStopAkw = unpluggedAutoStopAkw
        self.unpluggedMaxReminderCount = unpluggedMaxReminderCount
        super().__init__()


class PushConfig(yaml.YAMLObject):
    yaml_tag = "!PushConfig"

    def __init__(self, token: str) -> None:
        self.token = token
        super().__init__()


class Config(yaml.YAMLObject):
    yaml_tag = "!Config"

    def __init__(
        self, poll_interval: int, cooker_config: CookerConfig, push_config: PushConfig
    ) -> None:
        self.poll_interval = poll_interval
        self.cooker_config = cooker_config
        self.push_config = push_config
        super().__init__()


def read_config(config_path: str) -> Config:
    with open(
        config_path,
        encoding="utf8",
    ) as fp:
        config_content = fp.read()
        return yaml.full_load(config_content)
