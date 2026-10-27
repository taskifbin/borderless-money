"""Intent Parser — multilingual (Bengali / Arabic / English), rule-based.

Designed for low-literacy, voice-first users: extracts amount, currency,
payout rail and recipient relation from a raw transcript. Deterministic and
dependency-free; the LLM layer may refine it later, but the demo never
depends on a model to parse its own happy-path sentence.
"""
import re

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_NUMBER_WORDS = {
    # english
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "twenty": 20, "fifty": 50, "hundred": 100,
    # banglish / bengali
    "ek": 1, "এক": 1, "dui": 2, "দুই": 2, "tin": 3, "তিন": 3, "char": 4, "চার": 4,
    "panch": 5, "পাঁচ": 5, "pch": 5, "dash": 10, "দশ": 10, "sho": 100, "শত": 100,
    # arabic (transliterated)
    "wahid": 1, "ithnayn": 2, "thalatha": 3, "arbaa": 4, "khamsa": 5,
}
_THOUSAND_WORDS = {"thousand", "hajar", "হাজার", "hazár", "alf", "ألف"}

_CURRENCY_WORDS = {
    "AED": {"dirham", "dirhams", "diram", "dirhem", "aed", "درهم", "دراهم", "dhiram"},
    "BDT": {"taka", "takas", "tk", "bdt", "টাকা"},
}

_PAYOUT_WORDS = {
    "BKASH": {"bkash", "b-kash", "বিকাশ", "bikash"},
    "NAGAD": {"nagad", "নগদ"},
    "BANK": {"bank", "ব্যাংক", "bangk", "account", "হিসাব", "بنك"},
}

_RELATIONS = {
    "mother": "Mother", "mom": "Mother", "mum": "Mother",
    "father": "Father", "dad": "Father",
    "wife": "Wife", "husband": "Husband",
    "brother": "Brother", "sister": "Sister",
    "son": "Son", "daughter": "Daughter",
    "মা": "Mother", "মায়ের": "Mother", "মাকে": "Mother", "আম্মু": "Mother", "আম্মুকে": "Mother",
    "বাবা": "Father", "আব্বু": "Father", "আব্বুকে": "Father", "বাবার": "Father",
    "বউ": "Wife", "স্ত্রী": "Wife", "স্ত্রীর": "Wife",
    "ভাই": "Brother", "ভাইকে": "Brother", "ভাইয়ের": "Brother",
    "বোন": "Sister", "বোনকে": "Sister", "বোনের": "Sister",
    "ছেলে": "Son", "ছেলেকে": "Son", "ছেলের": "Son",
    "মেয়ে": "Daughter", "মেয়েকে": "Daughter", "মেয়ের": "Daughter",
    "أمي": "Mother", "والدتي": "Mother", "والدة": "Mother", "والدي": "Father", "أبي": "Father",
}

# Deadline phrases -> hours. These mappings are DEMO ASSUMPTIONS (no public
# standard exists for what "tonight" means operationally); they are documented
# here so the behavior is inspectable. Explicit "within N hours/days" always
# wins over the keyword mappings.
_URGENT_DEADLINE = {"urgent", "urgently", "asap", "immediately", "right now",
                    "jati", "এখুনি", "এখনই", "فورا", "حالا"}
_TODAY_DEADLINE = {"today", "tonight", "this evening", "ajke", "aj",
                   "আজকে", "আজ", "আজকের", "اليوم", "الليلة"}
_TOMORROW_DEADLINE = {"tomorrow", "tomarrow", "kal", "kalex", "আগামীকাল",
                      "কাল", "আগামী", "غدا", "غداً", "بكرة"}


def _extract_deadline_hours(text: str) -> float | None:
    """Deadline as arrival-hours ceiling, or None when no deadline is voiced."""
    normalized = text.translate(_BN_DIGITS).translate(_AR_DIGITS).lower()
    m = re.search(r"within\s+(\d+(?:\.\d+)?)\s*(hours?|hrs?|days?|din|দিন)", normalized)
    if m:
        value = float(m.group(1))
        unit = m.group(2)
        return value * 24.0 if unit.startswith(("day", "din", "দিন")) else value
    for words, hours in (
        (_URGENT_DEADLINE, 3.0),
        (_TOMORROW_DEADLINE, 24.0),
        (_TODAY_DEADLINE, 12.0),
    ):
        for w in words:
            if w.isascii():
                if re.search(rf"(^|\W){re.escape(w)}(\W|$)", normalized):
                    return hours
            elif w in normalized:
                return hours
    return None


