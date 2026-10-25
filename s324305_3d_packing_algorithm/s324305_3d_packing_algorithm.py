""" Classe principale che presenta la logica del codice, 
    implementando il best-fit e il first-fit. Le funzioni
    sono sviluppate nel file packing_methods.py
"""
import os
import random
import time
from collections import namedtuple

import pandas as pd
from instances.instance import Instance
from writing_and_checking_solutions import write_thesis_solution

try:
    from .packing_methods import PackingMethods
except ImportError:
    from packing_methods import PackingMethods

# Strategia di selezione tra le soluzioni fattibili trovate per un item:
#   - select_solution: funzione che, data la lista (non vuota) di SingleSolutionFeasible
#     raccolte sui container gia' aperti, restituisce quella da impaccare
#   - check_feasibility: funzione di PackingMethods usata per interrogare un singolo
#     container (bestFitIsFeasible per il best-fit, che calcola tutte le combinazioni EP/rotazione
#     con il relativo merito; firstFitIsFeasible per il first-fit, che si ferma alla prima
#     soluzione trovata e non calcola il merito, evitando lavoro inutile a quella euristica)
_FitStrategy = namedtuple('_FitStrategy', ['name', 'select_solution', 'check_feasibility'])
_PackingResult = namedtuple('_PackingResult', ['sol', 'containers_utilizzati'])


def _select_best_fit(solutions):
    return max(solutions, key=lambda s: s.merit)


def _select_first_fit(solutions):
    return solutions[0]


BEST_FIT = _FitStrategy('best_fit', _select_best_fit, PackingMethods.bestFitIsFeasible)
FIRST_FIT = _FitStrategy('first_fit', _select_first_fit, PackingMethods.firstFitIsFeasible)


