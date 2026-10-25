# Resoconto metodologico sulla generazione dei dataset di test — v2
### Algoritmo euristico di 3D Bin Packing con vincoli di peso, valore e gravity strength
### (flotta di veicoli FISSA a 2 tipi, identici in ogni dataset)

Questo documento descrive la **seconda generazione** dei dataset di test,
che sostituisce integralmente la precedente (basata su un container diverso
per scenario, incluse taglie da container ISO/semirimorchio). La differenza
chiave rispetto alla generazione precedente è che ora **ogni dataset porta
con sé, nel proprio `vehicles.csv`, esattamente gli stessi 2 veicoli fissi**,
pensati per essere usati uno alla volta (il solver viene eseguito due volte
per dataset, una per ciascun veicolo, ripetendo lo stesso tipo di veicolo
quante volte serve) così da poter isolare e confrontare l'effetto della
scelta del veicolo sul risultato di packing, a parità di merce da spedire.

Tutti i dataset sono stati prodotti da un unico script Python
(`generate_datasets_v2.py`, incluso nel pacchetto) con seme casuale fisso
(`20260804`, diverso dalla generazione precedente in modo da produrre una
run indipendente) per garantire la riproducibilità. Un secondo script
(`validate_v2.py`, incluso) verifica automaticamente che ogni dataset
rispetti lo schema richiesto — inclusi i controlli specifici della v2: le 2
righe di `vehicles.csv` devono essere **esattamente** identiche, valore per
valore, in tutti i 52 dataset, e ogni item deve poter entrare, in almeno
una delle *sue* rotazioni ammesse (`allowedRotations`), in **ciascuno** dei 2
veicoli fissi (il solver usa un veicolo per volta: un item che entrasse in uno
solo dei due renderebbe incompleta una delle due run), con peso e valore
entro i massimi di entrambi. La validazione non ha riscontrato errori sui 52
dataset.

---

## 1. I 2 veicoli fissi

I due veicoli sono stati forniti come dato di input, derivato da specifiche
tecniche di veicoli commerciali reali (un furgone Fiat Ducato L2H2 passo medio
e un furgone urbano piccolo), e sono stati usati così come sono, **senza
modifiche**, identici in ogni singolo `vehicles.csv` del pacchetto:

| type | Descrizione | width (cm) | depth (cm) | height (cm) | maxWeight (kg) | maxValue (EUR) | Volume utile (m³) |
|---|---|---|---|---|---|---|---|
| furgone_ducato_medio | Furgone Fiat Ducato L2H2 (passo medio) | 187 | 312 | 193 | 1200 | 60000 | ≈ 11,26 |
| furgone_torino_piccolo | Furgone urbano piccolo (city van) | 125 | 182 | 121 | 660 | 25000 | ≈ 2,75 |

**Perché rappresentano uno scenario coerente di consegna locale:** sono due
mezzi commerciali in uso corrente per la distribuzione locale: il Ducato medio
è il mezzo standard per l'ultimo miglio urbano, il Torino piccolo serve dove
le strade strette rendono impraticabile quello più grande. Non compaiono più,
rispetto alla generazione precedente, container ISO o semirimorchi: la
flotta è deliberatamente limitata a questi due mezzi per permettere il
confronto diretto "stesso carico, veicolo diverso" richiesto per la tesi.
Avendo il Ducato medio un volume utile circa 4,1 volte superiore al Torino
piccolo (11,26 m³ contro 2,75 m³) e una portata circa 1,8 volte superiore
(1200 kg contro 660 kg), a parità di merce i due mezzi si prestano bene a
mettere in luce differenze nel numero di veicoli necessari e nell'efficienza
di riempimento restituita dalle due euristiche.

> **Nota storica.** La prima versione di questa generazione usava come secondo
> veicolo un camion a cassone chiuso (`camion_cassone_medio`, 240×600×240 cm,
> 4000 kg, 180000 EUR). È stato sostituito dal furgone Torino piccolo in tutti
> i 52 dataset; i file `items.csv` non sono cambiati. Gli esperimenti della
> tesi usano esclusivamente la coppia Ducato medio + Torino piccolo.

