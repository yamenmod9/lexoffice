from __future__ import annotations

from functools import lru_cache

EGYPTIAN_GOVERNORATES = [
    "القاهرة",
    "الجيزة",
    "الإسكندرية",
    "الدقهلية",
    "البحر الأحمر",
    "البحيرة",
    "الفيوم",
    "الغربية",
    "الإسماعيلية",
    "المنوفية",
    "المنيا",
    "القليوبية",
    "الوادي الجديد",
    "السويس",
    "أسوان",
    "أسيوط",
    "بني سويف",
    "بورسعيد",
    "دمياط",
    "الشرقية",
    "جنوب سيناء",
    "كفر الشيخ",
    "مطروح",
    "الأقصر",
    "قنا",
    "شمال سيناء",
    "سوهاج",
]

_SUPREME_AND_SPECIAL_COURTS = [
    "محكمة النقض",
    "المحكمة الدستورية العليا",
    "مجلس الدولة - المحكمة الإدارية العليا",
    "مجلس الدولة - محكمة القضاء الإداري",
    "المحكمة الاقتصادية القاهرة",
    "المحكمة الاقتصادية الإسكندرية",
    "محكمة القضاء العسكري",
    "محكمة الجنايات",
    "محكمة الجنح المستأنفة",
    "محكمة الأمور المستعجلة",
    "محكمة التنفيذ المدني",
    "محكمة التنفيذ التجاري",
]

_APPEAL_COURTS = [
    "محكمة الاستئناف القاهرة",
    "محكمة الاستئناف الإسكندرية",
    "محكمة الاستئناف المنصورة",
    "محكمة الاستئناف أسيوط",
    "محكمة الاستئناف طنطا",
    "محكمة الاستئناف الإسماعيلية",
    "محكمة الاستئناف بني سويف",
]


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in items:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _governorate_courts(governorate: str) -> list[str]:
    return [
        f"محكمة {governorate} الابتدائية",
        f"محكمة الأسرة {governorate}",
        f"محكمة العمال {governorate}",
        f"مجلس الدولة - محكمة القضاء الإداري {governorate}",
        f"محكمة التنفيذ {governorate}",
    ]


@lru_cache(maxsize=1)
def get_egyptian_courts() -> tuple[str, ...]:
    courts: list[str] = []
    courts.extend(_SUPREME_AND_SPECIAL_COURTS)
    courts.extend(_APPEAL_COURTS)

    for governorate in EGYPTIAN_GOVERNORATES:
        courts.extend(_governorate_courts(governorate))

    # Preserve deterministic order while removing duplicates.
    return tuple(_dedupe_keep_order(courts))


@lru_cache(maxsize=1)
def get_egyptian_governorates() -> tuple[str, ...]:
    return tuple(EGYPTIAN_GOVERNORATES)


EGYPTIAN_COURTS = list(get_egyptian_courts())
