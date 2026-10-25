
"""
Classe usata per gestire più comodamente le soluzioni fattibili.
Ha come parametri il container, l'item (e le dimensioni per cui è calcolata la soluzione)
e l'ep per cui è calcolata. Implementa la funzione ComputeMerit, così da avere sotto mano
tutti i dati poi per 1) scegliere la soluzione migliore e 2) per aggiornare il container
senza andare a cercare i dati in maniera difficile.
"""

class SingleSolutionFeasible:
    def __init__(self, container, item, item_width, item_depth, item_height, ep, rotation, rs):
        self.container = container
        self.item = item
        self.item_width = item_width
        self.item_depth = item_depth
        self.item_height = item_height
        self.ep = ep
        self.item_rotation = rotation
        self.rs = rs  # Residual Space dell'EP al momento della valutazione (depth, width, height)
        self.merit = None

    def computeMerit(self):
        # Merito dell'articolo (Sez. 4.3, criterio Residual Space, pagg. 13-14):
        # fb = somma, sui tre assi, di (RS dell'EP - dimensione dell'item in questa rotazione).
        # fb va minimizzato (poco spazio sprecato); usiamo il meno perché poi si cerca il MAX.
        rs_depth, rs_width, rs_height = self.rs
        fb = (rs_depth - self.item_depth) + (rs_width - self.item_width) + (rs_height - self.item_height)
        self.merit = -fb