`vehicles.csv` (identico, riga per riga, in **tutti** i 52 dataset):

```
type,width,depth,height,maxWeight,maxValue
furgone_ducato_medio,187,312,193,1200,60000
furgone_torino_piccolo,125,182,121,660,25000
```

---

## 2. Categorie di prodotto

Sono state riutilizzate, senza modifiche sostanziali, le stesse **19
categorie di prodotto** già definite e motivate nella generazione
precedente (ispirate a cataloghi reali di e-commerce e a dimensioni
standard di scatole di spedizione per quella tipologia di merce). Sono
compatibili con entrambi i veicoli fissi: il più piccolo dei due (furgone
Torino piccolo, vano 125×182×121 cm) accoglie ogni item in almeno una delle
rotazioni ammesse per quell'item (controllo eseguito da `validate_v2.py`),
quindi nessun item risulta troppo grande per nessuno dei due mezzi.

| Categoria | Descrizione / esempi reali | W (cm) | D (cm) | H (cm) | Peso (kg) | Valore (€) | gravityStrength (%) | allowedRotations |
|---|---|---|---|---|---|---|---|---|
| electronics_small | Smartphone, cuffie, action cam, tablet | 7-20 | 6-16 | 3-9 | 0,15-0,9 | 29-1300 | 55-85 | 40% "01" (con scritta "alto"), 60% "012345" |
| electronics_large | TV, monitor, scatola laptop | 35-130 | 10-22 | 25-85 | 2-22 | 180-1800 | 75-95 | 01 |
| small_appliances | Frullatori, macchine caffè, microonde, tostapane | 22-55 | 20-45 | 25-40 | 1,5-13 | 25-320 | 55-85 | 01 |
| large_appliances | Mini-frigo, lavatrice, lavastoviglie | 50-65 | 55-70 | 60-90 | 18-75 | 150-650 | 45-70 | 01 |
| books_media | Tascabili, copertine rigide, cofanetti | 11-26 | 13-20 | 1,5-6 | 0,15-1,2 | 7-45 | 10-30 | 012345 |
| toys_games | LEGO, giochi da tavolo, action figure | 18-50 | 15-40 | 7-20 | 0,3-2,5 | 12-160 | 20-45 | 012345 |
| clothing_footwear | Scarpe, jeans, giacche in scatola/busta rigida | 20-34 | 13-28 | 5-14 | 0,25-1,3 | 15-160 | 10-25 | 012345 |
| kitchenware_glass | Vasellame, bicchieri, ceramiche | 28-48 | 28-48 | 18-32 | 2,5-9 | 35-180 | 80-96 | 01 |
| beverages_liquids | Vino, olio, detersivi imbottigliati | 18-42 | 18-32 | 22-34 | 4-11 | 8-110 | 55-80 | 01 |
| groceries_canned | Conserve, pasta, prodotti secchi confezionati | 28-45 | 20-32 | 18-28 | 6-12,5 | 9-30 | 15-35 | 012345 |
| furniture_flatpack | Tavolini, mensole, scaffali smontati | 80-160 | 40-70 | 3-8 | 9-32 | 35-260 | 20-40 | 01 (deve restare piatto) |
| sports_fitness_light | Tappetini yoga, abbigliamento sportivo | 15-65 | 12-20 | 10-20 | 0,4-3 | 12-70 | 20-40 | 012345 |
| sports_fitness_heavy | Manubri, pesi, kettlebell | 18-42 | 18-24 | 18-24 | 6-24 | 25-110 | 15-30 | 012345 |
| bicycles | Biciclette scatolate | 110-135 | 18-24 | 68-85 | 11-19 | 220-1100 | 65-88 | **0145** (parziale) |
| tools_hardware | Trapani, cassette attrezzi, utensili da giardino | 20-45 | 10-30 | 8-26 | 1,2-13 | 18-220 | 20-45 | 012345 |
| personal_care | Profumi, set make-up | 10-22 | 8-18 | 6-14 | 0,15-0,9 | 18-140 | 65-90 | 01 |
| musical_instruments | Custodie chitarra, tastiere compatte | 95-118 | 14-40 | 35-42 | 3-9,5 | 140-650 | 80-95 | 01 |
| pet_supplies | Sacchi mangime, cucce, trasportini | 35-90 | 25-60 | 12-65 | 3-18 | 20-130 | 20-40 | 012345 |
| office_supplies | Risme carta, sedie da ufficio, cancelleria | 30-70 | 25-45 | 12-62 | 2,5-19 | 15-260 | 25-55 | 35% "01", 65% "012345" |

