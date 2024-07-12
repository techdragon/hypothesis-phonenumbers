"""


        Country Codes are the numerical prefix in the phone number for routing calls.
        Region Codes are the ISO 3166-1 alpha 2 character abbreviations that refer to a country.

        NOTE: National trunk prefix not being a feature of all regions and regions having variation in
            their known number patterns, such as many not having shared cost number formats,
            means we need a slightly complicated method to control exclusion and inclusion as
            its necessary to distinguish between allowing or excluding it in the output,
            and specifically limiting the search space to only generate numbers from
            regions where it is possible to generate this kind of number.

        number_formats is a dictionary containing the names of various number formats
            and a value of True, False or None, to control their inclusion in the output.
                True indicates we want these in the output and will limit the strategy to
                    regions that have the named number format.
                False indicates we do not want these in the output,
                None indicates these can be generated when available, and we will not limit the region list.

        E.123 international notation prefixes are '+' followed by the country code such as 1, or 61,
                True indicates we want these in the output,
                False indicates we do not want these in the output,
                None indicates we will accept the default of True

        National number prefixes are what is used to indicate that the number being dialed includes an area code,
            in most countries this is just '0'
                True indicates we want these in the output and will limit the strategy to
                    regions that have trunk prefixes.
                False indicates we do not want these in the output,
                None indicates these can be generated when available, and we will not limit the region list.

        Local numbers without prefixes are the simplest format of phone number.
                True indicates we want these in the output,
                False indicates we do not want these in the output,
                None indicates we will accept the default of True
        """

from typing import Iterable, List, Optional, Union

from hypothesis import strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.strategies import SearchStrategy

# noinspection PyProtectedMember
from hypothesis.strategies._internal.strategies import Ex

# noinspection PyProtectedMember
from hypothesis.strategies._internal.utils import defines_strategy
from phonenumbers import COUNTRY_CODE_TO_REGION_CODE, SUPPORTED_REGIONS, PhoneMetadata

from hypothesis_phonenumbers.data import NAMED_NUMBER_FORMATS, PhoneNumberRegion, RegionalNamedFormat

PHONE_NUMBER_REGIONS: List[PhoneNumberRegion[int, str]] = []
for (
    _k,
    _v,
) in COUNTRY_CODE_TO_REGION_CODE.items():
    for _i in _v:
        PHONE_NUMBER_REGIONS.append(PhoneNumberRegion(_k, _i))

NUMBER_FORMATS: List[RegionalNamedFormat] = []
AVAILABILITY_LISTS = {}
METADATA_DICT = {}

for __phone_region in PHONE_NUMBER_REGIONS:
    __metadata: PhoneMetadata = PhoneMetadata.metadata_for_region_or_calling_code(
        __phone_region.country_code, __phone_region.region_code
    )
    __data = {"id": __metadata.id, "country_code": __metadata.country_code, "regexes": {}}

    # National Call Prefixes for easier lookup by the strategy.
    if hasattr(__metadata, "national_prefix") and __metadata.national_prefix is not None:
        __data["national_prefix"] = __metadata.national_prefix

    # Known number formats for easier lookup by the strategy.
    for number_format in NAMED_NUMBER_FORMATS:
        if hasattr(__metadata, number_format) and getattr(__metadata, number_format) is not None:
            if number_format not in AVAILABILITY_LISTS:
                AVAILABILITY_LISTS[number_format] = []
            AVAILABILITY_LISTS[number_format].append(__phone_region)
            __data["regexes"][number_format] = getattr(__metadata, number_format).national_number_pattern
            NUMBER_FORMATS.append(
                RegionalNamedFormat(
                    region=__phone_region,
                    format_name=number_format,
                    format_regex=getattr(__metadata, number_format).national_number_pattern,
                )
            )
    METADATA_DICT[__phone_region] = __data

phone_number_characters = st.sampled_from(elements=("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"))


def region_filter(
    regions_to_filter: Optional[Iterable[PhoneNumberRegion]] = None,
    has_national_trunk_prefix: Optional[bool] = None,
    required_number_formats: Optional[Iterable[str]] = None,
) -> List[PhoneNumberRegion[int, str]]:
    if required_number_formats is not None and not set(required_number_formats).issubset(set(NAMED_NUMBER_FORMATS)):
        raise ValueError("Invalid required named number format")  # NOQA: TRY003
    if regions_to_filter is None:
        regions_to_filter = PHONE_NUMBER_REGIONS
    for region in regions_to_filter:
        checks = []
        if has_national_trunk_prefix:
            checks.append("national_prefix" in METADATA_DICT[region])
        if required_number_formats:
            for __number_format in required_number_formats:
                checks.append(__number_format in METADATA_DICT[region]["regexes"])
        if all(checks):
            yield region


