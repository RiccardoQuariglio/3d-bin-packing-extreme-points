from __future__ import annotations


class Item:
    def __init__(self, item_id, width, depth, height, weight, value, allowed_rotations, gravity_strength):
        #Definizione degli attributi principali attraverso il costruttore
        self.id = item_id
        self.width = width
        self.depth = depth
        self.height = height
        self.volume = width * depth * height
        self.weight = weight
        self.value = value
        self.allowed_rotations = [int(ar) for ar in str(allowed_rotations)]
        self.gravity_strength = gravity_strength

        #Gestione delle rotazioni
        self.curr_width = width
        self.curr_depth = depth
        self.curr_height = height
        self.curr_rotation_number = self.allowed_rotations[0]

        #Posizione all'interno del container
        self.x_position = None
        self.y_position = None
        self.z_position = None

    #Funzione che modifica i valori 3D in base alla rotazione effettuata
    # (lista presa dal file results_checker)
    def setRotation(self, rotation_number):
        w, d, h = self.width, self.depth, self.height
        rotations = [
            (w, d, h),
            (d, w, h),
            (h, d, w),
            (d, h, w),
            (w, h, d),
            (h, w, d),
        ]
        self.curr_width, self.curr_depth, self.curr_height = rotations[rotation_number]
        self.curr_rotation_number = rotation_number

    #Definizione _toString che serve per testare il codice
    def __str__(self):
        return (f"Codice: {self.id}, Width: {self.width}, Depth: {self.depth}, Height: {self.height}, "
                f"Weight: {self.weight}, Value: {self.value}, Gravity Strength: {self.gravity_strength}.")


    #Funzione che verifica le sovrapposizioni tra gli item
    def overlapX(self, other: Item):
        return (max(self.x_position, other.x_position) <
                min(self.x_position + self.curr_depth, other.x_position + other.curr_depth))

    def overlapY(self, other: Item):
        return (max(self.y_position, other.y_position) <
                min(self.y_position + self.curr_width, other.y_position + other.curr_width))

    def overlapZ(self, other: Item):
        return (max(self.z_position, other.z_position) <
                min(self.z_position + self.curr_height, other.z_position + other.curr_height))

    def boxesOverlap(self, other):
        return (
                self.overlapX(other) and self.overlapY(other) and self.overlapZ(other)
        )

    #Funzione che verifica il supporto che un item (other) da a quello da verificare (self)
    def getSupportArea(self, other):
        #Se non è attaccato, non c'è appoggio
        if abs(self.z_position - (other.z_position + other.curr_height)) > 1e-6:
            return 0.0

        # Calcoliamo l'intersezione sugli assi X e Y
        inter_x = max(0, min(self.x_position + self.curr_depth, other.x_position + other.curr_depth) -
                      max(self.x_position, other.x_position))
        inter_y = max(0, min(self.y_position + self.curr_width, other.y_position + other.curr_width) -
                      max(self.y_position, other.y_position))

        return inter_x * inter_y
    
    def __eq__(self, other):
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
