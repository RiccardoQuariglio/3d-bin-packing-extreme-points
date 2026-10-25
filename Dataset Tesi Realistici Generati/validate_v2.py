# Verifica lo schema dei dataset. Uso (da qualsiasi cartella):
#   python validate_v2.py                    -> controlla ../datasets (quelli usati negli esperimenti)
#   python validate_v2.py <cartella>         -> controlla un'altra cartella (es. datasets_rigenerati,
#                                               prodotta da generate_datasets_v2.py)
import os, csv, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_HERE, os.pardir, "datasets")
errors = []
warnings = []

EXPECTED_VEHICLE_ROWS = [
    ["furgone_ducato_medio", "187", "312", "193", "1200", "60000"],
    ["furgone_torino_piccolo", "125", "182", "121", "660", "25000"],
]

folders = sorted(os.listdir(BASE))
print(f"Cartelle trovate: {len(folders)}")

for folder in folders:
    path = os.path.join(BASE, folder)
    items_path = os.path.join(path, "items.csv")
    veh_path = os.path.join(path, "vehicles.csv")
    if not os.path.exists(items_path) or not os.path.exists(veh_path):
        errors.append(f"{folder}: manca items.csv o vehicles.csv")
        continue

    with open(veh_path) as f:
        rows = list(csv.reader(f))
    if rows[0] != ["type", "width", "depth", "height", "maxWeight", "maxValue"]:
        errors.append(f"{folder}: header vehicles.csv errato: {rows[0]}")
    if len(rows) != 3:
        errors.append(f"{folder}: vehicles.csv deve avere ESATTAMENTE 2 righe dati, trovate {len(rows)-1}")
    else:
        for i, expected in enumerate(EXPECTED_VEHICLE_ROWS):
            actual = rows[1+i]
            # confronto numerico tollerante (es. "187" vs "187.0")
            if actual[0] != expected[0]:
                errors.append(f"{folder}: riga {i+1} vehicles.csv, type diverso: {actual[0]} vs {expected[0]}")
            for j in range(1, 6):
                if float(actual[j]) != float(expected[j]):
                    errors.append(f"{folder}: riga {i+1} vehicles.csv, colonna {j} diversa: {actual[j]} vs {expected[j]}")

    vehicles = {}
    for r in rows[1:]:
        vehicles[r[0]] = dict(width=float(r[1]), depth=float(r[2]), height=float(r[3]),
                               maxWeight=float(r[4]), maxValue=float(r[5]))

    with open(items_path) as f:
        rows = list(csv.reader(f))
    header = rows[0]
    expected = ["id","width","depth","height","weight","value","allowedRotations","gravityStrength"]
    if header != expected:
        errors.append(f"{folder}: header items.csv errato: {header}")

    seen_ids = set()
    for r in rows[1:]:
        rid, w, d, h, wt, val, rot, grav = r
        if rid in seen_ids:
            errors.append(f"{folder}: id duplicato {rid}")
        seen_ids.add(rid)
        if not (rid.startswith("I") and len(rid) == 5 and rid[1:].isdigit()):
            errors.append(f"{folder}: id malformato {rid}")
        try:
            w,d,h,wt,val,grav = float(w),float(d),float(h),float(wt),float(val),float(grav)
        except ValueError:
            errors.append(f"{folder}: valore numerico non parsabile in riga id={rid}")
            continue
        if w<=0 or d<=0 or h<=0:
            errors.append(f"{folder}/{rid}: dimensione non positiva")
        if wt<=0:
            errors.append(f"{folder}/{rid}: peso non positivo")
        if val<=0:
            errors.append(f"{folder}/{rid}: valore non positivo")
        if not (0 <= grav <= 100):
            errors.append(f"{folder}/{rid}: gravityStrength fuori range 0-100: {grav}")
        if not rot or any(ch not in "012345" for ch in rot):
            errors.append(f"{folder}/{rid}: allowedRotations non valido: {rot}")
        if len(set(rot)) != len(rot):
            errors.append(f"{folder}/{rid}: allowedRotations con cifre ripetute: {rot}")

        # fattibilita' dimensionale rispetto a CIASCUNO dei 2 veicoli fissi: il solver usa un
        # solo tipo di veicolo per volta, quindi ogni item deve entrare, in almeno una delle
        # SUE rotazioni ammesse (allowedRotations), in entrambi (altrimenti una delle due run
        # lo scarterebbe e la soluzione risulterebbe incompleta)
        orientations = [(w,d,h),(d,w,h),(h,d,w),(d,h,w),(w,h,d),(h,w,d)]
        allowed = [orientations[int(ch)] for ch in rot if ch in "012345"]
        for vname, v in vehicles.items():
            if not any(ow<=v["width"] and od<=v["depth"] and oh<=v["height"] for ow,od,oh in allowed):
                errors.append(f"{folder}/{rid}: nessuna rotazione ammessa ({rot}) entra in {vname} ({w}x{d}x{h})")
            # peso e valore del singolo item contro i massimi di OGNI veicolo
            if wt > v["maxWeight"]:
                errors.append(f"{folder}/{rid}: peso item ({wt}) supera la portata di {vname} ({v['maxWeight']})")
            if val > v["maxValue"]:
                errors.append(f"{folder}/{rid}: valore item ({val}) supera il massimo di {vname} ({v['maxValue']})")

    with open(items_path) as f:
        r = list(csv.DictReader(f))
    gravs = set(round(float(x["gravityStrength"]),1) for x in r)
    if len(gravs) <= 1 and len(r) > 3:
        errors.append(f"{folder}: gravityStrength costante su tutti gli item ({gravs})")
    rots = set(x["allowedRotations"] for x in r)
    if len(rots) <= 1 and len(r) > 5:
        warnings.append(f"{folder}: allowedRotations identico su tutti gli item ({rots})")

print(f"\nTotale errori: {len(errors)}")
for e in errors[:80]:
    print("ERRORE:", e)
print(f"\nTotale warning: {len(warnings)}")
for w in warnings[:30]:
    print("WARNING:", w)
