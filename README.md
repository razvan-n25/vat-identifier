# Descoperirea numerelor VAT din Regatul Unit folosind surse web publice


## Cum am gândit problema

Am tratat problema ca pe un exercițiu de descoperire + verificare, nu ca pe o căutare simplă de string-uri. Cadrul de lucru a fost următorul:

- am pornit de la o entitate legală din Companies House;
- am căutat dovezi publice despre website-ul companiei, nu despre VAT în sine;
- am extras candidați VAT din conținutul public;
- am filtrat numerele prin checksum și le-am verificat în HMRC;
- am verificat dacă numele și adresa returnate de HMRC corespund companiei din Companies House;
- am considerat că o asociere este validă numai dacă există dovadă de identitate și verificare autoritativă.

Aceasta înseamnă că, în proiectul nostru, un VAT nu este „valid” doar pentru că are formatul corect. O potrivire este acceptată numai dacă este confirmată de HMRC și corelată cu entitatea juridică corectă.

## Rezumat executiv

Am folosit un singur eșantion principal de 60 de companii, ales reproductibil, fără selecție după existența website-ului sau a VAT-ului. Din acest eșantion, procesul a confirmat 2 asocieri companie–VAT, adică o acoperire end-to-end de `2 / 60 = 3,3%`.

Un alt candidat a trecut checksum-ul, dar a fost respins de HMRC ca invalid. Nu au fost observate rezultate fals pozitive între cele două asocieri acceptate și verificate manual, dar eșantionul este prea mic pentru a afirma o precizie garantată în general.

Concluzia principală este că open web-ul poate produce asocieri VAT verificabile, dar nu susține încă promisiunea că poate completa singur cea mai mare parte a lacunelor din lista clientului. Blocajul principal nu a fost viteza crawlerului, ci identificarea corectă a website-ului companiei și a contextului de identitate.

### Proiectul pe scurt

| Întrebare | Răspuns măsurat |
|---|---|
| Câte companii conține eșantionul principal? | 60 |
| Cum au fost selectate? | Stratificat din Companies House, seed `42`, fără selecție după existența VAT |
| Câte domenii au fost suficient de sigure pentru crawling? | 10 |
| Câte domenii au returnat cel puțin o pagină HTTP 200? | 6 |
| Câți candidați unici au trecut checksum? | 3 |
| Câți au fost valizi în HMRC și atribuiți aceleiași companii? | 2 |
| Care este coverage-ul principal? | `2 / 60 = 3,3%` |
| Ce înseamnă lipsa unui rezultat? | Doar că procesul nu a găsit unul; nu dovedește că firma nu este înregistrată VAT |

## Întrebarea de cercetare

Pornind de la o înregistrare Companies House, pot descoperi un număr VAT pe web-ul public și pot demonstra, cu un risc suficient de mic de rezultate fals pozitive, că acesta aparține exact acelei entități juridice?

## Metodă

Website discovery a fost realizat manual ca parte a etapei de research: pentru fiecare companie din eșantion am identificat un website candidat sau am stabilit că nu există unul suficient de sigur pentru crawl. Lista rezultată din această cercetare a fost apoi folosită ca intrare pentru crawlerul automat. Acest design este intenționat: în această etapă, problema principală este validarea entității și a contextului, nu doar accesarea unei pagini.

Fluxul implementat și verificat în proof of concept este:

1. selectarea unei entități din Companies House;
2. identificarea website-ului oficial și păstrarea dovezilor de identitate;
3. accesarea controlată a unui număr limitat de pagini juridice sau de contact;
4. extragerea și normalizarea candidaților VAT;
5. respingerea numerelor care nu trec verificarea checksum;
6. verificarea numerelor rămase prin HMRC;
7. compararea numelui și adresei HMRC cu Companies House și cu dovezile din pagina-sursă;
8. acceptarea, respingerea ca entitate greșită sau trimiterea la verificare manuală.

