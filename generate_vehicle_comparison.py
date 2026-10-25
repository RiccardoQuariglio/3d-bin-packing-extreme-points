# Confronto best-fit/first-fit sui DUE veicoli fissi (furgone_ducato_medio,
# furgone_torino_piccolo) presenti in ogni dataset. Per ciascun dataset numerato
# (Dataset1...Dataset50) esegue 16 simulazioni (2 strategie x 4 livelli di
# randomicità x 2 veicoli) e scrive, nella cartella
# thesis_results_only_csv/Solution {dataset}/, due file:
#   1) {dataset}_comparison_4_simulazioni.csv   -> Δ% tempo e Δ% costo (n. container)
#      tra best-fit e first-fit, per ciascun veicolo, al livello 0% (non randomico).
#      4 righe: first-fit/best-fit x Ducato medio/Torino piccolo.
#   2) {dataset}_comparison_16_simulazioni.md   -> solo Δ% costo (n. container) per
#      tutte le 16 simulazioni (2 strategie x 4 livelli x 2 veicoli), rispetto al
#      first-fit non randomico dello stesso veicolo.
# solve() viene comunque chiamata (write_html=False) per ciascun veicolo: scrive
# anche i soliti CSV di dettaglio con suffisso _{vehicle_type} (comportamento
# normale, non richiesto esplicitamente ma non disattivato).
import os

from instances import Instance
from s324305_3d_packing_algorithm import s324305_3d_packing_algorithm
from generate_randomization_comparison import compute_dataset_rows

OUTPUT_DIR = 'thesis_results_only_csv'
DATASETS = [f'Dataset{i}' for i in range(1, 51)]
VEHICLES = ['furgone_ducato_medio', 'furgone_torino_piccolo']


def _fmt_number(value, decimals):
    # Formato italiano: virgola come separatore decimale
    return f'{value:.{decimals}f}'.replace('.', ',')


def _fmt_signed_pct(value):
    sign = '+' if value > 1e-9 else ('-' if value < -1e-9 else '')
    return f'{sign}{_fmt_number(abs(value), 2)}%'


def _write_4sim_csv(rows, out_path):
    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)


def _write_16sim_markdown(rows, out_path, dataset_name):
    headers = ['Veicolo', 'Randomicità', 'Strategia', 'Container',
               'Δ container vs first-fit 0% (stesso veicolo)']
    lines = [
        f"# Sensibilità del costo (n. container) all'ordinamento e al veicolo — {dataset_name}",
        '',
        'Ogni riga confronta il numero di container aperti a un certo livello di',
        'randomicità dell\'ordinamento, rispetto al first-fit non randomico (0%) dello',
        'STESSO veicolo (i due veicoli non sono confrontati direttamente in questa tabella,',
        'solo tra loro stessi a livelli di randomicità diversi).',
        '',
        '| ' + ' | '.join(headers) + ' |',
        '|' + '|'.join(['---'] * len(headers)) + '|',
    ]
    for row in rows:
        level_label = f"{row['level']:.0%}"
        lines.append(
            '| ' + ' | '.join([
                row['vehicle_type'],
                level_label,
                row['strategy'],
                str(row['n_containers']),
                _fmt_signed_pct(row['delta_pct']),
            ]) + ' |'
        )
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def process_dataset(dataset_name):
    print(f"=== {dataset_name} ===", flush=True)
    inst = Instance(dataset_name)
    out_dir = os.path.join(OUTPUT_DIR, f'Solution {dataset_name}')
    os.makedirs(out_dir, exist_ok=True)

    sim4_rows = []
    sim16_rows = []

    for vehicle_type in VEHICLES:
        solver = s324305_3d_packing_algorithm(inst)
        solver.solve(write_html=False, vehicle_type=vehicle_type)

        n_best = len(solver._best_fit_containers)
        n_first = len(solver._first_fit_containers)
        t_best = solver._best_fit_time
        t_first = solver._first_fit_time

        d_cont = (n_first - n_best) / n_first * 100 if n_first else 0.0
        d_time = (t_best - t_first) / t_first * 100 if t_first else 0.0

        sim4_rows.append({
            'vehicle_type': vehicle_type, 'strategy': 'first_fit',
            'n_containers': n_first, 'execution_time_seconds': t_first,
            'delta_containers_pct_vs_firstfit': 0.0, 'delta_time_pct_vs_firstfit': 0.0,
        })
        sim4_rows.append({
            'vehicle_type': vehicle_type, 'strategy': 'best_fit',
            'n_containers': n_best, 'execution_time_seconds': t_best,
            'delta_containers_pct_vs_firstfit': d_cont, 'delta_time_pct_vs_firstfit': d_time,
        })
        print(f"  [{vehicle_type}] best: n={n_best} t={t_best:.3f}s | "
              f"first: n={n_first} t={t_first:.3f}s | delta_container={d_cont:.2f}% delta_tempo={d_time:.2f}%", flush=True)

        rows16 = compute_dataset_rows(dataset_name, vehicle_type, solver=solver)
        sim16_rows.extend(rows16)

    _write_4sim_csv(sim4_rows, os.path.join(out_dir, f'{dataset_name}_comparison_4_simulazioni.csv'))
    _write_16sim_markdown(sim16_rows, os.path.join(out_dir, f'{dataset_name}_comparison_16_simulazioni.md'), dataset_name)


def main():
    for dataset_name in DATASETS:
        process_dataset(dataset_name)
    print("\nFatto. Output scritto in thesis_results_only_csv/Solution {Dataset}/ per ogni dataset numerato.")


if __name__ == '__main__':
    main()
