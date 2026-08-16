# Descoperirea numerelor VAT din Regatul Unit folosind surse web publice

## Abordare

Problema are 2 etape:
1. **Descoperire**: Găsesc website-ul oficial al companiei
2. **Verificare**: Extrag VAT din website, verific cu HMRC și confirm identitatea

Un VAT e valid doar dacă:
- Trece verificarea checksum (structură matematică)
- HMRC confirmă că e activ
- Numele și adresa corespund exact cu Companies House

## Rezumat executiv

Am testat pe **60 de companii** selectate aleatoriu fără bias. Rezultat: **2 VAT-uri verificate = 3,3% coverage**.

Un al treilea candidat a trecut checksum dar HMRC l-a respins ca invalid (nu e fals pozitiv acceptat).

**Concluzie**: Open web poate produce VAT-uri verificabile, dar la 3,3% coverage nu e viabil ca sursă principală. Blocajul nu e viteza crawlerului, ci găsirea website-ului oficial pentru fiecare companie.

### Tabel rezumat

| Etapă | Rezultat | % din 60 |
|---|---|---|
| Companii selectate | 60 | 100% |
| Website identificat (CONFIDENT/PROVISIONAL) | 10 | 16,7% |
| Pagini HTTP 200 extrase | 6 domenii | 10% |
| Candidați VAT unici (valid checksum) | 3 | 5% |
| Verificați și acceptați în HMRC | 2 | **3,3%** |

Ce înseamnă NO_CANDIDATE_FOUND? Doar că procesul nu a găsit VAT - nu că firma nu e înregistrată.

## Metodă

**Website discovery**: Manual (căutări Google, documente). De ce? Pentru că trebuie validată entitatea ("E acesta website-ul corect?"), nu doar accesată pagina.

**Pipeline** (8 etape):
1. Iau entitate din Companies House
2. Caut website oficial și documente de identitate
3. Crawl controlat (max 8 pagini/domeniu, respectez robots.txt, delays)
4. Extrag VAT din text
5. Validez checksum
6. Verific în HMRC
7. Compar nume + adresă cu Companies House
8. Accept / Respinge / Manual review

**Termeni**:
- **Candidat VAT**: număr extras, neacceptat
- **Checksum valid**: format OK, dar poate fi vechi/invalid/altei firme
- **HMRC-valid**: HMRC confirmă că e activ
- **Potrivire acceptată**: HMRC + identitate confirmă

## Eșantionare

**60 companii stratificate** pe 4 sectoare (15 fiecare):
- Producție
- Construcții
- Comerț
- Servicii (B2B)

**Algoritm**: Reservoir sampling, seed=42 (reproductibil).
**Sursă**: Companies House snapshot 1 august 2026.

Nu am selectat companii despre care știam că au website/VAT → nu ar fi viabil.

## Date și instrumente

- **Companies House**: Bun pentru eșantionare. Nu are VAT/website fields.
- **HMRC**: Verific VAT → primesc nume + adresă oficiale. API v2 necesită OAuth (nu aveam), am verificat manual pe <https://www.gov.uk/check-uk-vat-number>.
- **Procurement docs**: Mostly placeholder-uri `[NUMBER]`, puțini documente reale cu VAT.

## Rezultate pe cele 60 companii

### Website discovery (manual)
- 4 website-uri CONFIDENT
- 6 PROVISIONAL
- 3 AMBIGUOUS (excluse - brand înrudit sau adresă comună)
- 47 UNRESOLVED (nu am găsit)

Crawlerul a primit doar cele 10 domeniile sigure (CONFIDENT + PROVISIONAL).

### Crawl și extracție VAT

10 domenii → 49 cereri HTTP → 6 domenii cu succes (HTTP 200):
- 3 failed (DNS/conexiune)
- 1 exclus de robots.txt

Candidați extrași: **3 unici** (după deduplicare).

