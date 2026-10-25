# Visualizzazione 3D (Plotly) di una soluzione di packing: costruisce i box degli
# item e il wireframe dei container, li combina in un'unica figura con un
# container alla volta selezionabile da un dropdown, e produce la pagina HTML
# finale (tabella + grafico 3D, con il CSV della soluzione incorporato) tramite
# write_thesis_solution() - la funzione usata dal solver per scrivere i risultati.
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import plotly.offline as pyo
import numpy as np
import random
import os
import sys
import io
import re
import json
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from instances import Instance

# ---------------------------
# ROTATIONS
# ---------------------------
def apply_rotation(w, d, h, rot):
    if rot == 0:
        return w, d, h
    elif rot == 1:
        return d, w, h
    elif rot == 2:
        return h, d, w
    elif rot == 3:
        return d, h, w
    elif rot == 4:
        return w, h, d
    elif rot == 5:
        return h, w, d
    else:
        raise ValueError("Invalid rotation")
# ---------------------------
# DRAW BOX (ITEM)
# ---------------------------
def create_box(x, y, z, dx, dy, dz, color, name):
    vertices = np.array([
        [x, y, z],
        [x+dx, y, z],
        [x+dx, y+dy, z],
        [x, y+dy, z],
        [x, y, z+dz],
        [x+dx, y, z+dz],
        [x+dx, y+dy, z+dz],
        [x, y+dy, z+dz]
    ])

    faces = [
        [0,1,2], [0,2,3],
        [4,5,6], [4,6,7],
        [0,1,5], [0,5,4],
        [2,3,7], [2,7,6],
        [1,2,6], [1,6,5],
        [0,3,7], [0,7,4]
    ]

    i, j, k = zip(*faces)

    return go.Mesh3d(
        x=vertices[:,0],
        y=vertices[:,1],
        z=vertices[:,2],
        i=i, j=j, k=k,
        color=color,
        opacity=0.5,
        name=name
    )

# ---------------------------
# DRAW CONTAINER (WIREFRAME)
# ---------------------------
def create_container_wireframe(width, depth, height):
    # note: x=depth, y=width, z=height

    x = [0, depth, depth, 0, 0, 0, depth, depth, 0]
    y = [0, 0, width, width, 0, 0, 0, width, width]
    z = [0, 0, 0, 0, 0, height, height, height, height]

    edges = [
        (0,1),(1,2),(2,3),(3,0),  # bottom
        (4,5),(5,6),(6,7),(7,4),  # top
        (0,4),(1,5),(2,6),(3,7)   # verticals
    ]

    traces = []
    for e in edges:
        traces.append(go.Scatter3d(
            x=[x[e[0]], x[e[1]]],
            y=[y[e[0]], y[e[1]]],
            z=[z[e[0]], z[e[1]]],
            mode='lines',
            line=dict(color='black', width=3),
            showlegend=False
        ))
    return traces

# ---------------------------
# MAIN FUNCTION
# ---------------------------
def visualize_solution(df_items, df_vehicles, df_solution, idx_vehicle, output_path=None):
    fig = go.Figure()

    # filter only selected vehicle
    df_sol = df_solution[df_solution["idx_vehicle"] == idx_vehicle]

    if df_sol.empty:
        print(f"No items in vehicle {idx_vehicle}")
        return

    # Tipo di veicolo usato in questa soluzione (colonna 'type_vehicle', indice di df_vehicles)
    vehicle_type = df_sol.iloc[0]["type_vehicle"]
    vehicle = df_vehicles.loc[vehicle_type]

    cont_width = vehicle["width"]
    cont_depth = vehicle["depth"]
    cont_height = vehicle["height"]

    # draw container wireframe
    for trace in create_container_wireframe(cont_width, cont_depth, cont_height):
        fig.add_trace(trace)

    colors = {}

    for _, row in df_sol.iterrows():
        item_id = row["id_item"]
        item = df_items[df_items.index == item_id].iloc[0]

        w, d, h = item["width"], item["depth"], item["height"]
        rot = int(row["orient"])

        w, d, h = apply_rotation(w, d, h, rot)

        x = row["x_origin"]
        y = row["y_origin"]
        z = row["z_origin"]

        if item_id not in colors:
            colors[item_id] = "rgb({},{},{})".format(
                random.randint(50,200),
                random.randint(50,200),
                random.randint(50,200)
            )

        fig.add_trace(
            create_box(x, y, z, d, w, h, colors[item_id], item_id)
        )

    # layout
    fig.update_layout(
        scene=dict(
            xaxis_title="Depth (X)",
            yaxis_title="Width (Y)",
            zaxis_title="Height (Z)",
            aspectmode='data'
        ),
        title=f"Vehicle {idx_vehicle} Visualization",
        showlegend=True
    )

    if output_path is not None:
        fig.write_html(output_path)
    else:
        fig.show()