`NO_CANDIDATE_FOUND` nu înseamnă niciodată `NOT_VAT_REGISTERED`. Poate însemna și că website-ul nu a fost găsit, site-ul nu a fost accesibil, numărul nu a fost publicat, un PDF nu a fost găsit sau crawlerul nu a ajuns la pagina relevantă.

Termenii folosiți în document:

- **candidat VAT**: un număr extras dintr-o sursă, încă neacceptat;
- **checksum valid**: numărul are o structură matematic posibilă, dar poate fi vechi, invalid sau al altei firme;
- **HMRC-valid**: HMRC confirmă faptul că numărul este activ/valid;
- **potrivire acceptată**: HMRC confirmă numărul, iar identitatea corespunde companiei analizate;
- **coverage**: potriviri acceptate împărțite la toate cele 60 de companii selectate.

## Eșantionare

### Un singur eșantion principal

Rezultatul oficial al proiectului se bazează exclusiv pe cele 60 de companii. Nu am creat o cohortă separată din firme despre care știam deja că au website sau publică VAT, deoarece aceasta ar fi crescut artificial rata de succes.

Metoda a fost dezvoltată incremental și apoi aplicată întregului eșantion de 60 de companii. Toate rezultatele principale se bazează pe numitorul complet de 60, iar toate sursele relevante au fost evaluate împotriva aceleiași cohorte. Testele suplimentare pe surse alternative au fost exploratorii și nu au modificat cifra principală a acoperirii `2/60`.

Sursă: snapshotul Companies House Free Company Data Product din 1 august 2026. Fișierul CSV-sursă nu este inclus în repository deoarece are aproximativ 2,8 GB.

Comanda folosită:

```powershell
python src/sample_companies.py data/raw/BasicCompanyDataAsOneFile-2026-08-01.csv `
  --size 60 --seed 42 --output data/processed/sample_companies.csv
