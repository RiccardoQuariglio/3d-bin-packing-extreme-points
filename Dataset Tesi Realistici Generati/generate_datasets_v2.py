#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generatore di dataset realistici per algoritmo euristico di 3D Bin Packing
(tesi di laurea) - VERSIONE 2: flotta di veicoli FISSA a 2 soli tipi,
identici in ogni dataset (furgone Fiat Ducato L2H2 medio e furgone urbano
piccolo 'Torino'), cosi' da poter eseguire il solver due volte per
dataset (una per ciascun veicolo) e confrontare l'effetto della scelta del
veicolo sul risultato.

Rispetto alla versione precedente (container ISO / semirimorchi inclusi):
- vehicles.csv ha ora 2 righe fisse con colonna 'type' aggiuntiva, IDENTICHE
  in tutti i 52 dataset.
- la scala realistica degli item (n. item per dataset) e' stata ridotta per
  riflettere carichi plausibili per un furgone medio (~11 m3) o un furgone
  piccolo (~2.75 m3), NON piu' trasporto intermodale/industriale.

Genera:
  - dataset_prova_1 (5 item), dataset_prova_2 (20 item): dataset dimostrativi
  - Dataset1 ... Dataset50: dataset di test prestazionali (2 di essi con
    ~900-1000 item come caso limite esplicito, veicolo NON cambiato)
