# Descoperirea numerelor VAT din Regatul Unit folosind surse web publice

## Rezumat executiv

Acest proiect testează dacă numerele VAT ale companiilor britanice pot fi descoperite din surse web publice. Procesul nu acceptă un număr doar pentru că are format corect: HMRC trebuie să confirme numărul, iar numele și adresa returnate trebuie să corespundă companiei din Companies House.

Am folosit **un singur eșantion principal de 60 de companii**, ales reproductibil înainte să știm dacă firmele au website sau VAT. Din acest eșantion, procesul a confirmat 2 asocieri companie–VAT, adică o acoperire end-to-end de `2 / 60 = 3,3%`. A mai găsit un candidat cu checksum valid, dar HMRC l-a declarat invalid. Nu au fost observate rezultate fals pozitive între cele două asocieri acceptate și verificate manual, însă eșantionul este prea mic pentru a afirma o precizie garantată.

Concluzia este că open web-ul poate produce asocieri VAT verificabile, dar rezultatele actuale nu susțin promisiunea că ar putea completa singur cele două treimi lipsă din lista clientului. Principalul blocaj observat este identificarea website-ului corect al companiei, nu viteza crawlerului.

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

Metoda a fost dezvoltată incremental, apoi aplicată întregului eșantion. Toate rezultatele principale folosesc numitorul complet de 60 de companii. Un subset reproductibil de 20 a fost folosit numai pentru un experiment separat cu surse alternative; rezultatul lui nu înlocuiește și nu modifică coverage-ul principal `2/60`.

Sursă: snapshotul Companies House Free Company Data Product din 1 august 2026. Fișierul CSV-sursă nu este inclus în repository deoarece are aproximativ 2,8 GB.

Comanda folosită:

```powershell
python src/sample_companies.py data/raw/BasicCompanyDataAsOneFile-2026-08-01.csv `
  --size 60 --seed 42 --output data/processed/sample_companies.csv