```

Filtre și categorii:

- numai companii active;
- numărul și numele companiei sunt obligatorii;
- codul SIC principal trebuie să aparțină producției (10–33), construcțiilor (41–43), comerțului și reparării autovehiculelor/comerțului cu ridicata (45–46) sau anumitor servicii pentru companii (62, 69–74);
- au fost selectate uniform câte 15 companii din fiecare categorie prin reservoir sampling;
- seed aleatoriu: `42`.

Populațiile eligibile măsurate în snapshot au fost: 213.043 de înregistrări pentru producție, 506.399 pentru construcții, 272.579 pentru comerț cu ridicata și 893.631 pentru servicii destinate companiilor. Rezultatul conține 60 de înregistrări, câte 15 pentru fiecare categorie.

Acest design oferă diversitate între sectoare și evită selecția după rezultat. Totuși, nu poate fi declarat reprezentativ statistic pentru cei 40.000 de furnizori ai clientului, deoarece distribuția lor după sector, dimensiune și formă juridică nu este disponibilă. Cele 15 companii din fiecare categorie au aceeași pondere în experiment, chiar dacă sectoarele nu au aceeași pondere în populația Companies House sau în lista clientului.

Eșantionul de 60 este suficient pentru un proof of concept și pentru identificarea blocajelor, dar nu pentru o estimare precisă a coverage-ului. Cu resurse reale, următorul pas ar fi extinderea la 300–1.000 de companii prin **aceeași metodă**, fără filtrare după website sau VAT, ori rularea pe un eșantion din lista reală a clientului.

## Surse și constatări inițiale

### Datele agregate Companies House

Așteptare: un cadru complet pentru eșantionare și atribute de identitate. Rezultat: datele sunt utile pentru numărul companiei, numele juridic, adresa înregistrată, statut și codul SIC, dar nu conțin câmpuri pentru website sau VAT. Decizie: folosirea lor pentru eșantionare și verificarea entității, nu pentru descoperirea VAT. Lista oficială de câmpuri confirmă această limitare: <https://resources.companieshouse.gov.uk/toolsToHelp/pdf/freeDataProductDataset.pdf>.

O constatare practică a fost că unele antete CSV conțin spații la început, inclusiv ` CompanyNumber`. Scriptul de eșantionare elimină spațiile din numele câmpurilor înainte de mapare; în caz contrar, numerele companiilor ar deveni goale fără o eroare vizibilă.

### Instrumentul și API-ul HMRC

Așteptare: verificare autoritativă după descoperirea unui candidat. Rezultat: serviciul verifică un număr furnizat și returnează numele și adresa înregistrate, dar nu permite căutarea după numele companiei: <https://www.gov.uk/check-uk-vat-number>. API-ul v2 necesită credențiale OAuth cu acces restricționat aplicației, iar HMRC precizează că înregistrarea pentru producție durează aproximativ două săptămâni: <https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/vat-registered-companies-api/2.0/oas/page>.

Decizie: verificarea rămâne o etapă autentificată separată. Pentru acest proof of concept realizat într-un interval limitat pe un laptop personal, verificarea manuală este acceptabilă dacă dovezile sunt înregistrate; nu sunt însă justificate afirmații despre automatizarea în producție.

### Unde publicarea VAT este obligatorie — și de ce nu rezolvă descoperirea web

Ghidul oficial HMRC pentru facturi precizează că o factură VAT trebuie să includă numele, adresa și numărul de înregistrare VAT al furnizorului: <https://www.gov.uk/guidance/vat-guide-notice-700#section16>. După înregistrare, compania trebuie să includă numărul VAT pe facturile emise: <https://www.gov.uk/register-for-vat/how-register-for-vat>.

Aceasta explică de ce VAT este util pentru reconcilierea facturilor clientului, dar nu creează automat o sursă open-web. Facturile sunt în mod normal documente private schimbate între furnizor și client. Pentru produsul propus, cea mai valoroasă sursă ar fi chiar arhiva de facturi a clientului, dacă accesul și scopul prelucrării sunt autorizate: numărul poate fi extras din document, verificat prin HMRC și asociat cu înregistrarea furnizorului. Aceasta ar fi o strategie de completare first-party, nu un dataset construit exclusiv din open web.

### Identificator adiacent: EORI

EORI este o pistă concretă pentru companiile care fac operațiuni vamale. Ghidul oficial HMRC arată că, atunci când o companie este înregistrată VAT în UK, primele nouă cifre ale numărului EORI sunt identice cu numărul VAT: <https://www.gov.uk/guidance/economic-operators-registration-and-identification-eori/introduction>. Un EORI GB are forma `GB` plus 12 cifre, de exemplu `GB123456789000`.

Totuși, o companie poate avea EORI fără să fie înregistrată VAT. Prin urmare, pipeline-ul poate extrage primele nouă cifre dintr-un EORI public ca **candidat**, dar trebuie să le verifice prin HMRC și să confirme identitatea; nu poate declara automat că firma este înregistrată VAT. Serviciul oficial de verificare EORI poate returna numele și adresa numai dacă firma a acceptat publicarea lor: <https://www.gov.uk/check-eori-number>.

### Documente de procurement

Contracts Finder conține chestionare și documente contractuale care cer explicit numărul VAT al furnizorului. Cercetarea a găsit, de exemplu, formulare cu câmpurile „Full legal name”, „Company Registration Number” și „Registered VAT Number”. Problema este că multe documente publicate sunt șabloane goale sau conțin `[NUMBER]`, nu răspunsul completat de ofertant.

Concluzie: procurement este o sursă promițătoare numai dacă putem selecta documente contractuale finale sau formulare completate. O căutare largă după șabloane produce multe potriviri lexicale, dar puține dovezi atribuibile. Documentele cu placeholder nu sunt numărate drept candidați. Matricea surselor și deciziilor se află în `results/source_research.csv`.

## Experimentul end-to-end pe cele 60 de companii

Pentru fiecare companie s-a încercat identificarea website-ului oficial folosind numele juridic, numărul Companies House, adresa/localitatea și, unde a fost util, denumirea comercială. Fiecare dintre cele 60 de companii are un rezultat în `results/website_candidates.csv`, inclusiv atunci când nu a fost găsit niciun domeniu.

Această etapă a fost research manual asistat de căutare web, nu un proces complet automat. Au fost folosite combinații ale numelui juridic, numărului companiei, codului poștal și termenului `VAT`, dar nu au fost înregistrate pentru toate cele 60 motorul, ordinea exactă, numărul de rezultate inspectate sau timpul consumat. Prin urmare, rata `47 UNRESOLVED` este un rezultat al procesului efectuat, dar website discovery nu este complet reproductibil și costul său nu poate fi măsurat din logurile actuale. Un experiment următor trebuie să fixeze query-urile, limita de rezultate și regula de oprire înainte de rulare.

Descoperirea website-urilor a produs 4 rezultate `CONFIDENT`, 6 `PROVISIONAL`, 3 `AMBIGUOUS_RELATED_ENTITY` și 47 `UNRESOLVED`. Domeniile ambigue au fost excluse intenționat: un brand înrudit sau o adresă comună nu demonstrează că VAT-ul aparține entității juridice din eșantion. Crawlerul a primit toate cele 10 domenii `CONFIDENT` sau `PROVISIONAL`; pentru celelalte companii nu exista un URL de pornire suficient de sigur.

Cele zece domenii eligibile au produs 49 de încercări HTTP și o decizie explicită `ROBOTS_DISALLOWED`. Șase domenii au returnat cel puțin o pagină HTTP 200, trei au eșuat la nivel de conexiune/DNS, iar unul a fost exclus prin `robots.txt`. Logul conține acum și rândul de excludere; crawlerul a fost corectat pentru ca rulările viitoare să nu mai omită astfel de cazuri.

Crawlul extins a găsit un candidat nou care trece verificarea checksum, `316227425`, în pagina de termeni a Nagle and Sisters. Pagina oferă dovezi neobișnuit de puternice pentru descoperire: afișează împreună numele juridic, numărul companiei `08896326`, codul poștal înregistrat `E17 4BZ` și numărul VAT. Cu toate acestea, instrumentul oficial HMRC a indicat la 14 august 2026 că numărul este invalid. Rezultatul este înregistrat ca `REJECT_INVALID_VAT`. Explicațiile posibile includ conținut învechit pe website sau anularea înregistrării VAT; experimentul nu poate distinge între ele.

Ceilalți doi candidați unici au fost confirmați manual în instrumentul oficial HMRC la 14 august 2026:

- `861397010`, găsit pe pagina de confidențialitate KEOPS, a returnat `KEOPS LTD` și codul poștal `WR11 4SN`;
- `852761903`, publicat în footerul Marketplace AMP lângă numărul companiei `05104409`, a returnat `MARKETPLACE AMP LTD` și codul poștal `SN2 8BW`.

Pentru ambele, numele și codul poștal corespund datelor Companies House. Ele sunt înregistrate o singură dată ca asocieri finale `VERIFIED_MATCH` în `results/verified_results.csv`, chiar dacă același VAT apare ca dovadă pe mai multe pagini în `results/vat_candidates.csv`.

| Etapa pentru eșantionul complet | Companii | Rată din cele 60 selectate |
|---|---:|---:|
| Selectate | 60 | 100% |
| Domenii confirmate/provizorii | 10 | 16,7% |
| Domenii cu cel puțin o pagină HTTP 200 | 6 | 10,0% |
| Candidați unici care trec checksum | 3 | 5,0% |
| Candidați valizi conform HMRC | 2 | 3,3% |
| Potriviri acceptate cu identitatea confirmată | 2 | 3,3% |

Acoperirea măsurată după prima trecere este `2 / 60 = 3,3%`. HMRC a respins unul dintre cei trei candidați care treceau verificarea checksum. Aceasta este respingerea unui candidat, nu un rezultat fals pozitiv acceptat. Ambele potriviri acceptate au fost verificate manual, cu `0 / 2` rezultate fals pozitive observate; eșantionul este în continuare prea mic pentru a pretinde o precizie garantată.

### Explorare suplimentară pe surse publice

Pentru a evalua dacă sursele publice suplimentare aduc valoare peste website-ul principal, am aplicat o verificare directă pe întreaga cohortă de 60 de companii. La fiecare nume juridic exact a fost căutat împreună cu termenul `VAT`; rezultatele relevante au fost clasificate, fără a considera automat fiecare rezultat drept dovadă. Istoricul detaliat pentru fiecare rând se află în `results/source_experiments.csv`.

| Etapa căutării directe | Companii | Rată din cele 60 analizate |
|---|---:|---:|
| Căutări după numele exact și VAT | 60 | 100% |
| Piste utile pentru identitate/domeniu | 7 | 11,7% |
| Companii apărute în PDF-uri publice relevante | 4 | 6,7% |
| Candidați VAT noi și atribuibili | 0 | 0% |
| Candidați noi eligibili pentru HMRC | 0 | 0% |

Acoperirea VAT incrementală a acestei verificări suplimentare a fost `0 / 60 = 0%`. PDF-urile publice au inclus anunțuri Gazette, liste ale autorităților locale privind taxele sau facilitățile pentru proprietăți comerciale și un studiu industrial local. Acestea au ajutat la stabilirea identității, sediului sau activității, dar niciunul nu a publicat un număr VAT atribuibil. Directoarele au copiat frecvent date Companies House; două au afișat un câmp VAT, dar l-au lăsat necompletat. Marketplace-urile, listele de distribuitori, mărcile comerciale, litigiile și profilurile profesionale au oferit uneori indicii despre identitate, nu dovezi VAT autoritative.

A fost detectată o ambiguitate importantă: un domeniu găsit pentru Cheddar Spring Water Limited menționează în footer `Cheddar Water Limited`. Aceasta este o entitate juridică diferită sau înrudită și nu trebuie atribuită automat companiei din eșantion. Cazul arată de ce stratul de research necesită rezolvarea entității, clasificarea surselor și înregistrarea explicită a dovezilor negative, pe lângă crawling.

Acest experiment mic, cu randament zero, nu demonstrează că documentele publice sunt inutile. Arată însă că o căutare generică după numele exact și `VAT` nu ar trebui să fie principala strategie scalabilă pentru această cohortă. Un test următor mai bun ar fi descoperirea țintită a documentelor de achiziții, facturilor și PDF-urilor pentru companii despre care există dovezi că lucrează cu sectorul public, folosind un număr fix de companii și verificare manuală a entității. Common Crawl și registrele țintite de achiziții publice nu au fost încă măsurate și nu primesc credit pentru acoperire.

## Codul proof of concept

- `src/sample_companies.py`: eșantionare stratificată, deterministă, prin reservoir sampling și procesare în flux;
- `src/crawl_sites.py`: crawler limitat la același host, care respectă `robots.txt` și prioritizează paginile juridice/de contact;
- `src/extract_vat.py`: extragerea candidaților, normalizare, păstrarea contextului și filtrare prin checksum pentru UK; implicit, numai candidații cu eticheta `VAT` în apropiere sunt eligibili;
- `src/verify_results.py`: interogare autentificată HMRC v2 și decizie conservatoare; acceptarea automată necesită atât un scor al numelui de cel puțin 90, cât și același cod poștal;
- `tests/test_extraction.py`: teste pentru checksum, formatare, deduplicare și decizia privind entitatea.

Rulare locală:

```powershell
.\.venv\Scripts\activate
python -m pytest -q
python src/crawl_sites.py
python src/extract_vat.py
$env:HMRC_ACCESS_TOKEN = "..."
python src/verify_results.py
```

Proiectul a fost testat cu Python `3.12.10`. Ultima rulare a testelor a produs `7 passed`.

Fișierul publicat `results/verified_results.csv` a fost completat pe baza verificărilor manuale efectuate în serviciul web oficial HMRC. Integrarea API din `verify_results.py` este inclusă ca implementare orientată spre producție, dar nu a fost executată pentru aceste rezultate deoarece nu au fost disponibile credențiale OAuth în intervalul proiectului. Coloana `verification_method` separă explicit `HMRC_WEB_MANUAL` de eventualele rezultate viitoare `HMRC_API_V2`.

## Acceptare și măsurare

O potrivire finală acceptată necesită:

- un URL-sursă și contextul textual păstrat;
- un candidat care trece verificarea checksum;
- un răspuns HMRC valid;
- un nume juridic/comercial și/sau o adresă compatibilă;
- verificare manuală pentru cazurile ambigue care implică grupuri de firme, denumiri comerciale sau adrese comune.

Vocabularul deciziilor este comun codului și fișierelor de rezultate: `VERIFIED_MATCH`, `REJECT_INVALID_VAT`, `REJECT_WRONG_ENTITY`, `MANUAL_REVIEW` și `VERIFICATION_ERROR`.

Raportul final calculează:

```text
acoperire = potriviri companie–VAT acceptate / toate cele 60 de companii din eșantion
rata observată de rezultate fals pozitive = potriviri greșite la audit / potriviri acceptate auditate
```

Pentru prima trecere pe cele 60 de companii, acoperirea măsurată este de 3,3%, cu 0 rezultate fals pozitive observate între cele 2 potriviri acceptate și verificate manual. HMRC a respins încă un candidat de pe website care trecea verificarea checksum, înainte ca acesta să fie acceptat. Chiar dacă toate rezultatele acceptate trec verificarea, formularea rămâne „0 rezultate fals pozitive observate între N potriviri verificate”, nu „acuratețe garantată de 100%”.

## Scalare și model de cost

La scară de producție, etapele ar trebui separate astfel încât metodele costisitoare să fie folosite numai ca fallback:

1. identificarea domeniului din seturi de date existente companie–domeniu sau prin căutare comercială;
2. accesarea HTTP obișnuită a 5–10 pagini prioritizate pentru fiecare domeniu;
3. descoperirea PDF-urilor și extragerea textului;
4. randare în browser numai pentru paginile care necesită JavaScript;
5. verificare HMRC numai pentru candidații care trec checksum;
6. verificare umană numai pentru potrivirile cu identitate ambiguă.

Pentru 40.000 de furnizori, 8 pagini HTTP pentru fiecare domeniu identificat ar însemna aproximativ 320.000 de cereri, înainte de reîncercări, PDF-uri sau escaladarea la browser. Repository-ul nu atribuie încă un cost monetar deoarece rata măsurată de identificare a domeniilor, numărul de pagini per companie, rata de escaladare la browser și rata de verificare manuală sunt incomplete. Aceste observații trebuie să determine modelul de cost, nu o estimare generică de tip „crawler distribuit”.

În limbaj de business, răspunsul scurt la întrebarea „merită?” este: nu în varianta open-web-only, cel puțin nu cu acoperirea observată în acest experiment. La 3,3% acoperire confirmată pe 60 de companii, costul de identificare a domeniului, crawl, PDF-uri, verificare HMRC și review uman este prea mare pentru a justifica construirea unui flux de producție bazat doar pe web public. Abia dacă avem un flux hibrid cu informații first-party sau o listă de domenii deja existente se justifică extinderea. În această formă, proiectul este relevant ca cercetare și pentru validarea metodologiei, nu ca produs operabil de dimensiune reală.

### Model de cost bazat pe resurse

Experimentul nu a măsurat un cost monetar de producție și nu a folosit servicii comerciale, proxy-uri sau un browser headless. Prin urmare, nu raportează valori în lire care nu pot fi susținute prin facturi, oferte sau timpi măsurați. Costul trebuie exprimat prin componente observabile:

```text
cost per companie =
  cost rezolvare companie–domeniu
  pagini HTTP × cost per cerere
  probabilitate browser × cost browser
  probabilitate proxy × cost proxy
  candidați VAT × cost verificare HMRC
  probabilitate ambiguitate × cost review uman
  cost stocare dovezi
