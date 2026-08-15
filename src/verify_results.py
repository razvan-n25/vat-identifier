"""Verify VAT candidates with authenticated HMRC API and score entity agreement."""

from __future__ import annotations

import argparse
import csv
import os
import re
import time
from pathlib import Path

import requests
from rapidfuzz.fuzz import ratio

API_URL = "https://api.service.hmrc.gov.uk/organisations/vat/check-vat-number/lookup/{vat}"
FIELDS = ["company_number", "company_name", "postcode", "website", "page_url", "vat_number", "hmrc_valid",
          "hmrc_name", "hmrc_address", "name_score", "postcode_match", "decision", "verification_method",
          "checked_at", "http_status", "error"]
SUFFIXES = {"limited", "ltd", "plc", "llp", "company", "co"}


def normalise_name(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", (value or "").casefold())
    return " ".join(word for word in words if word not in SUFFIXES)


def postcode(value: str) -> str:
    matches = re.findall(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", (value or "").upper())
    return re.sub(r"\s", "", matches[-1]) if matches else ""


def classify(company_name: str, company_postcode: str, hmrc_name: str, hmrc_address: str) -> tuple[float, bool, str]:
    score = round(ratio(normalise_name(company_name), normalise_name(hmrc_name)), 1)
    target_postcode, returned_postcode = postcode(company_postcode), postcode(hmrc_address)
    postcodes_agree = bool(target_postcode and returned_postcode and target_postcode == returned_postcode)
    if score >= 90 and postcodes_agree:
        decision = "VERIFIED_MATCH"
    elif score < 60 and target_postcode and returned_postcode and not postcodes_agree:
        decision = "REJECT_WRONG_ENTITY"
    else:
        decision = "MANUAL_REVIEW"
    return score, postcodes_agree, decision


def verify(vat: str, token: str, timeout: float) -> tuple[int, dict[str, object]]:
    response = requests.get(API_URL.format(vat=vat), headers={"Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.hmrc.2.0+json"}, timeout=timeout)
    if response.status_code == 404:
        return response.status_code, {}
    response.raise_for_status()
    return response.status_code, response.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/vat_candidates.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/verified_results.csv"))
    parser.add_argument("--token-env", default="HMRC_ACCESS_TOKEN")
    parser.add_argument("--delay", type=float, default=0.35, help="seconds; stays below standard 3 req/s")
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()
    token = os.environ.get(args.token_env)
    if not token:
        parser.error(f"set {args.token_env}; HMRC API v2 requires an OAuth access token")

    with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
        candidates = list(csv.DictReader(stream))
    output = []
    for row in candidates:
        result = {field: "" for field in FIELDS}
        result["verification_method"] = "HMRC_API_V2"
        result.update({field: row.get(field, "") for field in
                       ("company_number", "company_name", "postcode", "website", "page_url", "vat_number")})
        try:
            status, payload = verify(row["vat_number"], token, args.timeout)
            result["http_status"] = status
            result["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            target = payload.get("target", {})
            result["hmrc_valid"] = bool(target)
            if target:
                address = ", ".join(str(value) for value in target.get("address", {}).values() if value)
                score, postcode_match, decision = classify(row.get("company_name", ""), row.get("postcode", ""),
                                                            str(target.get("name", "")), address)
                result.update({"hmrc_name": target.get("name", ""), "hmrc_address": address,
                               "name_score": score, "postcode_match": postcode_match, "decision": decision})
            else:
                result["decision"] = "REJECT_INVALID_VAT"
        except requests.RequestException as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["decision"] = "VERIFICATION_ERROR"
        output.append(result)
        time.sleep(args.delay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    accepted = sum(row["decision"] == "VERIFIED_MATCH" for row in output)
    print(f"candidates={len(output)} accepted={accepted}")


if __name__ == "__main__":
    main()