"""

import os
import csv
import random
import shutil

random.seed(20260804)  # nuovo seed, run distinta dalla generazione precedente

BASE_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets_rigenerati")  # NON sovrascrive ../datasets; cartella ricreata a ogni run
if os.path.exists(BASE_OUT):
    shutil.rmtree(BASE_OUT)
os.makedirs(BASE_OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 1) FLOTTA FISSA: ESATTAMENTE 2 VEICOLI, IDENTICI IN OGNI DATASET
# ---------------------------------------------------------------------------
# Valori forniti dall'utente (gia' derivati da specifiche tecniche di veicoli
# commerciali reali: Fiat Ducato L2H2 passo medio e un furgone urbano piccolo;
# una versione precedente del generatore usava come secondo veicolo un camion a
# cassone chiuso, poi sostituito dal furgone piccolo). Non vengono ri-cercati:
# si usano esattamente questi numeri, in questo ordine, in ogni vehicles.csv.
FIXED_VEHICLES = [
    dict(type="furgone_ducato_medio", width=187, depth=312, height=193,
         maxWeight=1200, maxValue=60000,
         label="Furgone Fiat Ducato L2H2 (passo medio)"),
    dict(type="furgone_torino_piccolo", width=125, depth=182, height=121,
         maxWeight=660, maxValue=25000,
         label="Furgone urbano piccolo (city van)"),
]

# ---------------------------------------------------------------------------
# 2) CATEGORIE DI PRODOTTO (stesse ispirate a cataloghi Amazon / e-commerce
#    reali usate nella generazione precedente; tutte le dimensioni restano
#    compatibili con entrambi i veicoli fissi - il piu' piccolo, il furgone
#    Torino piccolo, ha vano 125x182x121 cm: ogni item, in almeno una delle
#    sue rotazioni ammesse, vi entra (verificato da validate_v2.py))
# ---------------------------------------------------------------------------
CATEGORIES = {
    "electronics_small": dict(
        label="Elettronica di consumo (smartphone, cuffie, action cam, tablet)",
        dims=[(7, 20), (6, 16), (3, 9)],
        weight=(0.15, 0.9), value=(29, 1300),
        gravity=(55, 85), rot_mode="mixed_free_upright", rot_upright_share=0.4,
    ),
    "electronics_large": dict(
        label="Elettronica grande (TV, monitor, laptop box)",
        dims=[(35, 130), (10, 22), (25, 85)],
        weight=(2.0, 22.0), value=(180, 1800),
        gravity=(75, 95), rot_mode="upright",
    ),
    "small_appliances": dict(
        label="Piccoli elettrodomestici (frullatori, macchine caffe', microonde, tostapane)",
        dims=[(22, 55), (20, 45), (25, 40)],
        weight=(1.5, 13.0), value=(25, 320),
        gravity=(55, 85), rot_mode="upright",
    ),
    "large_appliances": dict(
        label="Grandi elettrodomestici (frigo mini-bar, lavatrice, lavastoviglie)",
        dims=[(50, 65), (55, 70), (60, 90)],
        weight=(18.0, 75.0), value=(150, 650),
        gravity=(45, 70), rot_mode="upright",
    ),
    "books_media": dict(
        label="Libri ed editoria (tascabili, copertine rigide, cofanetti)",
        dims=[(11, 26), (13, 20), (1.5, 6)],
        weight=(0.15, 1.2), value=(7, 45),
        gravity=(10, 30), rot_mode="free",
    ),
    "toys_games": dict(
        label="Giocattoli e giochi da tavolo (LEGO, board game, action figure)",
        dims=[(18, 50), (15, 40), (7, 20)],
        weight=(0.3, 2.5), value=(12, 160),
        gravity=(20, 45), rot_mode="free",
    ),
    "clothing_footwear": dict(
        label="Abbigliamento e calzature (scarpe, jeans, giacche in scatola/busta rigida)",
        dims=[(20, 34), (13, 28), (5, 14)],
        weight=(0.25, 1.3), value=(15, 160),
        gravity=(10, 25), rot_mode="free",
    ),
    "kitchenware_glass": dict(
        label="Articoli per la casa fragili (vasellame, bicchieri, ceramiche)",
        dims=[(28, 48), (28, 48), (18, 32)],
        weight=(2.5, 9.0), value=(35, 180),
        gravity=(80, 96), rot_mode="upright",
    ),
    "beverages_liquids": dict(
        label="Bevande e liquidi imbottigliati (vino, olio, detersivi)",
        dims=[(18, 42), (18, 32), (22, 34)],
        weight=(4.0, 11.0), value=(8, 110),
        gravity=(55, 80), rot_mode="upright",
    ),
    "groceries_canned": dict(
        label="Alimentari secchi/in scatola (conserve, pasta, prodotti confezionati)",
        dims=[(28, 45), (20, 32), (18, 28)],
        weight=(6.0, 12.5), value=(9, 30),
        gravity=(15, 35), rot_mode="free",
    ),
    "furniture_flatpack": dict(
        label="Mobili flat-pack (tavolini, mensole, scaffali smontati)",
        dims=[(80, 160), (40, 70), (3, 8)],
        weight=(9.0, 32.0), value=(35, 260),
        gravity=(20, 40), rot_mode="upright",  # deve restare piatto (h=lato sottile verticale)
    ),
    "sports_fitness_light": dict(
        label="Sport e fitness leggero (tappetini yoga, abbigliamento sportivo, accessori)",
        dims=[(15, 65), (12, 20), (10, 20)],
        weight=(0.4, 3.0), value=(12, 70),
        gravity=(20, 40), rot_mode="free",
    ),
    "sports_fitness_heavy": dict(
        label="Sport pesante (manubri, pesi, kettlebell)",
        dims=[(18, 42), (18, 24), (18, 24)],
        weight=(6.0, 24.0), value=(25, 110),
        gravity=(15, 30), rot_mode="free",
    ),
    "bicycles": dict(
        label="Biciclette e componenti scatolati",
        dims=[(110, 135), (18, 24), (68, 85)],
        weight=(11.0, 19.0), value=(220, 1100),
        gravity=(65, 88), rot_mode="upright",
    ),
    "tools_hardware": dict(
        label="Utensili e ferramenta (trapani, cassette attrezzi, utensili da giardino)",
        dims=[(20, 45), (10, 30), (8, 26)],
        weight=(1.2, 13.0), value=(18, 220),
        gravity=(20, 45), rot_mode="free",
    ),
    "personal_care": dict(
        label="Cura della persona e cosmetici (profumi, set make-up)",
        dims=[(10, 22), (8, 18), (6, 14)],
        weight=(0.15, 0.9), value=(18, 140),
        gravity=(65, 90), rot_mode="upright",
    ),
    "musical_instruments": dict(
        label="Strumenti musicali (custodie chitarra, tastiere compatte)",
        dims=[(95, 118), (14, 40), (35, 42)],
        weight=(3.0, 9.5), value=(140, 650),
        gravity=(80, 95), rot_mode="upright",
    ),
    "pet_supplies": dict(
        label="Prodotti per animali (sacchi mangime, cucce, trasportini)",
        dims=[(35, 90), (25, 60), (12, 65)],
        weight=(3.0, 18.0), value=(20, 130),
        gravity=(20, 40), rot_mode="free",
    ),
    "office_supplies": dict(
        label="Forniture per ufficio (risme carta, sedie da ufficio, cancelleria)",
        dims=[(30, 70), (25, 45), (12, 62)],
        weight=(2.5, 19.0), value=(15, 260),
        gravity=(25, 55), rot_mode="mixed_free_upright", rot_upright_share=0.35,
    ),
}

PARTIAL_ROTATIONS = {
    "bicycles": "0145",         # non va mai appoggiata sul fianco stretto (rot. 2,3)
    "musical_instruments": "01",
}

# ---------------------------------------------------------------------------
# 3) TEMI (mix di categorie) usati per comporre gli scenari dei 50 dataset
#    (stessi 16 temi della generazione precedente, riletti in chiave di
#    consegna locale / distribuzione regionale su furgone medio o piccolo,
#    non piu' trasporto intermodale)
# ---------------------------------------------------------------------------
THEMES = {
    "elettronica_consumer": {
        "electronics_small": 0.45, "electronics_large": 0.25,
        "small_appliances": 0.20, "personal_care": 0.10,
    },
    "libri_editoria": {
        "books_media": 0.85, "office_supplies": 0.15,
    },
    "misto_generico_ecommerce": {
        "electronics_small": 0.12, "books_media": 0.14, "toys_games": 0.12,
        "clothing_footwear": 0.16, "kitchenware_glass": 0.08,
        "groceries_canned": 0.10, "tools_hardware": 0.08,
        "personal_care": 0.08, "pet_supplies": 0.06, "office_supplies": 0.06,
    },
    "abbigliamento_calzature": {
        "clothing_footwear": 0.70, "sports_fitness_light": 0.18, "personal_care": 0.12,
    },
    "casa_cucina": {
        "kitchenware_glass": 0.45, "small_appliances": 0.35, "groceries_canned": 0.20,
    },
    "giocattoli_gioco": {
        "toys_games": 0.80, "books_media": 0.20,
    },
    "sport_tempo_libero": {
        "sports_fitness_light": 0.35, "sports_fitness_heavy": 0.30,
        "bicycles": 0.15, "clothing_footwear": 0.20,
    },
    "fai_da_te_utensili": {
        "tools_hardware": 0.70, "furniture_flatpack": 0.30,
    },
    "alimentari_bevande": {
        "groceries_canned": 0.55, "beverages_liquids": 0.45,
    },
    "grande_distribuzione_mista": {
        # distribuzione regionale verso piccoli negozi/supermercati locali
        # (scala compatibile col furgone Ducato medio, non trasporto
        # intermodale/industriale)
        "groceries_canned": 0.30, "beverages_liquids": 0.25,
        "kitchenware_glass": 0.15, "personal_care": 0.10,
        "small_appliances": 0.10, "clothing_footwear": 0.10,
    },
    "arredamento_flatpack": {
        "furniture_flatpack": 0.65, "large_appliances": 0.20, "office_supplies": 0.15,
    },
    "elettrodomestici_grandi": {
        "large_appliances": 0.55, "small_appliances": 0.45,
    },
    "ufficio_forniture": {
        "office_supplies": 0.55, "electronics_small": 0.25, "books_media": 0.20,
    },
    "musica_hobby": {
        "musical_instruments": 0.35, "toys_games": 0.35, "books_media": 0.30,
    },
    "pet_shop": {
        "pet_supplies": 0.75, "groceries_canned": 0.25,
    },
    "reso_magazzino_stress": {
        # mix ampio e generico usato per i 2 dataset da 900-1000 item
        "electronics_small": 0.10, "electronics_large": 0.05, "small_appliances": 0.08,
        "books_media": 0.12, "toys_games": 0.10, "clothing_footwear": 0.12,
        "kitchenware_glass": 0.06, "groceries_canned": 0.10, "beverages_liquids": 0.06,
        "tools_hardware": 0.08, "personal_care": 0.06, "pet_supplies": 0.04,
        "office_supplies": 0.03,
    },
}


def sample_category_item(rng, cat_key, idx, force_rotation=None):
    """Campiona un item della categoria cat_key. force_rotation puo' essere
    'upright' o 'free' per forzare la modalita' di rotazione (usato nei
    dataset dimostrativi per mostrare entrambi i casi anche su categorie a
    modalita' mista)."""
    c = CATEGORIES[cat_key]
    (wlo, whi), (dlo, dhi), (hlo, hhi) = c["dims"]
    width = round(rng.uniform(wlo, whi), 1)
    depth = round(rng.uniform(dlo, dhi), 1)
    height = round(rng.uniform(hlo, hhi), 1)

    wlo_w, whi_w = c["weight"]
    weight = rng.uniform(wlo_w, whi_w)
    weight = round(weight, 3) if weight < 2 else round(weight, 2)

    vlo, vhi = c["value"]
    t = rng.random() ** 1.6
    value = vlo + t * (vhi - vlo)
    value = round(value, 2)

    glo, ghi = c["gravity"]
    gravity = round(rng.uniform(glo, ghi), 1)

    rot_mode = c["rot_mode"]
    if force_rotation == "upright":
        rotations = PARTIAL_ROTATIONS.get(cat_key, "01")
    elif force_rotation == "free":
        rotations = "012345"
    elif rot_mode == "free":
        rotations = "012345"
    elif rot_mode == "upright":
        rotations = PARTIAL_ROTATIONS.get(cat_key, "01")
    elif rot_mode == "mixed_free_upright":
        share = c.get("rot_upright_share", 0.3)
        rotations = "01" if rng.random() < share else "012345"
    else:
        rotations = "012345"

    return dict(
        id=f"I{idx:04d}",
        width=width, depth=depth, height=height,
        weight=weight, value=value,
        allowedRotations=rotations, gravityStrength=gravity,
    )