def _detect_language(text: str) -> str:
    if re.search(r"[\u0980-\u09FF]", text):
        return "bn"
    if re.search(r"[\u0600-\u06FF]", text):
        return "ar"
    return "en"


_THOUSAND_RE = r"(?:thousand|hajar|হাজার|alf|ألف)"


def _extract_amount(text: str) -> float | None:
    normalized = text.translate(_BN_DIGITS).translate(_AR_DIGITS).lower()
    # digits followed by a thousand word: "2 hajar", "5 thousand", "٣ alf"
    m = re.search(rf"(\d[\d,]*(?:\.\d+)?)\s*{_THOUSAND_RE}", normalized)
    if m:
        return float(m.group(1).replace(",", "")) * 1000.0
    # plain digits: "1,000 dirhams"
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", normalized)
    if m:
        return float(m.group(1).replace(",", ""))
    # word numbers: "ek hajar" / "one thousand" / bare "hajar"
    words = re.findall(r"[\w\u0980-\u09FF\u0600-\u06FF]+", normalized)
    for i, w in enumerate(words):
        if w in _THOUSAND_WORDS and i > 0 and words[i - 1] in _NUMBER_WORDS:
            return _NUMBER_WORDS[words[i - 1]] * 1000.0
        if w in _THOUSAND_WORDS:  # bare "hajar" = 1,000
            return 1000.0
    return None


def _extract_currency(text: str) -> str | None:
    normalized = text.lower()
    for code, words in _CURRENCY_WORDS.items():
        if any(w in normalized for w in words):
            return code
    return None


def _extract_payout(text: str) -> str | None:
    normalized = text.lower()
    for code, words in _PAYOUT_WORDS.items():
        if any(w in normalized for w in words):
            return code
    return None


def _extract_recipient(text: str) -> str | None:
    m = re.search(r"\bmy\s+(mother|mom|mum|father|dad|wife|husband|brother|sister|son|daughter)'?s?\b",
                  text, re.IGNORECASE)
    if m:
        return _RELATIONS[m.group(1).lower()]
    # longest tokens first: 'আমার' contains 'মা', so 'বোনকে' must win over 'মা'
    for token, relation in sorted(_RELATIONS.items(), key=lambda kv: len(kv[0]), reverse=True):
        if token.isascii():
            if re.search(rf"(^|\W){re.escape(token)}(\W|$)", text, re.IGNORECASE):
                return relation
        elif token in text:  # Bengali/Arabic: substring (word boundaries don't apply)
            return relation
    # Bare proper-noun recipient: "… to <Name> via bkash" / "… to <Name>".
    # A name that lands in free text MUST be screened, not silently replaced
    # by the demo persona — screening the wrong name is how holds get missed.
    m = re.search(
        r"\bto\s+((?:[A-Z][a-z]+)(?:\s+(?:[A-Z][a-z]+|bin|binte|ibn|al)){0,3})\b"
        r"(?=\s+(?:via|using|through|on|by)\b|\s*$|[,.!?]|$)",
        text)
    if m:
        candidate = m.group(1).strip()
        # reject corridor/payout words that merely look like names
        if candidate.lower() not in {"bkash", "nagad", "bank", "wallet", "dhaka", "bangladesh"}:
            return candidate
    return None


def parse_intent(text: str, default_corridor: str = "AED_TO_BDT") -> dict:
    """Transcript -> ParsedIntent (see docs/api-contracts.md)."""
    text = (text or "").strip()
    amount = _extract_amount(text)
    currency = _extract_currency(text)
    payout = _extract_payout(text)
    recipient = _extract_recipient(text)
    language = _detect_language(text)
    deadline_hours = _extract_deadline_hours(text)

    defaults_applied = []
    if currency is None:
        currency = "AED"  # demo corridor source currency
        defaults_applied.append("currency")

    confidence = 0.45
    if amount is not None:
        confidence += 0.25
    if currency and "currency" not in defaults_applied:
        confidence += 0.10
    if payout:
        confidence += 0.05
    if recipient:
        confidence += 0.05
    if deadline_hours is not None:
        confidence += 0.05

    return {
        "raw_text": text,
        "amount": amount,
        "source_currency": currency,
        "dest_currency": "BDT",
        "recipient": recipient,
        "payout_method": payout,
        "deadline_hours": deadline_hours,
        "corridor": default_corridor,
        "language_detected": language,
        "confidence": round(confidence, 2),
        "defaults_applied": defaults_applied,
    }