### Come e perché varia `gravityStrength`

Per ogni item il valore viene campionato uniformemente all'interno del
range della sua categoria (arrotondato a 1 decimale), scelto in base alla
fragilità intrinseca del prodotto:

- **10-35%**: oggetti robusti in scatole rigide (libri, giochi da tavolo,
  abbigliamento, conserve, utensili) — non richiedono grande supporto
  sottostante per restare stabili o non deformarsi.
- **45-70%**: grandi elettrodomestici — rigidi (lamiera/plastica dura) ma
  pesanti, richiedono un supporto parziale ma non minimo per la stabilità.
- **55-85%**: piccola elettronica, elettrodomestici da banco, bevande/
  liquidi imbottigliati — packaging meno rigido o rischio di
  danneggiamento/perdita di liquido in caso di cedimento sotto il peso.
- **65-96%**: oggetti più fragili o a rischio rottura in caso di cedimento
  strutturale sottostante (vasellame/ceramiche, strumenti musicali,
  biciclette, cura della persona con flaconi in vetro, elettronica grande
  con schermo).

Il valore non è mai costante entro un dataset: sia per il jitter casuale
all'interno di ciascuna categoria, sia perché la maggior parte dei temi
combina più categorie con range di fragilità diversi.

### Come e perché varia `allowedRotations`

- **"01" (upright-only)**: elettrodomestici (piccoli e grandi), elettronica
  con schermo, vasellame/ceramiche, bevande/liquidi imbottigliati (per
  evitare perdite dai tappi), strumenti musicali, cura della persona
  (flaconi), mobili flat-pack (devono restare distesi sul lato piatto).
- **"012345" (liberamente orientabile)**: libri, giochi, abbigliamento,
  alimentari confezionati/in scatola, utensili, articoli sportivi
  leggeri/pesanti, prodotti per animali.
- **Categorie a modalità mista** (`electronics_small` 40% upright,
  `office_supplies` 35% upright): stessa categoria merceologica ma con una
  quota di item vincolati (es. dispositivi con etichetta "alto", sedie da
  ufficio) e una quota liberamente orientabile (es. cuffie, cancelleria).
- **Sottoinsieme parziale "0145"** per le biciclette scatolate: esclude le
  rotazioni 2 e 3 (che farebbero poggiare la scatola sul fianco stretto,
  instabile e a rischio danneggiamento del telaio/cambio), mantenendo le
  due posizioni "in piedi" (0,1) e le due sdraiate sul lato lungo (4,5).

---

## 3. Dataset dimostrativi

### dataset_prova_1 (5 item)

Mix curato per mostrare da subito l'intera gamma dello schema anche con
pochi item: elettronica grande (upright, gravity ~93%), bevanda
imbottigliata (upright, gravity ~69%), libro (libera rotazione, gravity
~24%), gioco da tavolo (libera rotazione, gravity ~43%), cassetta attrezzi
(libera rotazione, gravity ~42%).

### dataset_prova_2 (20 item)

Copre quasi tutte le 19 categorie di prodotto definite (incluse due varianti
di elettronica di consumo, una upright e una a libera rotazione), e include
un item della categoria "biciclette" per mostrare in azione il sottoinsieme
di rotazione parziale `"0145"`. La gamma di `gravityStrength` nel dataset va
da un minimo di circa 13% a un massimo di circa 87%, con `allowedRotations`
che copre tutti e tre i pattern usati ("01", "012345", "0145").

