"""Extract checksum-valid UK VAT candidates while preserving page evidence."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

VAT_PATTERN = re.compile(
    r"(?ix)(?<![A-Z0-9])(?:VAT(?:\s+(?:REGISTRATION|REG|NO|NUMBER))?\s*[:#.-]?\s*)?"
    r"(?:GB\s*)?(\d(?:[ .-]?\d){8})(?!\d)"
)
LABEL_PATTERN = re.compile(r"(?i)\bVAT(?:\s+(?:REGISTRATION|REG|NO|NUMBER))?\b")
OUTPUT_FIELDS = ["company_number", "company_name", "postcode", "website", "page_url", "vat_number",
                 "checksum_valid", "label_nearby", "evidence"]


def clean_vat(value: str) -> str:
    return re.sub(r"\D", "", value)


def valid_uk_vat_checksum(value: str) -> bool:
    """Validate standard and historic 55-offset nine-digit schemes."""
    digits = clean_vat(value)
    if len(digits) != 9:
        return False
    body_sum = sum(int(digits[index]) * (8 - index) for index in range(7))
    supplied = int(digits[-2:])
    standard = (97 - (body_sum % 97)) % 97
    historic = (97 - ((body_sum + 55) % 97)) % 97
    return supplied in {standard, historic}


def extract_candidates(text: str, context_chars: int = 80) -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for match in VAT_PATTERN.finditer(text or ""):
        vat = clean_vat(match.group(1))
        start, end = max(0, match.start() - context_chars), min(len(text), match.end() + context_chars)
        labelled = bool(LABEL_PATTERN.search(text[max(0, match.start() - 35):match.end()]))
        candidate: dict[str, object] = {
            "vat_number": vat,
            "checksum_valid": valid_uk_vat_checksum(vat),
            "label_nearby": labelled,
            "evidence": re.sub(r"\s+", " ", text[start:end]).strip(),
        }
        previous = found.get(vat)
        if previous is None or (labelled and not previous["label_nearby"]):
            found[vat] = candidate
    return list(found.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/crawl_results.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/vat_candidates.csv"))
    parser.add_argument("--include-invalid", action="store_true")
    parser.add_argument("--include-unlabelled", action="store_true",
                        help="include checksum-valid digit sequences without a nearby VAT label")
    args = parser.parse_args()
    output: list[dict[str, object]] = []
    with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            for candidate in extract_candidates(row.get("text", "")):
                if not args.include_invalid and not candidate["checksum_valid"]:
                    continue
                if not args.include_unlabelled and not candidate["label_nearby"]:
                    continue
                output.append({"company_number": row.get("company_number", ""),
                               "company_name": row.get("company_name", ""),
                               "postcode": row.get("postcode", ""),
                               "website": row.get("website", ""), "page_url": row.get("page_url", ""),
                               **candidate})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(output)
    print(f"candidate_rows={len(output)} unique_vat_numbers={len({r['vat_number'] for r in output})}")


if __name__ == "__main__":
    main()
