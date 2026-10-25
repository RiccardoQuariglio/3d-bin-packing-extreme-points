# Sensibilità del costo all'ordinamento degli item: per ogni dataset e per ciascuno
# dei 2 veicoli fissi (furgone_ducato_medio, furgone_torino_piccolo), confronta il
# costo di best-fit e first-fit a 4 livelli di probabilità di pescare un item
# casuale invece del prossimo in ordine (0/10/20/30%), rispetto al first-fit non
# randomico dello stesso dataset/veicolo. Computazionalmente rifà lo stesso lavoro
# di generate_all_solutions.py (stessi _pack() sugli stessi dataset) girato
# standalone; la differenza è solo nell'output: qui tutti i 50 dataset (per
# veicolo) finiscono in un'unica tabella combinata
# (thesis_results_only_csv/randomization_comparison_{vehicle_type}.md), più
# facile da leggere a colpo d'occhio rispetto ai file separati per dataset.
import os
import random

from instances import Instance
from s324305_3d_packing_algorithm import s324305_3d_packing_algorithm
from s324305_3d_packing_algorithm.s324305_3d_packing_algorithm import BEST_FIT, FIRST_FIT

OUTPUT_DIR = 'thesis_results_only_csv'
DATASETS = [f'Dataset{i}' for i in range(1, 51)]
VEHICLES = ['furgone_ducato_medio', 'furgone_torino_piccolo']
RANDOM_LEVELS = [0.0, 0.10, 0.20, 0.30]
STRATEGIES = [BEST_FIT, FIRST_FIT]
SEED_BASE = 1000  # stesso seed per best-fit e first-fit allo stesso livello (resettato tra i due)


def fmt_number(value, decimals):
    # Formato italiano: virgola come separatore decimale
    return f'{value:.{decimals}f}'.replace('.', ',')


def fmt_signed_pct(value):
    sign = '+' if value > 1e-9 else ('-' if value < -1e-9 else '')
    return f'{sign}{fmt_number(abs(value), 2)}%'


def compute_dataset_rows(dataset_name, vehicle_type, solver=None):
    """
    Esegue best-fit e first-fit ai 4 livelli di randomicità (0/10/20/30%) su un
    singolo dataset, sempre con lo stesso `vehicle_type`, e ritorna le 8 righe
    (costo = n. container aperti, delta% rispetto al first-fit non randomico
    dello stesso dataset/veicolo). Riusabile sia dal batch su tutti i dataset
    (main() qui sotto) sia da uno script su un singolo dataset (es. main.py),
    passando un solver gia' costruito per non ricaricare il dataset due volte.
    """
    if solver is None:
        inst = Instance(dataset_name)
        solver = s324305_3d_packing_algorithm(inst)

    rows = []
    baseline_cost = None
    for level_idx, level in enumerate(RANDOM_LEVELS):
        seed = SEED_BASE + level_idx
        for strategy in STRATEGIES:
            rng = random.Random(seed)  # stesso seed per best/first allo stesso livello
            result = solver._pack(strategy, vehicle_type, random_pick_prob=level, rng=rng)
            # Funzione obiettivo = n. di container aperti (non c'è più un costo per container)
            n_containers = len(result.containers_utilizzati)

            if strategy is FIRST_FIT and level == 0.0:
                baseline_cost = n_containers

            rows.append({
                'dataset': dataset_name,
                'vehicle_type': vehicle_type,
                'level': level,
                'strategy': strategy.name,
                'n_containers': n_containers,
            })

    for row in rows:
        row['delta_pct'] = (row['n_containers'] - baseline_cost) / baseline_cost * 100 if baseline_cost else 0.0
    return rows


def write_markdown_table(rows, out_path, title):
    headers = ['Dataset', 'Randomicità', 'Strategia', 'Costo (n. container aperti)',
               'Δcosto vs first-fit 0% (stesso dataset)']
    lines = [
        title,
        '',
        'Ogni riga confronta il costo (n. di container aperti) ottenuto introducendo una',
        "probabilità di pescare un item casuale invece del prossimo in ordine",
        '(`sortedItemsByAHW`), rispetto al costo del first-fit non randomico (0%) sullo',
        'stesso dataset.',
        '',
        '| ' + ' | '.join(headers) + ' |',
        '|' + '|'.join(['---'] * len(headers)) + '|',
    ]
    for row in rows:
        level_label = f"{row['level']:.0%}"
        lines.append(
            '| ' + ' | '.join([
                row['dataset'],
                level_label,
                row['strategy'],
                str(row['n_containers']),
                fmt_signed_pct(row['delta_pct']),
            ]) + ' |'
        )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    for vehicle_type in VEHICLES:
        rows = []
        for dataset_name in DATASETS:
            print(f"=== {dataset_name} ({vehicle_type}) ===")
            dataset_rows = compute_dataset_rows(dataset_name, vehicle_type)
            rows.extend(dataset_rows)
            for row in dataset_rows:
                print(f"  livello={row['level']:.0%}  {row['strategy']:10s}  "
                      f"container={row['n_containers']}")

        out_path = os.path.join(OUTPUT_DIR, f'randomization_comparison_{vehicle_type}.md')
        write_markdown_table(
            rows, out_path,
            title=f"# Sensibilità del costo all'ordinamento degli item (randomizzazione) — "
                  f"tutti i dataset ({vehicle_type})")
        print(f"\nScritto: {out_path}")


if __name__ == '__main__':
    main()
