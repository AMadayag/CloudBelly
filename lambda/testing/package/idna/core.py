# import bisect
import re
import unicodedata
from typing import Optional, Union

from . import idnadata
from .intranges import intranges_contain

_virama_combining_class = 9
_alabel_prefix = b"xn--"
_unicode_dots_re = re.compile(r"[\u002e\u3002\uff0e\uff61]")


class IDNAError(UnicodeError):
    """Base exception for all IDNA-encoding related problems"""
    pass


class IDNABidiError(IDNAError):
    """Exception when bidirectional requirements are not satisfied"""
    pass


class InvalidCodepoint(IDNAError):
    """Exception when a disallowed or unallocated codepoint is used"""
    pass


class InvalidCodepointContext(IDNAError):
    """Exception when the codepoint is not valid in the context it is used"""
    pass


def _combining_class(cp: int) -> int:
    v = unicodedata.combining(chr(cp))
    if v == 0:
        if not unicodedata.name(chr(cp)):
            raise ValueError("Unknown character in unicodedata")
    return v


def _is_script(cp: str, script: str) -> bool:
    return intranges_contain(ord(cp), idnadata.scripts[script])


def _punycode(s: str) -> bytes:
    return s.encode("punycode")


def _unot(s: int) -> str:
    return f"U+{s:04X}"


def valid_label_length(label: Union[bytes, str]) -> bool:
    return len(label) <= 63


def valid_string_length(label: Union[bytes, str],
                        trailing_dot: bool) -> bool:
    limit = 254 if trailing_dot else 253
    return len(label) <= limit


def check_bidi(label: str, check_ltr: bool = False) -> bool:
    bidi_label = False

    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)
        if direction == "":
            raise IDNABidiError(
                f"Unknown directionality in label {label!r} "
                f"at position {idx}"
            )
        if direction in ["R", "AL", "AN"]:
            bidi_label = True

    if not bidi_label and not check_ltr:
        return True

    direction = unicodedata.bidirectional(label[0])
    if direction in ["R", "AL"]:
        rtl = True
    elif direction == "L":
        rtl = False
    else:
        raise IDNABidiError(
            f"First codepoint in label {label!r} must be "
            "directionality L, R or AL"
        )

    valid_ending = False
    number_type: Optional[str] = None

    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)

        if rtl:
            if direction not in [
                "R", "AL", "AN", "EN", "ES", "CS",
                "ET", "ON", "BN", "NSM",
            ]:
                raise IDNABidiError(
                    f"Invalid direction at position {idx} "
                    "in RTL label"
                )

            if direction in ["R", "AL", "EN", "AN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False

            if direction in ["AN", "EN"]:
                if not number_type:
                    number_type = direction
                elif number_type != direction:
                    raise IDNABidiError(
                        "Cannot mix numeral types in RTL label"
                    )
        else:
            if direction not in [
                "L", "EN", "ES", "CS", "ET",
                "ON", "BN", "NSM",
            ]:
                raise IDNABidiError(
                    f"Invalid direction at position {idx} "
                    "in LTR label"
                )

            if direction in ["L", "EN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False

    if not valid_ending:
        raise IDNABidiError(
            "Label ends with illegal codepoint directionality"
        )

    return True


def check_initial_combiner(label: str) -> bool:
    if unicodedata.category(label[0])[0] == "M":
        raise IDNAError(
            "Label begins with an illegal combining character"
        )
    return True


def check_hyphen_ok(label: str) -> bool:
    if label[2:4] == "--":
        raise IDNAError(
            "Label has disallowed hyphens in 3rd and 4th position"
        )
    if label[0] == "-" or label[-1] == "-":
        raise IDNAError(
            "Label must not start or end with a hyphen"
        )
    return True


def check_nfc(label: str) -> None:
    if unicodedata.normalize("NFC", label) != label:
        raise IDNAError("Label must be in Normalization Form C")


def valid_contextj(label: str, pos: int) -> bool:
    cp_value = ord(label[pos])

    if cp_value == 0x200C:
        if pos > 0 and _combining_class(
            ord(label[pos - 1])
        ) == _virama_combining_class:
            return True

        ok = False
        for i in range(pos - 1, -1, -1):
            joining_type = idnadata.joining_types.get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            if joining_type in [ord("L"), ord("D")]:
                ok = True
                break
            break

        if not ok:
            return False

        ok = False
        for i in range(pos + 1, len(label)):
            joining_type = idnadata.joining_types.get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            if joining_type in [ord("R"), ord("D")]:
                ok = True
                break
            break
        return ok

    if cp_value == 0x200D:
        return (
            pos > 0 and
            _combining_class(ord(label[pos - 1]))
            == _virama_combining_class
        )

    return False


def valid_contexto(label: str, pos: int,
                   exception: bool = False) -> bool:
    cp_value = ord(label[pos])

    if cp_value == 0x00B7:
        return (
            0 < pos < len(label) - 1 and
            ord(label[pos - 1]) == 0x006C and
            ord(label[pos + 1]) == 0x006C
        )

    if cp_value == 0x0375:
        return (
            pos < len(label) - 1 and
            len(label) > 1 and
            _is_script(label[pos + 1], "Greek")
        )

    if cp_value in (0x05F3, 0x05F4):
        return pos > 0 and _is_script(label[pos - 1], "Hebrew")

    if cp_value == 0x30FB:
        return any(
            _is_script(cp, "Hiragana")
            or _is_script(cp, "Katakana")
            or _is_script(cp, "Han")
            for cp in label if cp != "\u30fb"
        )

    if 0x660 <= cp_value <= 0x669:
        return not any(
            0x6F0 <= ord(cp) <= 0x06F9 for cp in label
        )

    if 0x6F0 <= cp_value <= 0x6F9:
        return not any(
            0x660 <= ord(cp) <= 0x0669 for cp in label
        )

    return False
