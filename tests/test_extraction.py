from src.extract_vat import extract_candidates, valid_uk_vat_checksum
from src.verify_results import classify, normalise_name


def make_standard_vat(prefix: str) -> str:
    total = sum(int(prefix[index]) * (8 - index) for index in range(7))
    return prefix + f"{(97 - total % 97) % 97:02d}"


def test_checksum_accepts_generated_standard_number():
    vat = make_standard_vat("1234567")
    assert valid_uk_vat_checksum(vat)


def test_checksum_rejects_wrong_check_digits():
    vat = make_standard_vat("1234567")
    wrong = vat[:-2] + f"{(int(vat[-2:]) + 1) % 97:02d}"
    assert not valid_uk_vat_checksum(wrong)


def test_extracts_spaced_labelled_number_with_evidence():
    vat = make_standard_vat("7654321")
    spaced = f"{vat[:3]} {vat[3:6]} {vat[6:]}"
    candidates = extract_candidates(f"Footer text. VAT registration number: GB {spaced}. Copyright.")
    assert candidates[0]["vat_number"] == vat
    assert candidates[0]["checksum_valid"] is True
    assert candidates[0]["label_nearby"] is True


def test_deduplicates_same_number_on_page():
    vat = make_standard_vat("2345678")
    assert len(extract_candidates(f"VAT {vat}; again VAT {vat}")) == 1


def test_name_normalisation_and_acceptance():
    assert normalise_name("J. Smith Building Services Limited") == "j smith building services"
    score, postcode_match, decision = classify(
        "J Smith Building Services Ltd", "SW1A 1AA",
        "J. SMITH BUILDING SERVICES LIMITED", "London, SW1A 1AA",
    )
    assert score == 100
    assert postcode_match is True
    assert decision == "accept"


def test_ambiguous_identity_goes_to_review():
    _, _, decision = classify("Alpha Engineering Ltd", "", "Alpha Holdings Limited", "Somewhere")
    assert decision == "manual_review"