# ---------------------------
# COMBINED FIGURE (all containers as traces; caller controls which are visible)
# ---------------------------
def build_combined_figure(df_items, df_vehicles, df_solution, dataset_name):
    fig = go.Figure()
    colors = {}
    trace_ranges = []

    vehicle_ids = sorted(df_solution["idx_vehicle"].unique())

    for i, idx_vehicle in enumerate(vehicle_ids):
        df_veh = df_solution[df_solution["idx_vehicle"] == idx_vehicle]
        vehicle_type = df_veh.iloc[0]["type_vehicle"]
        vehicle = df_vehicles.loc[vehicle_type]

        start = len(fig.data)

        for trace in create_container_wireframe(vehicle["width"], vehicle["depth"], vehicle["height"]):
            trace.visible = (i == 0)
            fig.add_trace(trace)

        for _, row in df_veh.iterrows():
            item_id = row["id_item"]
            item = df_items[df_items.index == item_id].iloc[0]

            w, d, h = apply_rotation(item["width"], item["depth"], item["height"], int(row["orient"]))

            if item_id not in colors:
                colors[item_id] = "rgb({},{},{})".format(
                    random.randint(50,200),
                    random.randint(50,200),
                    random.randint(50,200)
                )

            box = create_box(row["x_origin"], row["y_origin"], row["z_origin"], d, w, h, colors[item_id], item_id)
            box.visible = (i == 0)
            fig.add_trace(box)

        trace_ranges.append((idx_vehicle, start, len(fig.data)))

    fig.update_layout(
        scene=dict(
            xaxis_title="Depth (X)",
            yaxis_title="Width (Y)",
            zaxis_title="Height (Z)",
            aspectmode='data'
        ),
        title=f"{dataset_name} - Vehicle {vehicle_ids[0]}" if vehicle_ids else dataset_name,
        showlegend=True
    )
    return fig, trace_ranges

