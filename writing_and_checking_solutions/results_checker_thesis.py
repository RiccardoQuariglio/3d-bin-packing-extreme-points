# Verifica la fattibilità di una soluzione già generata (l'HTML in
# thesis_results_with_images/, sempre il first-fit non randomico - l'unico che il
# solver scrive), leggendo il CSV incorporato nella pagina. Controlla: bounds,
# overlap tra item, peso/valore entro i massimi del container, supporto minimo di
# gravità per item non a contatto col pavimento, e che tutti gli item siano piazzati.
import os
import sys
import io
import re
import json
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from instances import Instance

if __name__ == '__main__':
    solution_file_path = 'thesis_results_with_images/sol_Dataset1_s324305_3d_packing_algorithm_first_fit_furgone_ducato_medio.html'

    # -------------------------
    # Extract embedded solution data from the thesis solution file
    # -------------------------
    with open(solution_file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    meta_match = re.search(
        r'<script type="application/json" id="thesis-solution-meta">(.*?)</script>', html, re.S)
    meta = json.loads(meta_match.group(1))
    dataset_name = meta['dataset_name']

    data_match = re.search(
        r'<script type="text/csv" id="thesis-solution-data">(.*?)</script>', html, re.S)
    solution = pd.read_csv(io.StringIO(data_match.group(1)))

    inst = Instance(dataset_name)

    # -------------------------
    # Load data
    # -------------------------
    items = inst.df_items
    vehicles = inst.df_vehicles

    # -------------------------
    # Helpers
    # -------------------------
    def get_dims(item, orient):
        w, d, h = item["width"], item["depth"], item["height"]

        rotations = [
            (w, d, h),
            (d, w, h),
            (h, d, w),
            (d, h, w),
            (w, h, d),
            (h, w, d),
        ]
        return rotations[orient]


    # Tolleranza per i confronti geometrici. Serve perche' il checker RICALCOLA
    # gli estremi dei box (x + d) partendo dalle coordinate lette dal CSV, e in
    # virgola mobile 183.4 + 31.3 non fa esattamente 214.7: due item che si
    # toccano perfettamente risultano sovrapposti di ~3e-14 cm. Senza questa
    # tolleranza il checker segnalava come OVERLAP ogni contatto faccia a faccia,
    # e bocciava soluzioni geometricamente corrette (soprattutto quelle best-fit,
    # che incastrano gli item nelle nicchie e quindi hanno molti piu' contatti).
    # 1e-6 cm = 10 nanometri: irrilevante per dati espressi in cm con un
    # decimale, ma otto ordini di grandezza sopra l'errore numerico.
    EPS = 1e-6

    def overlap_1d(a_min, a_max, b_min, b_max):
        return max(a_min, b_min) + EPS < min(a_max, b_max)


    def boxes_overlap(a, b):
        return (
            overlap_1d(a["x1"], a["x2"], b["x1"], b["x2"]) and
            overlap_1d(a["y1"], a["y2"], b["y1"], b["y2"]) and
            overlap_1d(a["z1"], a["z2"], b["z1"], b["z2"])
        )


    # -------------------------
    # Prepare lookups
    # -------------------------
    items_dict = items.to_dict("index")
    vehicles_dict = vehicles.to_dict("index")

    groups = solution.groupby("idx_vehicle")

    feasible = True
    placed_item_ids = set()

    print("\n================ SOLUTION CHECK ================\n")

    for vidx, group in groups:
        vehicle_type = group.iloc[0]['type_vehicle']
        vehicle = vehicles_dict[vehicle_type]

        vehicle_ok = True
        placed_boxes = []
        total_weight = 0
        total_value = 0

        for _, row in group.iterrows():
            item_id = row["id_item"]
            placed_item_ids.add(item_id)
            item = items_dict[item_id]

            orient = int(row["orient"])
            w, d, h = get_dims(item, orient)

            x, y, z = row["x_origin"], row["y_origin"], row["z_origin"]


            box = {
                "id": item_id,
                "x1": x, "y1": y, "z1": z,
                "x2": x + d, "y2": y + w, "z2": z + h,
                "base_area": w * d,
                "gravity": item["gravityStrength"]
            }


            # -------------------------
            # Bounds
            # -------------------------
            # stessa tolleranza dell'overlap: un item che finisce esattamente
            # sulla parete non e' fuori dai bordi
            if box["x2"] > vehicle["depth"] + EPS or \
            box["y2"] > vehicle["width"] + EPS or \
            box["z2"] > vehicle["height"] + EPS:
                print(f"\nVehicle {vidx} ({vehicle_type}):")
                print(f"OUT OF BOUNDS: {item_id}")
                vehicle_ok = False

            # -------------------------
            # Overlap
            # -------------------------
            for other in placed_boxes:
                if boxes_overlap(box, other):
                    print(f"\nVehicle {vidx} ({vehicle_type})")
                    print(f"OVERLAP: {item_id} with {other['id']}")
                    vehicle_ok = False

            placed_boxes.append(box)

            total_weight += item["weight"]
            total_value += item["value"]

        # -------------------------
        # Weight
        # -------------------------
        if total_weight > vehicle["maxWeight"]:
            print(f"\nVehicle {vidx} ({vehicle_type})")
            print(f" WEIGHT: {total_weight:.2f} > {vehicle['maxWeight']}")
            vehicle_ok = False

        # -------------------------
        # Value
        # -------------------------
        if total_value > vehicle["maxValue"]:
            print(f"\nVehicle {vidx} ({vehicle_type})")
            print(f"VALUE: {total_value:.2f} > {vehicle['maxValue']}")
            vehicle_ok = False

        # -------------------------
        # Gravity
        # -------------------------
        for i, box in enumerate(placed_boxes):
            if box["z1"] == 0:
                continue

            support_area = 0

            for j, other in enumerate(placed_boxes):
                if i == j:
                    continue

                if abs(other["z2"] - box["z1"]) < 1e-6:
                    dx = max(0, min(box["x2"], other["x2"]) - max(box["x1"], other["x1"]))
                    dy = max(0, min(box["y2"], other["y2"]) - max(box["y1"], other["y1"]))
                    support_area += dx * dy

            required = box["base_area"] * (box["gravity"] / 100.0)

            # come sopra: il supporto e' una somma di aree ricalcolate, quindi
            # va confrontata con la stessa tolleranza (il solver usa 1e-9 qui)
            if support_area + EPS < required:
                print(f"\nVehicle {vidx} ({vehicle_type})")
                print(f"GRAVITY: {box['id']} supported {support_area:.1f} < {required:.1f}")
                vehicle_ok = False

        if not vehicle_ok:
            feasible = False

    # -------------------------
    # Check that all items are placed
    # -------------------------
    all_items = set(items.index)
    missing_items = all_items - placed_item_ids

    if missing_items:
        print(f"MISSING ITEMS: {', '.join(sorted(missing_items))}")
        feasible = False

    # -------------------------
    # Final summary
    # -------------------------
    print("=============== SUMMARY ===============")
    print(f"Objective cost (n. containers): {len(groups)}")

    if feasible:
        print("FEASIBLE solution")
    else:
        print("INFEASIBLE solution")
