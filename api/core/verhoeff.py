"""Verhoeff check digit and MPNG code helpers. Standard library only."""

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
PREFIX = "MPNG-"


def check_digit(num: str) -> str:
    """Return the Verhoeff check digit for a string of decimal digits."""
    if not num or not num.isascii() or not num.isdigit():
        raise ValueError("digits only")
    c = 0
    for i, d in enumerate(reversed(num)):
        c = _D[c][_P[(i + 1) % 8][int(d)]]
    return str(_INV[c])


def is_valid(num_with_check: str) -> bool:
    """Verify that a number with check digit satisfies the Verhoeff equation."""
    if not num_with_check or not num_with_check.isascii() or not num_with_check.isdigit():
        return False
    c = 0
    for i, d in enumerate(reversed(num_with_check)):
        c = _D[c][_P[i % 8][int(d)]]
    return c == 0


def make_code(sequence: int) -> str:
    """Build MPNG-<10 digit sequence>-<check digit> (17 chars)."""
    if not 0 < sequence < 10**10:
        raise ValueError("sequence out of range")
    body = f"{sequence:010d}"
    return f"{PREFIX}{body}-{check_digit(body)}"


def validate_code(code: str) -> bool:
    """True only for a well-formed 17-character code with a correct check digit."""
    if not isinstance(code, str) or len(code) != 17 or not code.startswith(PREFIX):
        return False
    body, sep, chk = code[5:15], code[15], code[16]
    if sep != "-" or not (body + chk).isascii() or not (body + chk).isdigit():
        return False
    return is_valid(body + chk)