_THESIS_PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<script type="text/javascript">__PLOTLYJS__</script>
<style>
  html, body { margin:0; padding:0; height:100%; font-family: Arial, Helvetica, sans-serif; }
  .container { display:flex; height:100vh; box-sizing:border-box; }
  #table-pane { width:38%; overflow:auto; border-right:1px solid #ccc; padding:10px; box-sizing:border-box; }
  #plot-pane { width:62%; display:flex; flex-direction:column; box-sizing:border-box; }
  #vehicle-select { margin:10px; font-size:14px; padding:4px; align-self:flex-start; }
  #plot-div { flex:1 1 auto; }
  table { border-collapse: collapse; width:100%; font-size:12px; }
  th, td { border:1px solid #ddd; padding:4px 6px; text-align:left; white-space:nowrap; }
  th { background:#f0f0f0; position:sticky; top:0; }
  tr.highlight { background-color:#ffe082; }
  h3 { margin: 4px 0 10px 0; }
</style>
</head>
<body>
<script type="application/json" id="thesis-solution-meta">__META_JSON__</script>
<script type="text/csv" id="thesis-solution-data">
__CSV_TEXT__</script>
<div class="container">
  <div id="table-pane">
    <h3>__TITLE__</h3>
    <table>
      <thead>
        <tr><th>type_vehicle</th><th>idx_vehicle</th><th>id_item</th><th>x_origin</th><th>y_origin</th><th>z_origin</th><th>orient</th></tr>
      </thead>
      <tbody>
__TABLE_ROWS__
      </tbody>
    </table>
  </div>
  <div id="plot-pane">
    <select id="vehicle-select">
__OPTIONS__
    </select>
    <div id="plot-div"></div>
  </div>
</div>
<script type="text/javascript">
  var plotData = __DATA_JSON__;
  var plotLayout = __LAYOUT_JSON__;
  var visibilityByVehicle = __VISIBILITY_JSON__;
  var datasetName = __DATASET_NAME_JSON__;

  Plotly.newPlot('plot-div', plotData, plotLayout, {responsive: true});

  function updateVehicle(vehicleId) {
    Plotly.restyle('plot-div', {visible: visibilityByVehicle[vehicleId]});
    Plotly.relayout('plot-div', {title: datasetName + ' - Vehicle ' + vehicleId});
    document.querySelectorAll('#table-pane tbody tr').forEach(function(tr) {
      tr.classList.toggle('highlight', tr.getAttribute('data-vehicle') === String(vehicleId));
    });
    var firstMatch = document.querySelector('#table-pane tbody tr[data-vehicle="' + vehicleId + '"]');
    if (firstMatch) { firstMatch.scrollIntoView({block: 'center'}); }
  }

  var select = document.getElementById('vehicle-select');
  select.addEventListener('change', function(e) { updateVehicle(e.target.value); });
  updateVehicle(select.value);
</script>
</body>
</html>
"""

# ---------------------------
# THESIS SOLUTION FILE (split-screen: data table + combined figure with a
# vehicle dropdown; selecting a vehicle highlights its rows in the table)
# ---------------------------
def write_thesis_solution(df_items, df_vehicles, df_solution, dataset_name, solver_name, output_dir='thesis_results'):
    os.makedirs(output_dir, exist_ok=True)

    fig, trace_ranges = build_combined_figure(df_items, df_vehicles, df_solution, dataset_name)

    fig_dict = json.loads(pio.to_json(fig))
    data_json = json.dumps(fig_dict['data'])
    layout_json = json.dumps(fig_dict['layout'])

    total_traces = len(fig.data)
    visibility_by_vehicle = {}
    for idx_vehicle, start, end in trace_ranges:
        visible = [False] * total_traces
        for t in range(start, end):
            visible[t] = True
        visibility_by_vehicle[str(idx_vehicle)] = visible
    visibility_json = json.dumps(visibility_by_vehicle)

    options_html = '\n'.join(
        f'      <option value="{idx_vehicle}">Vehicle {idx_vehicle}</option>'
        for idx_vehicle, _, _ in trace_ranges
    )

    table_rows_html = '\n'.join(
        '        <tr data-vehicle="{idx}"><td>{type_vehicle}</td><td>{idx}</td><td>{id_item}</td>'
        '<td>{x:.3f}</td><td>{y:.3f}</td><td>{z:.3f}</td><td>{orient}</td></tr>'.format(
            idx=row['idx_vehicle'],
            type_vehicle=escape(str(row['type_vehicle'])),
            id_item=escape(str(row['id_item'])),
            x=row['x_origin'], y=row['y_origin'], z=row['z_origin'],
            orient=row['orient']
        )
        for _, row in df_solution.iterrows()
    )

    title = f'{dataset_name} - {solver_name}'
    meta_json = json.dumps({"dataset_name": dataset_name, "solver_name": solver_name})
    csv_text = df_solution.to_csv(index=False)
    plotlyjs_source = pyo.get_plotlyjs()

    html_str = (
        _THESIS_PAGE_TEMPLATE
        .replace('__PLOTLYJS__', plotlyjs_source)
        .replace('__TITLE__', escape(title))
        .replace('__META_JSON__', meta_json)
        .replace('__CSV_TEXT__', csv_text)
        .replace('__TABLE_ROWS__', table_rows_html)
        .replace('__OPTIONS__', options_html)
        .replace('__DATA_JSON__', data_json)
        .replace('__LAYOUT_JSON__', layout_json)
        .replace('__VISIBILITY_JSON__', visibility_json)
        .replace('__DATASET_NAME_JSON__', json.dumps(dataset_name))
    )

    output_path = os.path.join(output_dir, f'sol_{dataset_name}_{solver_name}.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_str)
    return output_path

if __name__ == '__main__':

    vehicle_to_visualize = 0  # idx_vehicle da mostrare (0 = primo veicolo aperto)

    dataset_name = 'Dataset1'
    solver_name = 's324305_3d_packing_algorithm'
    vehicle_type = 'furgone_ducato_medio'  # <-- oppure 'furgone_torino_piccolo'
    inst = Instance(dataset_name)

    # -------------------------
    # Load data
    # -------------------------
    items = inst.df_items
    vehicles = inst.df_vehicles

    # Il solver scrive sempre e solo il first-fit non randomico (vedi _write_html_solutions
    # in s324305_3d_packing_algorithm.py), quindi il nome file ha sempre il suffisso
    # _first_fit_{vehicle_type} (un HTML per dataset PER veicolo).
    thesis_file = os.path.join(
        'thesis_results_with_images', f'sol_{dataset_name}_{solver_name}_first_fit_{vehicle_type}.html')
    thesis_html = open(thesis_file, encoding='utf-8').read()
    csv_text = re.search(
        r'<script type="text/csv" id="thesis-solution-data">(.*?)</script>', thesis_html, re.S).group(1)
    solution = pd.read_csv(io.StringIO(csv_text))

    visualize_solution(items, vehicles, solution, vehicle_to_visualize)