```

Costul per rezultat util se calculează separat:

```text
cost per VAT acceptat = cost total al pipeline-ului / potriviri confirmate
```

Datele măsurate în acest proof of concept sunt:

| Indicator de volum | Valoare observată |
|---|---:|
| Companii încercate | 60 |
| Domenii confirmate/provizorii | 10 |
| Domenii cu cel puțin un HTTP 200 | 6 |
| Încercări HTTP înregistrate | 49 |
| Decizii `ROBOTS_DISALLOWED` | 1 |
| Candidați unici care trec checksum | 3 |
| Verificări HMRC efectuate | 3 |
| Potriviri acceptate și verificate manual | 2 |

Aceste valori arată forma costului, dar nu permit încă un preț per companie. Timpul consumat pentru căutarea manuală a domeniilor nu a fost înregistrat, iar Playwright, proxy-urile și review-ul uman la scară nu au fost benchmarkate.

Cele mai ieftine operațiuni sunt probabil cererile HTTP și filtrarea checksum locală. Cele mai costisitoare componente per rezultat corect sunt probabil:

1. rezolvarea sigură a domeniului, deoarece necesită căutare, compararea identității și uneori verificare manuală;
2. review-ul uman al entităților ambigue;
3. browserul headless, prin consumul suplimentar de CPU, RAM, timp și trafic;
4. proxy-urile și reîncercările, care cresc volumul de cereri și complexitatea operațională;
5. păstrarea HTML-ului, PDF-urilor sau capturilor necesare pentru audit.

Înaintea unei estimări comerciale, aș rula un pilot pe 500–1.000 de furnizori din distribuția reală a clientului și aș înregistra pentru fiecare companie: timpul de rezolvare a domeniului, numărul de cereri și octeți, durata CPU, rata de browser/proxy fallback, numărul de candidați HMRC și minutele de review uman. Abia apoi aș atașa prețurile furnizorilor și salariile pentru a calcula costul per companie și per VAT acceptat.

Monitorizarea în producție ar trebui să includă precizia domeniilor, succesul accesării pe categorii de erori, numărul de pagini și octeți per companie, randamentul candidaților după sursă/tip de pagină, rata de trecere checksum, rata de validitate HMRC, decizia privind potrivirea entității, reutilizarea unui VAT de către mai multe entități juridice, rata corectărilor umane, latența și costul per potrivire acceptată.

### Ce s-ar defecta primul

Primul blocaj probabil nu este capacitatea HTTP, ci rezolvarea corectă companie–domeniu. În eșantion, numai 10 dintre 60 de firme au avut domenii confirmate sau provizorii, iar numai 6 au returnat cel puțin o pagină HTTP 200. După îmbunătățirea rezolvării domeniului, următoarele limite ar fi conținutul nepublicat, JavaScript/anti-bot și asocierea greșită între brand, subsidiară, companie-mamă și entitatea juridică.

Proxy-ul și Playwright nu trebuie activate automat după orice eroare. Waterfall-ul de producție ar clasifica mai întâi eșecul:

```text
HTTP + retry/backoff
→ browser numai pentru pagini dependente de JavaScript
→ proxy numai pentru blocaje confirmate și numai dacă termenii permit
→ surse alternative/EORI/documente
→ verificare manuală pentru identitate ambiguă
```

Escaladarea necondiționată ar crește costul și riscul de conformitate fără să rezolve erorile DNS, domeniile greșite sau companiile care nu publică VAT.

## Concluzie comercială

Experimentul arată că un dataset UK company–VAT poate fi construit **parțial** din open web, cu dovezi puternice și precizie conservatoare pentru rezultatele acceptate. Nu arată că open web-ul singur poate furniza cele două treimi lipsă pentru cei 40.000 de furnizori. Prima trecere a confirmat 2 din 60 de companii, adică 3,3%.

Pentru scopul task-ului, răspunsul este clar: într-o variantă bazată doar pe web public, proiectul nu este încă suficient de bun pentru a justifica investiția la scară reală. Costul de descoperire a domeniului, crawl-ul, auditul surselor, verificarea HMRC și review-ul uman este prea mare în raport cu randamentul observat. În schimb, modelul care merită să fie continuat este hibrid: facturile autorizate ale clientului ca sursă first-party, open web și EORI pentru completare, surse comerciale pentru rezolvarea domeniului, HMRC pentru verificare și review uman pentru ambiguități.

Valoarea vandabilă nu este lista de numere găsite, ci fiecare asociere companie–VAT însoțită de proveniență, verificare HMRC, scor de identitate și dată. În această formulare, proiectul este util ca dovadă de fezabilitate și pentru stabilirea blocajelor, dar nu ca soluție completă și automatizată de dimensiune de producție.



### Enumerarea numerelor VAT care trec verificarea checksum

Checksumul reduce spațiul candidaților, dar trimiterea către HMRC a unor numere generate transformă verificarea într-o enumerare a registrului. Ar produce o încărcare considerabilă, probabil ar intra în conflict cu scopul și termenii instrumentului/API-ului, ar atrage limitarea cererilor și ar necesita în continuare asocierea inversă cu entitatea. Nu aș folosi această metodă fără permisiune scrisă explicită din partea HMRC; checksumul este un filtru local, nu o strategie de descoperire.

### Menținerea setului de date actualizat

Pentru fiecare afirmație trebuie păstrate proveniența și marcajul temporal. Sursele valoroase sau volatile trebuie reaccesate incremental, numerele VAT acceptate trebuie reverificate conform unui calendar bazat pe risc, iar schimbările de statut, nume și adresă din Companies House trebuie procesate. Înregistrările trebuie puse în carantină atunci când identitatea HMRC se schimbă sau un număr devine invalid. Absența la o accesare ulterioară este o dovadă slabă; schimbarea statutului sau identității HMRC este mai puternică.

### Detectarea erorilor fără un set complet de referință

Trebuie auditate eșantioane aleatorii stratificate, urmărite corectările rezultate din verificarea umană, testate invariantele — de exemplu, același VAT asociat neașteptat unor companii fără legătură — comparate surse independente, monitorizate schimbările de distribuție și păstrate capturi sau dovezi ale paginilor pentru reproducerea deciziilor. Precizia trebuie estimată prin audituri și intervale de încredere, nu dedusă din validitatea checksumului.

### Surse pe care aș ezita să le comercializez

Fragmentele din rezultatele motoarelor de căutare, directoarele extrase automat și marketplace-urile sunt piste pentru descoperire, nu dovezi autoritative: pot fi învechite, copiate sau se pot referi la vânzători, companii-mamă, procesatori de plăți ori autorități contractante. Aș evita și comercializarea datelor din surse ai căror termeni interzic reutilizarea sau accesarea automată. Fiecare pistă trebuie urmărită până la o sursă permisă și verificată independent prin HMRC și asocierea cu entitatea.

## Rezultatele din repository

`data/processed/sample_companies.csv` reprezintă cohorta fixă a experimentului. Fișierele din `results/` sunt rezultatele fiecărei etape și trebuie să păstreze atât eșecurile, cât și reușitele, pentru ca numitorul funnelului să poată fi auditat.
