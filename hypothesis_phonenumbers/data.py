from typing import NamedTuple

from aenum import Enum


class PhoneNumberFormat(Enum):
    E164 = 0, "E164"
    INTERNATIONAL = 1, "INTERNATIONAL"
    NATIONAL = 2, "NATIONAL"
    RFC3966 = 3, "RFC3966"

    def __iter__(self):
        """this works around a pycharm issue PY-30216
        https://youtrack.jetbrains.com/issue/PY-30216/Enum-type-from-enum-backport-is-not-recognized-as-iterable"""
        super().__iter__(self)

    def __str__(self):
        return self.string

    @classmethod
    def _missing_value_(cls, value):
        # noinspection PyTypeChecker
        for member in cls:
            if isinstance(value, str) and member.value == value.upper():
                return member
            if member.string == value:
                return member


# this works around a pycharm issue PY-30216
# PhoneNumberFormat = PhoneNumberFormat  # type: typing.Union[typing.Type[PhoneNumberFormat], typing.Iterable]


NAMED_NUMBER_FORMATS = [
    "general_desc",  # General Description
    "fixed_line",
    "mobile",
    "toll_free",
    "premium_rate",
    "shared_cost",
    "personal_number",
    "voip",
    "pager",
    "uan",
    "emergency",
    "voicemail",
    "short_code",
    "standard_rate",
    "carrier_specific",
    "sms_services",
    "no_international_dialling",
]


# PhoneRegion = namedtuple("PhoneRegion", ["country_code", "region_code"])
class PhoneNumberRegion(NamedTuple):
    country_code: int
    region_code: str


class RegionalNamedFormat(NamedTuple):
    region: PhoneNumberRegion
    format_name: str
    format_regex: str