def region_finder(
    country_codes: Optional[List[int]] = None,
    region_codes: Optional[List[str]] = None,
) -> List[PhoneNumberRegion[int, str]]:
    if country_codes is not None and region_codes is not None:
        raise InvalidArgument("Cannot specify both country code and region code")  # NOQA: TRY003
    if country_codes is not None:
        for country_code in country_codes:
            if country_code.upper() not in SUPPORTED_REGIONS:
                raise InvalidArgument(f"Invalid country code: {country_code}")  # NOQA: TRY003
    if region_codes is not None:
        for region_code in region_codes:
            if region_code in COUNTRY_CODE_TO_REGION_CODE:
                raise InvalidArgument(f"Invalid region code: {region_code}")  # NOQA: TRY003
    if country_codes is not None:
        return [__region for __region in PHONE_NUMBER_REGIONS if __region.country_code in country_codes]
    elif region_codes is not None:
        return [__region for __region in PHONE_NUMBER_REGIONS if __region.region_code in region_codes]


def named_number_formats_from_regions(regions: Iterable[PhoneNumberRegion[int, str]]) -> Iterable[str]:
    __number_formats = set()
    for region in regions:
        for __key in METADATA_DICT[region]["regexes"]:
            __number_formats.update(__key)
    return __number_formats


class PhoneNumberStrategy(SearchStrategy):
    selected_region: Optional[PhoneNumberRegion] = None
    selected_named_number_format = Optional[str] = None

    def __init__(
        self,
        regions: Optional[Union[List[PhoneNumberRegion], List[tuple]]] = None,
        named_number_formats: Optional[List[str]] = None,
    ) -> None:
        super().__init__()
        if regions is None:
            self.regions = PHONE_NUMBER_REGIONS
        else:
            self.regions = [PhoneNumberRegion(*region) for region in regions]  # Normalize the types.
            for region in self.regions:
                if region not in PHONE_NUMBER_REGIONS:
                    # This might be a little confusing for tuple inputs
                    raise InvalidArgument(f"Invalid region: {region}")  # NOQA: TRY003

        if named_number_formats is None:
            self.named_number_formats = NAMED_NUMBER_FORMATS
        else:
            for __name in named_number_formats:
                if __name not in NAMED_NUMBER_FORMATS:
                    raise InvalidArgument(f"Invalid number format: {__name} in named_number_formats")  # NOQA: TRY003
            self.named_number_formats = named_number_formats

        self.available_formats: List[RegionalNamedFormat] = [
            _format
            for _format in NUMBER_FORMATS
            if _format.region in self.regions and _format.format_name in self.named_number_formats
        ]

    def do_draw(self, data: ConjectureData) -> Ex:
        """
        # 1 - Select Region
        # 2 - Select a Number format to generate
        # 3 - Attach suitable prefixes at random when desired.
        """
        self.selected_region: PhoneNumberRegion = data.draw(st.sampled_from(self.regions))
        available_formats = set(METADATA_DICT[self.selected_region]["regexes"].keys()).intersection(
            set(self.named_number_formats)
        )
        self.selected_named_number_format = data.draw(st.sampled_from(available_formats))
        # intersection of available formats and our selected formats
        selected_phone_number = data.draw(
            st.from_regex(
                regex=METADATA_DICT[self.selected_region]["regexes"][self.selected_named_number_format],
                alphabet=phone_number_characters,
                fullmatch=True,
            )
        )
        return selected_phone_number


@defines_strategy(force_reusable_values=True)
def phone_number(
    *, regions: Optional[Union[List[PhoneNumberRegion], List[tuple]]] = None, number_formats: Optional[List[str]] = None
) -> st.SearchStrategy[str]:
    return PhoneNumberStrategy(
        regions=regions,
        named_number_formats=number_formats,
    )


# phonenumbers.format_number(phonenumbers.parse(phone_number(region_codes='AU').example(), 'AU'), phonenumbers.PhoneNumberFormat.INTERNATIONAL)
# phonenumbers.format_number(phonenumbers.parse(phone_number(region_codes='AU').example(), 'AU'), 0)

# TODO: Dialing Sequence strategy:
#  generate the digits to dial a random number based on a country & international dial info