def weighted_choice(rng, weight_map):
    keys = list(weight_map.keys())
    weights = list(weight_map.values())
    return rng.choices(keys, weights=weights, k=1)[0]


def generate_items(rng, theme_key, n_items):
    theme = THEMES[theme_key]
    items = []
    for i in range(n_items):
        cat_key = weighted_choice(rng, theme)
        items.append(sample_category_item(rng, cat_key, i))
    return items


def generate_items_curated(rng, cat_list):
    items = []
    for i, entry in enumerate(cat_list):
        if isinstance(entry, tuple):
            cat_key, force_rot = entry
        else:
            cat_key, force_rot = entry, None
        items.append(sample_category_item(rng, cat_key, i, force_rotation=force_rot))
    return items


def write_dataset(name, theme_key, n_items, rng_seed, curated_cats=None):
    rng = random.Random(rng_seed)
    if curated_cats is not None:
        items = generate_items_curated(rng, curated_cats)
    else:
        items = generate_items(rng, theme_key, n_items)

    folder = os.path.join(BASE_OUT, name)
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "items.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "width", "depth", "height", "weight", "value",
                    "allowedRotations", "gravityStrength"])
        for it in items:
            w.writerow([it["id"], it["width"], it["depth"], it["height"],
                        it["weight"], it["value"], it["allowedRotations"],
                        it["gravityStrength"]])

    # vehicles.csv: SEMPRE le stesse 2 righe fisse, identiche in ogni dataset
    with open(os.path.join(folder, "vehicles.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["type", "width", "depth", "height", "maxWeight", "maxValue"])
        for v in FIXED_VEHICLES:
            w.writerow([v["type"], v["width"], v["depth"], v["height"],
                        v["maxWeight"], v["maxValue"]])

    return dict(
        name=name, theme=theme_key, n_items=len(items),
        total_weight=round(sum(i["weight"] for i in items), 1),
        total_value=round(sum(i["value"] for i in items), 1),
    )


# ---------------------------------------------------------------------------
# 4) DATASET DIMOSTRATIVI (curati per mostrare tutta la varieta' dello schema)
# ---------------------------------------------------------------------------
demo_meta = []

DEMO1_CATS = [
    ("electronics_large", "upright"),
    ("beverages_liquids", "upright"),
    ("books_media", "free"),
    ("toys_games", "free"),
    ("tools_hardware", "free"),
]
demo_meta.append(write_dataset(
    "dataset_prova_1", None, 5, rng_seed=1001, curated_cats=DEMO1_CATS))

DEMO2_CATS = [
    ("electronics_small", "upright"),
    ("electronics_small", "free"),
    "electronics_large",
    "small_appliances",
    "large_appliances",
    "books_media",
    "toys_games",
    "clothing_footwear",
    "kitchenware_glass",
    "beverages_liquids",
    "groceries_canned",
    "furniture_flatpack",
    "sports_fitness_light",
    "sports_fitness_heavy",
    "bicycles",
    "tools_hardware",
    "personal_care",
    "musical_instruments",
    "pet_supplies",
    "office_supplies",
]
demo_meta.append(write_dataset(
    "dataset_prova_2", None, 20, rng_seed=1002, curated_cats=DEMO2_CATS))

# ---------------------------------------------------------------------------
# 5) 50 DATASET DI TEST PRESTAZIONALI
# ---------------------------------------------------------------------------
# Ogni riga: (indice, theme_key, n_items). Il veicolo NON compare piu' qui:
# e' sempre la stessa coppia fissa in ogni dataset. Numero di item pensato
# per un furgone Ducato medio (~11 m3, 1200 kg) o un furgone Torino piccolo
# (~2.75 m3, 660 kg): da poche decine (consegna locale) a qualche centinaio
# (giro di distribuzione regionale su piu' punti vendita), con 2 dataset
# portati a ~900-1000 item come caso limite esplicito e volutamente non
# realistico per questi 2 mezzi.

DATASET_PLAN = [
    (1,  "elettronica_consumer",       25),
    (2,  "libri_editoria",             40),
    (3,  "misto_generico_ecommerce",   60),
    (4,  "abbigliamento_calzature",    30),
    (5,  "casa_cucina",                45),
    (6,  "giocattoli_gioco",           55),
    (7,  "sport_tempo_libero",         35),
    (8,  "fai_da_te_utensili",         40),
    (9,  "alimentari_bevande",         90),
    (10, "grande_distribuzione_mista", 120),
    (11, "arredamento_flatpack",       25),
    (12, "elettrodomestici_grandi",    18),
    (13, "ufficio_forniture",          50),
    (14, "musica_hobby",               22),
    (15, "pet_shop",                   35),
    (16, "elettronica_consumer",       70),
    (17, "libri_editoria",             85),
    (18, "misto_generico_ecommerce",  100),
    (19, "abbigliamento_calzature",    75),
    (20, "casa_cucina",                65),
    (21, "giocattoli_gioco",          130),
    (22, "sport_tempo_libero",         60),
    (23, "fai_da_te_utensili",         95),
    (24, "alimentari_bevande",        150),
    (25, "reso_magazzino_stress",     950),   # CASO LIMITE
    (26, "grande_distribuzione_mista",180),
    (27, "arredamento_flatpack",       70),
    (28, "elettrodomestici_grandi",    45),
    (29, "ufficio_forniture",         100),
    (30, "musica_hobby",               40),
    (31, "pet_shop",                   80),
    (32, "elettronica_consumer",      110),
    (33, "libri_editoria",            160),
    (34, "misto_generico_ecommerce",  190),
    (35, "abbigliamento_calzature",   170),
    (36, "casa_cucina",               140),
    (37, "giocattoli_gioco",          210),
    (38, "sport_tempo_libero",        150),
    (39, "fai_da_te_utensili",        180),
    (40, "alimentari_bevande",        240),
    (41, "grande_distribuzione_mista",260),
    (42, "arredamento_flatpack",      110),
    (43, "elettrodomestici_grandi",    65),
    (44, "ufficio_forniture",         150),
    (45, "musica_hobby",               90),
    (46, "pet_shop",                  140),
    (47, "elettronica_consumer",      200),
    (48, "misto_generico_ecommerce",  280),
    (49, "grande_distribuzione_mista",300),
    (50, "reso_magazzino_stress",    1000),   # CASO LIMITE
]

assert len(DATASET_PLAN) == 50
assert len({p[0] for p in DATASET_PLAN}) == 50

perf_meta = []
for idx, theme_key, n_items in DATASET_PLAN:
    name = f"Dataset{idx}"
    meta = write_dataset(name, theme_key, n_items, rng_seed=3000 + idx)
    perf_meta.append(meta)

print("=== DATASET DIMOSTRATIVI ===")
for m in demo_meta:
    print(m)

print("\n=== DATASET DI TEST (50) ===")
for m in perf_meta:
    print(m)

print("\nTotale cartelle generate:", len(demo_meta) + len(perf_meta))