```

Filtre și categorii:

- numai companii active;
- numărul și numele companiei sunt obligatorii;
- codul SIC principal trebuie să aparțină producției (10–33), construcțiilor (41–43), comerțului cu ridicata (45–46) sau anumitor servicii pentru companii (62, 69–74);
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

Descoperirea website-urilor a produs 4 rezultate `CONFIDENT`, 6 `PROVISIONAL`, 3 `AMBIGUOUS_RELATED_ENTITY` și 47 `UNRESOLVED`. Domeniile ambigue au fost excluse intenționat: un brand înrudit sau o adresă comună nu demonstrează că VAT-ul aparține entității juridice din eșantion. Crawlerul a primit toate cele 10 domenii `CONFIDENT` sau `PROVISIONAL`; pentru celelalte companii nu exista un URL de pornire suficient de sigur.

Cele zece domenii eligibile au produs 49 de încercări de accesare a paginilor. Șase domenii au returnat cel puțin o pagină HTTP 200, trei au eșuat la nivel de conexiune/DNS, iar unul nu a produs nicio înregistrare deoarece `robots.txt` a exclus crawlingul. Ultimul caz a scos la iveală o problemă de observabilitate: excluderile impuse de `robots.txt` ar trebui înregistrate explicit, nu omise fără explicație.

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

### Experiment de căutare directă și documente publice

Pentru a testa dacă cercetarea în afara website-urilor companiilor îmbunătățește descoperirea, a fost selectat aleatoriu și reproductibil, cu seed `43`, un subeșantion de 20 dintre cele 60 de companii. La 14 august 2026, fiecare nume juridic exact a fost căutat împreună cu termenul `VAT`; rezultatele relevante au fost clasificate, fără a considera automat fiecare rezultat drept dovadă. Istoricul detaliat pentru fiecare rând se află în `results/source_experiments.csv`.

| Etapa căutării directe | Companii | Rată din cele 20 analizate |
|---|---:|---:|
| Căutări după numele exact și VAT | 20 | 100% |
| Piste utile pentru identitate/domeniu | 7 | 35% |
| Companii apărute în PDF-uri publice relevante | 4 | 20% |
| Candidați VAT noi și atribuibili | 0 | 0% |
| Candidați noi eligibili pentru HMRC | 0 | 0% |

Acoperirea VAT incrementală a experimentului a fost `0 / 20 = 0%`. PDF-urile publice au inclus anunțuri Gazette, liste ale autorităților locale privind taxele sau facilitățile pentru proprietăți comerciale și un studiu industrial local. Acestea au ajutat la stabilirea identității, sediului sau activității, dar niciunul nu a publicat un număr VAT atribuibil. Directoarele au copiat frecvent date Companies House; două au afișat un câmp VAT, dar l-au lăsat necompletat. Marketplace-urile, listele de distribuitori, mărcile comerciale, litigiile și profilurile profesionale au oferit uneori indicii despre identitate, nu dovezi VAT autoritative.

A fost detectată o ambiguitate importantă: un domeniu găsit pentru Cheddar Spring Water Limited menționează în footer `Cheddar Water Limited`. Aceasta este o entitate juridică diferită sau înrudită și nu trebuie atribuită automat companiei din eșantion. Cazul arată de ce stratul de research necesită rezolvarea entității, clasificarea surselor și înregistrarea explicită a dovezilor negative, pe lângă crawling.

Acest experiment mic, cu randament zero, nu demonstrează că documentele publice sunt inutile. Arată însă că o căutare generică după numele exact și `VAT` nu ar trebui să fie principala strategie scalabilă pentru această cohortă. Un test următor mai bun ar fi descoperirea țintită a documentelor de achiziții, facturilor și PDF-urilor pentru companii despre care există dovezi că lucrează cu sectorul public, folosind un număr fix de companii și verificare manuală a entității. Common Crawl și registrele țintite de achiziții publice nu au fost încă măsurate și nu primesc credit pentru acoperire.

## Codul proof of concept

- `src/sample_companies.py`: eșantionare stratificată, deterministă, prin reservoir sampling și procesare în flux;
- `src/crawl_sites.py`: crawler limitat la același host, care respectă `robots.txt` și prioritizează paginile juridice/de contact;
- `src/extract_vat.py`: extragerea candidaților, normalizare, păstrarea contextului și filtrare prin checksum pentru UK;
- `src/verify_results.py`: interogare autentificată HMRC v2 și decizie conservatoare pe baza numelui/adresei;
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

Ultima rulare a testelor a produs `6 passed`.

## Acceptare și măsurare

O potrivire finală acceptată necesită:

- un URL-sursă și contextul textual păstrat;
- un candidat care trece verificarea checksum;
- un răspuns HMRC valid;
- un nume juridic/comercial și/sau o adresă compatibilă;
- verificare manuală pentru cazurile ambigue care implică grupuri de firme, denumiri comerciale sau adrese comune.

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
| Pagini înregistrate | 49 |
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

Experimentul arată că un dataset UK company–VAT poate fi construit **parțial** din open web, cu dovezi puternice și precizie conservatoare pentru rezultatele acceptate. Nu arată că open web-ul singur poate furniza cele două treimi lipsă pentru cei 40.000 de furnizori. Prima trecere a confirmat 2 din 60 de companii, adică 3,3%, iar căutarea directă suplimentară a adăugat 0 din 20.

Prin urmare, nu aș promite clientului acoperirea cerută înaintea unui pilot pe furnizorii săi reali. Aș propune un produs hibrid: facturile autorizate ale clientului ca sursă first-party, open web și EORI pentru completare, surse comerciale pentru rezolvarea domeniului, HMRC pentru verificare și review uman pentru ambiguități. Valoarea vandabilă nu este lista de numere găsite, ci fiecare asociere companie–VAT însoțită de proveniență, verificare HMRC, scor de identitate și dată.

## Subiecte pentru discuție

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
