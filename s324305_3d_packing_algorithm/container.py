class Container:
    def __init__(self, type_name, width, depth, height, max_weight, max_value):
        self.type = type_name
        self.idx = None
        self.width = width
        self.depth = depth
        self.height = height
        self.volume = width * depth * height
        self.max_weight = max_weight
        self.max_value = max_value

        #Parametri utilizzati per gestire l'impaccamento
        self.remaining_value = max_value
        self.remaining_weight = max_weight
        self.items_placed = []  # Lista di oggetti Item già posizionati
        self.extreme_points = [(0, 0, 0)]  # Inizializzazione EP
        # Residual Space per ogni EP (Sez. 4.3 del paper): distanza libera lungo ciascun
        # asse (depth, width, height) dall'ostacolo più vicino (parete o item). L'EP iniziale
        # non ha ancora ostacoli, quindi il suo RS è pari alle dimensioni piene del container.
        self.ep_residual_space = {(0, 0, 0): (self.depth, self.width, self.height)}

    # Definizione _toString che serve per testare il codice
    def __str__(self):
        return (f"Type: {self.type}, Width: {self.width}, Depth: {self.depth}, Height: {self.height}, "
                f"Max Weight: {self.max_weight}, Max Value: {self.max_value}")

    def __eq__(self, other):
        return self.idx == other.idx
    
    def __hash__(self):
        return hash(self.idx)