| VAT | Sursă | Checksum | HMRC |
|---|---|---|---|
| 316227425 | Nagle & Sisters | ✓ | ✗ INVALID |
| 861397010 | KEOPS privacy | ✓ | ✓ KEOPS LTD / WR11 4SN |
| 852761903 | Marketplace AMP footer | ✓ | ✓ MARKETPLACE AMP LTD / SN2 8BW |

Ambele VAT-uri acceptate verificate manual pe HMRC web (14 august 2026):
- Nume + adresă = match complet
- **0 rezultate fals pozitive**

### Cautare directă suplimentară

Am testat Google (nume juridic exact + "VAT") pe toate 60:
- 7 companii cu piste utile
- 4 apărute în PDF-uri (Gazette, liste locale)
- **0 VAT-uri noi** extrase

Concluzie: căutare generică nu ajută. Documente private (facturi) ar fi sursă bună, dar nu e open web.

## Cod

- `src/sample_companies.py`: Eșantionare stratificată reproductibilă
- `src/crawl_sites.py`: Crawler politicos (robots.txt, delays, same-host)
- `src/extract_vat.py`: Regex + checksum validation
- `src/verify_results.py`: HMRC v2 API (cod ready, manual verification executat)
- `tests/test_extraction.py`: 7 teste unit (all pass)

Run:
```powershell
.\.venv\Scripts\activate
python -m pytest -q
python src/crawl_sites.py
python src/extract_vat.py
$env:HMRC_ACCESS_TOKEN = "..."
python src/verify_results.py
```

Testat cu Python 3.12.10. Ultima rulare: `7 passed`.

## Acceptare și măsurare

O potrivire finală acceptată necesită:
- URL sursă + context text
- Checksum valid
- Răspuns HMRC valid
- Nume/adresă compatible
- Manual review pentru cazuri ambigue

Vocabular: `VERIFIED_MATCH`, `REJECT_INVALID_VAT`, `REJECT_WRONG_ENTITY`, `MANUAL_REVIEW`.

**Métrici**:
```
Coverage = VAT-uri acceptate / 60
False positives observate = 0 / 2 verificate (prea mic pentru garantie)
```

## Model de cost și scalare

**Blocaj principal**: Website discovery (47/60 = 78% niciun website găsit).

Pentru 40.000 furnizori, costul depinde de:
- Identificare domeniu (dataset sau search)
- HTTP requests (5-10 pagini/domeniu)
- PDF extraction + rendering
- HMRC API calls (numai candidați valid)
- Manual review (cazuri ambigue)

**Verdict**: NU ca open-web-only la 3,3%. DA dacă avem:
- Dataset companie-domeniu (cumpărat sau scraiat din surse cunoscute)
- SAU arhivă first-party (facturi interne cu VAT)
- SAU listă țintită (e.g., doar furnizori care dau facturi)

## Fișiere de rezultate

- `data/processed/sample_companies.csv`: 60 companii (reproducibil)
- `results/website_candidates.csv`: 60 rânduri cu status (CONFIDENT/PROVISIONAL/AMBIGUOUS/UNRESOLVED)
- `results/crawl_results.csv`: 50 pagini extrase de pe 10 domenii
- `results/vat_candidates.csv`: 10 candidați (dedup'd in 3 unici)
- `results/verified_results.csv`: 3 rânduri (2 VERIFIED_MATCH, 1 REJECT_INVALID_VAT)

## Lecții

- Puține companii publică VAT (doar 30% din paginile crawlate au VAT)
- Website discovery e bottleneck-ul (16,7% identificate)
- Conservative validation (HMRC + fuzzy match) necesară
- Fără first-party data sau lista de domenii, coverage e mic
- Metodologie transparentă (funnel) e esențială pentru credibilitate

---

**Status**: Proof-of-concept completat. Gata pentru discuție cu team pe viitor: cum obținem lista de domenii? Avem acces la facturi? Cât buget pentru solutie hibridă?
