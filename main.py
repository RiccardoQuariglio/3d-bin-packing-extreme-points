import os

from instances import Instance
from s324305_3d_packing_algorithm import s324305_3d_packing_algorithm
from generate_randomization_comparison import compute_dataset_rows, write_markdown_table

if __name__ == '__main__':

    dataset_name = 'Dataset1'  # <-- cambiare qui per eseguire su un altro dataset
    vehicle_type = 'furgone_ducato_medio'  # <-- oppure 'furgone_torino_piccolo'

    inst = Instance(dataset_name)
    solver = s324305_3d_packing_algorithm(inst)

    # 1) Soluzione "ufficiale" best-fit / first-fit (non randomici): scrive in
    #    thesis_results_only_csv/Solution {dataset_name}/ i 3 CSV (comparison + le 2 soluzioni),
    #    con suffisso vehicle_type nel nome (solve() puo' essere richiamata per l'altro veicolo
    #    sullo stesso dataset senza sovrascrivere questi file).
    #    write_html=False: solo CSV, niente HTML in thesis_results_with_images/.
    solver.solve(write_html=False, vehicle_type=vehicle_type)

    # 2) Sensibilità del costo all'ordinamento (randomizzazione), sullo stesso dataset e
    #    veicolo: aggiunge un 4o file (markdown) nella stessa cartella. Riusa il solver di
    #    sopra, cosi' non ricarica item/container una seconda volta.
    out_dir = os.path.join('thesis_results_only_csv', f'Solution {dataset_name}')
    rows = compute_dataset_rows(dataset_name, vehicle_type, solver=solver)
    write_markdown_table(
        rows, os.path.join(out_dir, f'{dataset_name}_randomization_comparison_{vehicle_type}.md'),
        title=f"# Sensibilità del costo all'ordinamento degli item — {dataset_name} ({vehicle_type})")

    print(f"Fatto. Output completo in: {out_dir}")