Entrambi i dataset dimostrativi usano lo stesso `vehicles.csv` fisso di
tutti gli altri dataset (le due righe Ducato medio / Torino piccolo), pur
essendo pensati, per numero di item contenuto, per una visualizzazione grafica
leggibile soprattutto sul veicolo più piccolo (Torino piccolo).

---

## 4. I 50 dataset di test prestazionali (Dataset1 … Dataset50)

Poiché il veicolo non varia più da dataset a dataset (è sempre la stessa
coppia fissa), la varietà tra i 50 dataset è affidata interamente a due
leve: il **tema/profilo merceologico** e il **numero di item**. Sono stati
riutilizzati gli stessi 16 temi (mix pesati di categorie) della generazione
precedente, riletti in chiave di consegna locale/distribuzione regionale
coerente con i due mezzi fissi (in particolare il tema
"grande_distribuzione_mista", che nella generazione precedente poteva
arrivare a scala di camion pesante/semirimorchio, qui rappresenta una
distribuzione regionale verso punti vendita locali, scala compatibile con
il furgone Ducato medio).

Il numero di item per dataset è stato scelto per riflettere carichi
plausibili per i due mezzi fissi: da poche decine (consegna locale con
furgone) a qualche centinaio (giro di distribuzione regionale su più punti
vendita, eventualmente ripetuto su più mezzi dello stesso tipo), con un range di
riferimento indicativo di circa 15-300 item, più i 2 dataset da 900-1000
item come caso limite esplicito.

### Tabella completa

| # | Tema/scenario | n. item |
|---|---|---|
| Dataset1 | elettronica_consumer | 25 |
| Dataset2 | libri_editoria | 40 |
| Dataset3 | misto_generico_ecommerce | 60 |
| Dataset4 | abbigliamento_calzature | 30 |
| Dataset5 | casa_cucina | 45 |
| Dataset6 | giocattoli_gioco | 55 |
| Dataset7 | sport_tempo_libero | 35 |
| Dataset8 | fai_da_te_utensili | 40 |
| Dataset9 | alimentari_bevande | 90 |
| Dataset10 | grande_distribuzione_mista | 120 |
| Dataset11 | arredamento_flatpack | 25 |
| Dataset12 | elettrodomestici_grandi | 18 |
| Dataset13 | ufficio_forniture | 50 |
| Dataset14 | musica_hobby | 22 |
| Dataset15 | pet_shop | 35 |
| Dataset16 | elettronica_consumer | 70 |
| Dataset17 | libri_editoria | 85 |
| Dataset18 | misto_generico_ecommerce | 100 |
| Dataset19 | abbigliamento_calzature | 75 |
| Dataset20 | casa_cucina | 65 |
| Dataset21 | giocattoli_gioco | 130 |
| Dataset22 | sport_tempo_libero | 60 |
| Dataset23 | fai_da_te_utensili | 95 |
| Dataset24 | alimentari_bevande | 150 |
| **Dataset25** | **reso_magazzino_stress** | **950 — CASO LIMITE** |
| Dataset26 | grande_distribuzione_mista | 180 |
| Dataset27 | arredamento_flatpack | 70 |
| Dataset28 | elettrodomestici_grandi | 45 |
| Dataset29 | ufficio_forniture | 100 |
| Dataset30 | musica_hobby | 40 |
| Dataset31 | pet_shop | 80 |
| Dataset32 | elettronica_consumer | 110 |
| Dataset33 | libri_editoria | 160 |
| Dataset34 | misto_generico_ecommerce | 190 |
| Dataset35 | abbigliamento_calzature | 170 |
| Dataset36 | casa_cucina | 140 |
| Dataset37 | giocattoli_gioco | 210 |
| Dataset38 | sport_tempo_libero | 150 |
| Dataset39 | fai_da_te_utensili | 180 |
| Dataset40 | alimentari_bevande | 240 |
| Dataset41 | grande_distribuzione_mista | 260 |
| Dataset42 | arredamento_flatpack | 110 |
| Dataset43 | elettrodomestici_grandi | 65 |
| Dataset44 | ufficio_forniture | 150 |
| Dataset45 | musica_hobby | 90 |
| Dataset46 | pet_shop | 140 |
| Dataset47 | elettronica_consumer | 200 |
| Dataset48 | misto_generico_ecommerce | 280 |
| Dataset49 | grande_distribuzione_mista | 300 |
| **Dataset50** | **reso_magazzino_stress** | **1000 — CASO LIMITE** |

