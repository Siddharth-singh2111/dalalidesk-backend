"""
GST block of a dalali tax invoice.

Rules (DM, Oct 2026 — from Dhruv Textile invoice GST-15):
  taxable      = the memos' commission (or the typed amount on a Part entry)
  tax          = taxable x rate; IGST when the billing firm's state differs from
                 the place of supply (the supplier's state), else CGST + SGST at
                 half the rate each
  grand total  = taxable + tax rounded to the nearest rupee; the difference is
                 the "Rounded off" line
Example GST-15: 31,668 @ 18% IGST = 5,700.24 -> 37,368.24 -> 37,368 (round off -0.24).

Standard library only so it can be tested on its own.
"""
from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

SAC_CODE = "996111"  # Services provided for a fee or commission (trade agents)
ALLOWED_RATES = (Decimal("0"), Decimal("5"), Decimal("18"))

STATE_NAMES: Dict[str, str] = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory",
}

_GSTIN_RE = re.compile(r"^(\d{2})[A-Z0-9]{13}$")

# PIN code -> GST state, for a supplier with no GSTIN. Three-digit prefixes
# that differ from their two-digit block are listed first.
_PIN3 = {
    "160": "04", "194": "38", "403": "30", "605": "34", "737": "11", "744": "35",
    "246": "05", "248": "05", "249": "05", "263": "05",
    "500": "36", "501": "36", "502": "36", "503": "36", "504": "36", "505": "36",
    "506": "36", "507": "36", "508": "36", "509": "36",
    "790": "12", "791": "12", "792": "12", "793": "17", "794": "17", "795": "14",
    "796": "15", "797": "13", "798": "13", "799": "16",
    "814": "20", "815": "20", "816": "20", "822": "20", "825": "20", "826": "20",
    "827": "20", "828": "20", "829": "20", "831": "20", "832": "20", "833": "20",
    "834": "20", "835": "20",
}
_PIN2 = {
    "11": "07", "12": "06", "13": "06", "14": "03", "15": "03", "16": "03", "17": "02",
    "18": "01", "19": "01", "20": "09", "21": "09", "22": "09", "23": "09", "24": "09",
    "25": "09", "26": "09", "27": "09", "28": "09", "30": "08", "31": "08", "32": "08",
    "33": "08", "34": "08", "36": "24", "37": "24", "38": "24", "39": "24", "40": "27",
    "41": "27", "42": "27", "43": "27", "44": "27", "45": "23", "46": "23", "47": "23",
    "48": "23", "49": "22", "51": "37", "52": "37", "53": "37", "56": "29", "57": "29",
    "58": "29", "59": "29", "60": "33", "61": "33", "62": "33", "63": "33", "64": "33",
    "67": "32", "68": "32", "69": "32", "70": "19", "71": "19", "72": "19", "73": "19",
    "74": "19", "75": "21", "76": "21", "77": "21", "78": "18", "80": "10", "81": "10",
    "82": "10", "83": "10", "84": "10", "85": "10",
}

TWO = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


def state_from_gstin(gstin: Optional[str]) -> Optional[str]:
    if not gstin:
        return None
    m = _GSTIN_RE.match(re.sub(r"\s+", "", gstin).upper())
    if not m or m.group(1) not in STATE_NAMES:
        return None
    return m.group(1)


def state_from_pin(pin: Optional[str]) -> Optional[str]:
    digits = re.sub(r"\D", "", pin or "")
    if len(digits) != 6:
        return None
    return _PIN3.get(digits[:3]) or _PIN2.get(digits[:2])


def supplier_state(gstin: Optional[str], pin_code: Optional[str]) -> Dict[str, Optional[str]]:
    """Place of supply for a supplier: from its GSTIN, else its PIN code."""
    code = state_from_gstin(gstin)
    if code:
        return {"code": code, "source": "gstin"}
    code = state_from_pin(pin_code)
    if code:
        return {"code": code, "source": "pin_code"}
    return {"code": None, "source": None}


def normalize_rate(rate) -> Decimal:
    r = Decimal(str(rate))
    if r not in ALLOWED_RATES:
        raise ValueError("GST rate must be 18%, 5% or None")
    return r


def compute(taxable, rate, firm_state: Optional[str], place_of_supply: Optional[str]) -> Dict[str, Decimal]:
    """
    Work out the GST block. Unknown states count as inter-state (IGST), the
    safe default for a Kanpur firm billing an out-of-state supplier.
    """
    taxable = money(taxable)
    rate = normalize_rate(rate)
    intra = bool(firm_state) and firm_state == place_of_supply
    cgst = sgst = igst = Decimal("0.00")
    if rate > 0:
        if intra:
            half = rate / 2
            cgst = money(taxable * half / 100)
            sgst = money(taxable * half / 100)
        else:
            igst = money(taxable * rate / 100)
    exact = taxable + cgst + sgst + igst
    grand = exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return {
        "taxable_amount": taxable,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "round_off": money(grand - exact),
        "grand_total": money(grand),
        "intra_state": intra,
    }


_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
         "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
         "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three(n: int) -> str:
    h, rest = divmod(n, 100)
    parts = []
    if h:
        parts.append(_ONES[h] + " Hundred")
    if rest:
        parts.append(_two(rest))
    return " ".join(parts)


def amount_in_words(amount) -> str:
    """Indian numbering: 37368 -> 'Rupees Thirty Seven Thousand Three Hundred Sixty Eight Only'."""
    total = money(amount)
    rupees = int(total)
    paise = int((total - rupees) * 100)
    if rupees == 0 and paise == 0:
        return "Rupees Zero Only"
    parts = []
    crore, rupees = divmod(rupees, 10_000_000)
    lakh, rupees = divmod(rupees, 100_000)
    thousand, rupees = divmod(rupees, 1000)
    if crore:
        parts.append(_three(crore) if crore < 1000 else amount_in_words(crore)[7:-5])
        parts.append("Crore")
    if lakh:
        parts += [_two(lakh), "Lakh"]
    if thousand:
        parts += [_two(thousand), "Thousand"]
    if rupees:
        parts.append(_three(rupees))
    words = "Rupees " + " ".join(p for p in parts if p)
    if paise:
        words += " and " + _two(paise) + " Paise"
    return words + " Only"


_SUFFIX_RE = re.compile(r"^(.*?)(\d+)$")


def next_invoice_number(last: Optional[str], default_prefix: str = "GST-") -> str:
    """'GST-15' -> 'GST-16'; keeps zero padding ('INV/007' -> 'INV/008')."""
    if not last:
        return f"{default_prefix}1"
    m = _SUFFIX_RE.match(last.strip())
    if not m:
        return f"{last.strip()}-1"
    prefix, digits = m.groups()
    return f"{prefix}{str(int(digits) + 1).zfill(len(digits))}"


def financial_year(d) -> str:
    """Indian financial year of a date, e.g. 2026-09-11 -> '2026-27'."""
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{str(start + 1)[-2:]}"
