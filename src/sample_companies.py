"""Draw a deterministic reservoir sample from Companies House bulk CSV files."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


OUTPUT_FIELDS = ["company_number", "company_name", "company_status", "company_category",
                 "address_line_1", "post_town", "county", "postcode", "sic_code_1", "sample_stratum",
                 "source_file"]

STRATA = {
    "manufacturing": tuple(f"{code:02d}" for code in range(10, 34)),
    "construction": ("41", "42", "43"),
    "wholesale_trade": ("45", "46"),
    "business_services": ("62", "69", "70", "71", "72", "73", "74"),
}


def pick(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row:
            return (row.get(name) or "").strip()
    return ""


def normalise_company(row: dict[str, str], source: str) -> dict[str, str]:
    return {
        "company_number": pick(row, "CompanyNumber", "company_number"),
        "company_name": pick(row, "CompanyName", "company_name"),
        "company_status": pick(row, "CompanyStatus", "company_status"),
        "company_category": pick(row, "CompanyCategory", "company_category"),
        "address_line_1": pick(row, "RegAddress.AddressLine1", "address_line_1"),
        "post_town": pick(row, "RegAddress.PostTown", "post_town"),
        "county": pick(row, "RegAddress.County", "county"),
        "postcode": pick(row, "RegAddress.PostCode", "postcode"),
        "sic_code_1": pick(row, "SICCode.SicText_1", "sic_code_1"),
        "sample_stratum": "",
        "source_file": source,
    }


def sic_prefix(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    return digits[:2]


def stratum_for(company: dict[str, str]) -> str | None:
    prefix = sic_prefix(company["sic_code_1"])
    return next((name for name, prefixes in STRATA.items() if prefix in prefixes), None)


def reservoir_sample(paths: list[Path], size: int, seed: int) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Draw equal-size reservoir samples across four supplier-relevant SIC strata."""
    rng = random.Random(seed)
    if size % len(STRATA):
        raise ValueError(f"sample size must be divisible by {len(STRATA)}")
    per_stratum = size // len(STRATA)
    samples: dict[str, list[dict[str, str]]] = {name: [] for name in STRATA}
    eligible = {name: 0 for name in STRATA}
    for path in paths:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
            for raw in csv.DictReader(stream):
                raw = {(key or "").strip(): value for key, value in raw.items()}
                company = normalise_company(raw, path.name)
                if company["company_status"] and company["company_status"].casefold() != "active":
                    continue
                if not company["company_number"] or not company["company_name"]:
                    continue
                stratum = stratum_for(company)
                if stratum is None:
                    continue
                company["sample_stratum"] = stratum
                eligible[stratum] += 1
                sample = samples[stratum]
                if len(sample) < per_stratum:
                    sample.append(company)
                else:
                    position = rng.randrange(eligible[stratum])
                    if position < per_stratum:
                        sample[position] = company
    sample = [company for stratum_sample in samples.values() for company in stratum_sample]
    sample.sort(key=lambda row: row["company_number"])
    return sample, eligible


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--size", type=int, default=60, help="must be divisible by four")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/processed/sample_companies.csv"))
    args = parser.parse_args()
    if args.size < 1:
        parser.error("--size must be positive")
    sample, population = reservoir_sample(args.inputs, args.size, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(sample)
    counts = ",".join(f"{name}={count}" for name, count in population.items())
    print(f"eligible_population[{counts}] sample_size={len(sample)} seed={args.seed}")


if __name__ == "__main__":
    main()
