"""Fill the official government PDFs from the onboarding profile.

Adapted from Richard's `moneyfinder/form-filling/demo_forms.py` (pypdf AcroForm
fill, no submit). The blank forms are cached under `fixtures/forms/`; the filled
PDF is written under `data/forms/` and served as a real download.
"""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

FORMS = {
    "ben_it636": {"code": "IT-636", "file": "IT-636.pdf"},
    "ben_it212": {"code": "IT-212", "file": "IT-212.pdf"},
    "ben_it643": {"code": "IT-643", "file": "IT-643.pdf"},
    "ben_8846": {"code": "8846", "file": "8846.pdf"},
}


class PdfFillError(RuntimeError):
    pass


def _profile(store) -> dict[str, str]:
    return {f["key"]: (f.get("value") or "").strip() for f in store.onboarding_fields()}


def _identity(store) -> tuple[str, str, str]:
    p = _profile(store)
    name = p.get("legal_name") or store.business.get("legal_name") or "Gowanus Kettle Brewing Co. LLC"
    ein = p.get("ein") or "00-4271985"
    addr = p.get("address") or "417 Sackett Street, Brooklyn, NY 11231"
    return name, ein, addr


def values_for(benefit_id: str, store) -> dict[str, str]:
    name, ein, addr = _identity(store)
    p = _profile(store)
    year = p.get("tax_year") or "2025"
    if benefit_id == "ben_it636":
        return {
            "date_begin": f"01/01/{year}", "date_end": f"12/31/{year}", "names_return": name, "ID_num": ein,
            "lineA": "/Yes", "lineB": "/Yes", "lineB_distributor": name, "lineB_EIN": ein, "lineB_SLA": "1319027",
            "lineC1": "/Yes", "lineC2": "/No", "lineC3": "/No", "lineC4": "/No",
            "SchB_P1_A1": addr, "SchB_P1_B1": "96,224", "line1": "96,224", "line2": "96,224",
            "line3": "13,471", "line8": "13,471",
        }
    if benefit_id == "ben_it212":
        return {
            "names": name, "type of business": "Brewery (manufacturing)", "id number": ein,
            "business began": "03/11/2019", "location of prop": addr, "NAICS code": "312120",
            "1 dollars": "7,460", "9 dollars": "7,460", "11 dollars": "7,460", "13 dollars": "7,460",
            "15a dollars": "7,460",
        }
    if benefit_id == "ben_it643":
        return {
            "Name": name, "ID_num": ein, "LineA": "/Yes", "LineB": ein, "LineC": "2", "LineD": "/Yes",
            "P1_First nameRow1": "Darnell", "P1_MIRow1": "R", "P1_Last nameRow1": "Reyes",
            "P1__SSN1": "XXX-XX-4417", "P1_Emp_periodRow1": "05/27/25-12/31/25", "P1_Wages1": "52,000",
            "P1_ColE1": "7,800", "P1_ColF1": "7,800",
            "P1_First nameRow2": "Keisha", "P1_MIRow2": "M", "P1_Last nameRow2": "Monroe",
            "P1__SSN2": "XXX-XX-2093", "P1_Emp_periodRow2": "08/11/25-12/31/25", "P1_Wages2": "48,500",
            "P1_ColE2": "7,275", "P1_ColF2": "7,275",
            "Line1a": "15,075", "Line1": "15,075",
        }
    if benefit_id == "ben_8846":
        return {
            "f1_1[0]": name, "f1_2[0]": ein, "f1_3[0]": "148,600", "f1_4[0]": "21,400",
            "f1_5[0]": "127,200", "f1_6[0]": "9,731", "f1_8[0]": "9,731",
        }
    raise PdfFillError(f"no PDF mapping for {benefit_id}")


def _short(name) -> str:
    return str(name).split(".")[-1]


def _fill(src: Path, values: dict[str, str], dest: Path) -> list[str]:
    writer = PdfWriter(clone_from=PdfReader(src))
    texts = {k: v for k, v in values.items() if not v.startswith("/")}
    checks = {k: v for k, v in values.items() if v.startswith("/")}
    found: set[str] = set()
    for page in writer.pages:
        names = set()
        for annot in page.get("/Annots") or []:
            annot = annot.get_object()
            parent = annot.get("/Parent").get_object() if annot.get("/Parent") else None
            field = _short(annot.get("/T") or (parent or {}).get("/T") or "")
            names.add(field)
            if field in checks:
                states = list((annot.get("/AP") or {}).get("/N", {}).keys())
                on = checks[field] in states
                annot[NameObject("/AS")] = NameObject(checks[field] if on else "/Off")
                (parent or annot)[NameObject("/V")] = NameObject(checks[field])
                found.add(field)
        page_texts = {k: v for k, v in texts.items() if k in names}
        if page_texts:
            writer.update_page_form_field_values(page, page_texts, auto_regenerate=False)
            found |= set(page_texts)
    writer.set_need_appearances_writer(True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as fh:
        writer.write(fh)
    return sorted(set(values) - found)


def build(benefit_id: str, store) -> Path:
    spec = FORMS.get(benefit_id)
    if spec is None:
        raise PdfFillError(f"no official PDF mapped for {benefit_id}")
    blank = Path(store.root) / "fixtures" / "forms" / spec["file"]
    if not blank.is_file():
        raise PdfFillError(f"blank form missing: {blank}")
    dest = Path(store.data) / "forms" / f"{spec['code']}-filled.pdf"
    missing = _fill(blank, values_for(benefit_id, store), dest)
    if missing:
        raise PdfFillError(f"{spec['code']}: fields not found {missing}")
    return dest