class s324305_3d_packing_algorithm:

    def __init__(self, inst: Instance):
        self.name = 's324305_3d_packing_algorithm'
        self.inst = inst
        self.packing_methods = PackingMethods()

        # Popolati da solve(): una soluzione per ciascuna delle due euristiche a confronto.
        self.sol_best_fit = None
        self.sol_first_fit = None
        self._best_fit_containers = []
        self._first_fit_containers = []
        self._best_fit_time = None
        self._first_fit_time = None

    def solve(self, write_html, vehicle_type):
        """
        Esegue best-fit e first-fit separatamente sullo stesso dataset, sempre con lo
        stesso `vehicle_type` (vedi _pack()). `write_html=False` salta la generazione
        degli HTML di visualizzazione (thesis_results_with_images/) e scrive solo i CSV.
        `vehicle_type` è obbligatorio (nessuna scelta automatica tra i veicoli disponibili
        in vehicles.csv, se ce n'è più di uno): dev'essere uno dei valori dell'indice
        (colonna 'type') di self.inst.df_vehicles.
        """
        t0 = time.perf_counter()
        best_result = self._pack(BEST_FIT, vehicle_type)
        self._best_fit_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        first_result = self._pack(FIRST_FIT, vehicle_type)
        self._first_fit_time = time.perf_counter() - t0

        self.sol_best_fit = best_result.sol
        self.sol_first_fit = first_result.sol
        self._best_fit_containers = best_result.containers_utilizzati
        self._first_fit_containers = first_result.containers_utilizzati

        self.write_solution_to_file(write_html=write_html, vehicle_type=vehicle_type)

    def _pack(self, strategy: _FitStrategy, vehicle_type, random_pick_prob=0.0, rng=None):
        """
        Metodo costituito da più step:
        1) Memorizzazione degli items del dataset in una lista, e caricamento del container
           template per `vehicle_type` (vedi loadContainer/newContainerInstance)
        2) Sorting degli items secondo uno specifico criterio
        3) Apertura del primo container (copia del template): da qui in avanti c'è il vero impaccamento
        4) Calcolo soluzioni fattibili per ogni container aperto, ciclando su di essi
        5.0 - 5.1) Si sceglie la soluzione (criterio dato da `strategy`) e si impacca
                   finalmente l'item, andando ad aggiornare lista_items, container coinvolto.
                   Se l'item non entra in nessuno dei container già aperti, se ne apre uno nuovo
                   (sempre una copia dello stesso template: non c'è scelta automatica tra i
                   veicoli disponibili, `vehicle_type` è deciso dal chiamante).
        5.2) Se anche in un container appena aperto (vuoto) l'item non entra, viene scartato
             (con un warning) per evitare un loop infinito.

        `random_pick_prob` (test di sensibilità all'ordinamento, non usato da solve()): ad ogni
        iterazione, con questa probabilità si pesca un item a caso tra quelli rimanenti invece
        di prendere sempre il prossimo in ordine (`items_list[0]`). Con 0.0 (default) il
        comportamento è identico a prima, byte per byte.
        """
        if random_pick_prob and rng is None:
            rng = random.Random()

        # 1.0) Memorizzazione Items
        items_list = self.packing_methods.loadItems(self.inst.df_items)
        # 1.1) Container template per il veicolo richiesto
        container_template = self.packing_methods.loadContainer(self.inst.df_vehicles, vehicle_type)

        # 2) Ordina gli item per area di base e altezza decrescente (euristica: i più ingombranti vengono piazzati per primi)
        items_list = self.packing_methods.sortedItemsByAHW(items_list)

        sol = self._new_sol_dict()
        idx_vehicle = 0
        containers_utilizzati = []

        def _open_new_container():
            nonlocal idx_vehicle
            new_container = self.packing_methods.newContainerInstance(container_template)
            new_container.idx = idx_vehicle
            idx_vehicle += 1
            containers_utilizzati.append(new_container)
            return new_container

        # 3) Apertura del primo container
        if items_list:
            _open_new_container()

        #4) Per ogni container, vedere se ci sono soluzioni fattibili, e aggiungerli alla lista totale (delle soluz fattibili)
        while items_list:
            if random_pick_prob and rng.random() < random_pick_prob:
                pick_idx = rng.randrange(len(items_list))
            else:
                pick_idx = 0
            item_to_pack = items_list[pick_idx]
            bool_placed = False
            all_feasible_solutions = []
            for container in containers_utilizzati:
                container_feasible_solutions = strategy.check_feasibility(item_to_pack, container)
                if container_feasible_solutions:
                    all_feasible_solutions.extend(container_feasible_solutions)

            # 5.0) Se ci sono soluzioni fattibili, sceglierne una secondo `strategy`
            #      e impaccare l'item nel container
            if all_feasible_solutions:
                bool_placed = True
                chosen_solution = strategy.select_solution(all_feasible_solutions)
                self.packing_methods.packItemIntoContainer(chosen_solution)
                items_list.pop(pick_idx)
                self._append_placement(sol, chosen_solution)

            # 5.1) Se non c'è nessuna soluzione fattibile nei container già aperti, se ne apre uno
            #      nuovo (copia vuota dello stesso template) e ci si prova.
            if not bool_placed:
                new_container = _open_new_container()
                feasible_solutions = strategy.check_feasibility(item_to_pack, new_container)
                if feasible_solutions is not None:
                    chosen_solution = strategy.select_solution(feasible_solutions)
                    self.packing_methods.packItemIntoContainer(chosen_solution)
                    bool_placed = True
                    items_list.pop(pick_idx)
                    self._append_placement(sol, chosen_solution)
                else:
                    containers_utilizzati.pop()
                    idx_vehicle -= 1

            if not bool_placed:
                # 5.2) Nemmeno un container vuoto riesce a contenere l'item: lo scartiamo con un
                # warning. Per evitare loop infinito, rimuoviamo comunque l'item dalla lista,
                # registrando che non è stato possibile piazzarlo (la soluzione sarà infeasible per items mancanti,
                # ma il solver termina invece di bloccarsi).
                print(f"WARNING [{strategy.name}]: l'item {item_to_pack.id} non è stato posizionato "
                      f"neanche in un container vuoto.")
                items_list.pop(pick_idx)

        return _PackingResult(sol=sol, containers_utilizzati=containers_utilizzati)

    @staticmethod
    def _new_sol_dict():
        return {
            'type_vehicle': [],
            'idx_vehicle': [],
            'id_item': [],
            'x_origin': [],
            'y_origin': [],
            'z_origin': [],
            'orient': [],
        }

    @staticmethod
    def _append_placement(sol, solution):
        sol['type_vehicle'].append(solution.container.type)
        sol['idx_vehicle'].append(solution.container.idx)
        sol['id_item'].append(solution.item.id)
        sol['x_origin'].append(solution.ep[0])
        sol['y_origin'].append(solution.ep[1])
        sol['z_origin'].append(solution.ep[2])
        sol['orient'].append(solution.item_rotation)

    def write_solution_to_file(self, write_html, vehicle_type):
        if write_html:
            self._write_html_solutions(vehicle_type)
        self._write_csv_comparison(vehicle_type)

    def _write_html_solutions(self, vehicle_type):
        # Solo il first-fit non randomico: e' la soluzione di riferimento per la
        # visualizzazione, un file HTML per dataset+veicolo (il best-fit resta solo nei CSV).
        df_sol = pd.DataFrame.from_dict(self.sol_first_fit)
        write_thesis_solution(
            self.inst.df_items, self.inst.df_vehicles, df_sol, self.inst.name,
            f'{self.name}_first_fit_{vehicle_type}',
            output_dir='thesis_results_with_images'
        )

    def _write_csv_comparison(self, vehicle_type):
        dataset_name = self.inst.name
        out_dir = os.path.join('thesis_results_only_csv', f'Solution {dataset_name}')
        os.makedirs(out_dir, exist_ok=True)

        # Funzione obiettivo = n. di container aperti (non c'è più un costo per container):
        # il confronto chiave tra best-fit e first-fit è quindi tra questo valore e il tempo
        # di esecuzione. Nome file con suffisso vehicle_type: solve() puo' essere chiamata
        # una volta per veicolo sullo stesso dataset, non deve sovrascrivere l'altra.
        comparison = pd.DataFrame({
            'strategy': ['best_fit', 'first_fit'],
            'n_containers': [len(self._best_fit_containers), len(self._first_fit_containers)],
            'execution_time_seconds': [self._best_fit_time, self._first_fit_time],
        })
        comparison.to_csv(
            os.path.join(out_dir, f'{dataset_name}_comparison_bestFit_firstFit_{vehicle_type}.csv'), index=False)

        pd.DataFrame.from_dict(self.sol_best_fit).to_csv(
            os.path.join(out_dir, f'{dataset_name}_solution_bestFit_{self.name}_{vehicle_type}.csv'), index=False)
        pd.DataFrame.from_dict(self.sol_first_fit).to_csv(
            os.path.join(out_dir, f'{dataset_name}_solution_firstFit_{self.name}_{vehicle_type}.csv'), index=False)
