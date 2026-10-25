"""Verifica TUTTE le soluzioni della campagna sperimentale del Cap. 5.

Il checker del progetto (writing_and_checking_solutions/results_checker_thesis.py)
legge una soluzione alla volta dall'HTML di visualizzazione, e gli HTML esistono
solo per una manciata di casi. La tesi pero' afferma, in sez. 4.9.1 e in sez.
5.1, che OGNI soluzione riportata e' stata validata: questo script rende vera
quell'affermazione, applicando gli stessi controlli ai 200 CSV di soluzione
(50 dataset x 2 strategie x 2 veicoli) che la campagna ha prodotto.

Controlla, per ogni veicolo di ogni soluzione:
  - contenimento nei bordi del vano;
  - assenza di sovrapposizioni fra item;
  - peso totale entro la portata;
  - valore totale entro il massimo assicurato;
  - gravity strength: per ogni item non appoggiato al pavimento, l'area di base
    sostenuta dagli item sottostanti deve coprire almeno la frazione richiesta;
  - che nessun item dell'istanza sia rimasto fuori dal piano di carico.

La tolleranza EPS ha la stessa ragione d'essere spiegata nel checker: gli
estremi dei box vengono RICALCOLATI dalle coordinate lette dal CSV, e in virgola
mobile due facce a contatto risultano sovrapposte di ~3e-14 cm.

Uso, dalla ROOT del progetto:
    python validate_all_solutions.py
"""
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.getcwd())
from instances import Instance

EPS = 1e-6
ROOT = 'thesis_results_only_csv'

ROTATIONS = [
    lambda w, d, h: (w, d, h),
    lambda w, d, h: (d, w, h),
    lambda w, d, h: (h, d, w),
    lambda w, d, h: (d, h, w),
    lambda w, d, h: (w, h, d),
    lambda w, d, h: (h, w, d),
]


def load_items(dataset):
    """id -> (w, d, h, peso, valore, gravity) dal file dell'istanza."""
    out = {}
    with open(os.path.join('datasets', dataset, 'items.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out[r['id']] = (float(r['width']), float(r['depth']), float(r['height']),
                            float(r['weight']), float(r['value']), float(r['gravityStrength']))
    return out


def check_solution(path, dataset, items, vehicles):
    """Ritorna la lista delle violazioni trovate (vuota se la soluzione e' valida)."""
    by_vehicle = {}
    placed = set()
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            by_vehicle.setdefault(int(r['idx_vehicle']), []).append(r)
            placed.add(r['id_item'])

    problems = []
    for vidx, rows in by_vehicle.items():
        veh = vehicles.loc[rows[0]['type_vehicle']]
        V_W, V_D, V_H = float(veh['width']), float(veh['depth']), float(veh['height'])
        boxes, tot_w, tot_v = [], 0.0, 0.0

        for r in rows:
            w0, d0, h0, weight, value, gravity = items[r['id_item']]
            w, d, h = ROTATIONS[int(r['orient'])](w0, d0, h0)
            x, y, z = float(r['x_origin']), float(r['y_origin']), float(r['z_origin'])
            # convenzione del codice: x -> depth, y -> width, z -> height
            box = dict(id=r['id_item'], x1=x, x2=x + d, y1=y, y2=y + w, z1=z, z2=z + h,
                       base=w * d, gravity=gravity)
            tot_w += weight
            tot_v += value

            if box['x2'] > V_D + EPS or box['y2'] > V_W + EPS or box['z2'] > V_H + EPS:
                problems.append(f'vehicle {vidx}: {box["id"]} fuori dai bordi')
            if x < -EPS or y < -EPS or z < -EPS:
                problems.append(f'vehicle {vidx}: {box["id"]} con coordinate negative')

            for other in boxes:
                if (max(box['x1'], other['x1']) + EPS < min(box['x2'], other['x2']) and
                        max(box['y1'], other['y1']) + EPS < min(box['y2'], other['y2']) and
                        max(box['z1'], other['z1']) + EPS < min(box['z2'], other['z2'])):
                    problems.append(f'vehicle {vidx}: {box["id"]} sovrapposto a {other["id"]}')
            boxes.append(box)

        if tot_w > float(veh['maxWeight']) + EPS:
            problems.append(f'vehicle {vidx}: peso {tot_w:.1f} > {veh["maxWeight"]}')
        if tot_v > float(veh['maxValue']) + EPS:
            problems.append(f'vehicle {vidx}: valore {tot_v:.1f} > {veh["maxValue"]}')

        for box in boxes:
            if box['z1'] <= EPS:
                continue                      # appoggiato al pavimento
            support = 0.0
            for other in boxes:
                if other is box or abs(other['z2'] - box['z1']) > 1e-6:
                    continue
                dx = min(box['x2'], other['x2']) - max(box['x1'], other['x1'])
                dy = min(box['y2'], other['y2']) - max(box['y1'], other['y1'])
                if dx > 0 and dy > 0:
                    support += dx * dy
            required = box['base'] * box['gravity'] / 100.0
            if support + EPS < required:
                problems.append(f'vehicle {vidx}: {box["id"]} supporto {support:.1f} < {required:.1f}')

    missing = set(items) - placed
    if missing:
        problems.append(f'{len(missing)} item non piazzati: {sorted(missing)[:5]}')
    return problems


def main():
    files = sorted(glob.glob(os.path.join(ROOT, 'Solution Dataset*', '*_solution_*.csv')))
    print(f'{len(files)} soluzioni da verificare\n')

    cache_items, cache_veh = {}, {}
    n_ok = 0
    failures = []

    for i, path in enumerate(files, 1):
        dataset = re.search(r'Solution (Dataset\d+)', path).group(1)
        if dataset not in cache_items:
            cache_items[dataset] = load_items(dataset)
            cache_veh[dataset] = Instance(dataset).df_vehicles
        problems = check_solution(path, dataset, cache_items[dataset], cache_veh[dataset])
        if problems:
            failures.append((os.path.basename(path), problems))
            print(f'  [{i:3d}/{len(files)}] VIOLAZIONI  {os.path.basename(path)}')
            for p in problems[:5]:
                print(f'        {p}')
            if len(problems) > 5:
                print(f'        ... e altre {len(problems) - 5}')
        else:
            n_ok += 1
        if i % 25 == 0:
            print(f'  ... {i}/{len(files)} verificate, {n_ok} valide finora', flush=True)

    print(f'\n{"=" * 60}')
    print(f'{n_ok}/{len(files)} soluzioni valide')
    if failures:
        print(f'{len(failures)} soluzioni con violazioni:')
        for name, problems in failures:
            print(f'  - {name}: {len(problems)} violazioni')
    else:
        print('Nessuna violazione: contenimento, sovrapposizioni, peso, valore,')
        print('gravity strength e completezza del carico sono rispettati ovunque.')


if __name__ == '__main__':
    main()