### I due dataset da ~900-1000 item (Dataset25 e Dataset50)

**Dataset25 (950 item)** e **Dataset50 (1000 item)** rappresentano un caso
limite volutamente non realistico per un furgone Ducato medio o un furgone
Torino piccolo (nessuna consegna locale o distribuzione regionale carica
davvero mille colli eterogenei per un singolo giro con questi mezzi), ma
utile dal punto di vista sperimentale per **misurare la scalabilità e i
tempi di esecuzione delle due euristiche (best-fit e first-fit)** al
crescere del numero di item — un aspetto centrale per la validazione pratica
dell'algoritmo, specialmente eseguendolo due volte (una per veicolo) su un
carico così numeroso. Per restare comunque plausibili come scenario
"limite superiore", sono stati inquadrati come una **consolidazione/reso di
magazzino e-commerce** (tema `reso_magazzino_stress`, mix merceologico molto
ampio che unisce con pesi minori quasi tutte le 19 categorie di prodotto).
Dimensioni, pesi, valori e `gravityStrength` degli item restano generati
con le stesse regole di realismo di tutti gli altri 48 dataset, e il
`vehicles.csv` resta la stessa coppia fissa non modificata: a variare, per
costruzione esplicita, è solo la numerosità.

---

## 5. Struttura dei file e riproducibilità

```
datasets/
  dataset_prova_1/{items.csv, vehicles.csv}
  dataset_prova_2/{items.csv, vehicles.csv}
  Dataset1/{items.csv, vehicles.csv}
  ...
  Dataset50/{items.csv, vehicles.csv}
generate_datasets_v2.py   # script generatore (riproducibile, seed=20260804)
validate_v2.py            # script di validazione dello schema (incl. controllo dei 2 veicoli fissi)
RESOCONTO.md               # questo documento
```

Nel repository la cartella `datasets/` si trova nella radice del progetto
(da dove la leggono i solver), mentre questa cartella contiene solo gli script
e questo documento. Per **rigenerare** i dataset: `python generate_datasets_v2.py`
scrive in `datasets_rigenerati/` (accanto allo script, ricreata a ogni
esecuzione, **non** sovrascrive `datasets/`); i 52 `items.csv` risultano
identici byte per byte a quelli in `datasets/`, e i 52 `vehicles.csv` hanno lo
stesso contenuto (può cambiare solo il carattere di fine riga). Per
**validare** una cartella di dataset: `python validate_v2.py [cartella]`
(senza argomento controlla `../datasets`).

`items.csv`: colonne `id,width,depth,height,weight,value,allowedRotations,gravityStrength`
(id progressivo `I0000...`, dimensioni in cm, peso in kg, valore in EUR,
`allowedRotations` stringa di cifre 0-5, `gravityStrength` percentuale
0-100).

`vehicles.csv`: **esattamente 2 righe**, colonne
`type,width,depth,height,maxWeight,maxValue`, identiche in ogni dataset:

```
type,width,depth,height,maxWeight,maxValue
furgone_ducato_medio,187,312,193,1200,60000
furgone_torino_piccolo,125,182,121,660,25000
```

### Nota sui riferimenti reali

I due veicoli fissi (Fiat Ducato L2H2 e un furgone urbano piccolo) sono
ancorati a specifiche tecniche di veicoli commerciali reali e sono stati
utilizzati senza modifiche né nuova ricerca. Le 19 categorie di
prodotto restano ancorate, come nella generazione precedente, a fasce di
prezzo, pesi e dimensioni di packaging tipiche riscontrabili su cataloghi
e-commerce reali (es. Amazon) per ciascuna tipologia di merce.
