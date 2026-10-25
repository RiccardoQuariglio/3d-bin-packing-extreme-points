try:
    from .item import Item
    from .container import Container
    from .singleSolutionFeasible import SingleSolutionFeasible
except ImportError:
    from item import Item
    from container import Container
    from singleSolutionFeasible import SingleSolutionFeasible

"""
    Ordine delle funzioni nel file packing_methods:
    1) loadItems(df_items) --> memorizza gli items in una lista non ordinata
    2) loadContainer(df_vehicles, vehicle_type) --> costruisce il container "template" per il
       veicolo richiesto esplicitamente (vehicle_type, es. 'furgone_ducato_medio' o
       'furgone_torino_piccolo'): vehicles.csv puo' avere piu' righe (piu' tipi di veicolo
       disponibili per il dataset), ma il solver ne usa sempre e solo UNO per ogni singola
       run, scelto dal chiamante — non c'e' scelta automatica (niente più chooseContainer).
       Vedi newContainerInstance per come se ne aprono copie durante il packing.
    3) sortedItemsByAHW(items) --> ordina gli items di una lista per area e altezza decrescente
    4) newContainerInstance(template) --> crea una nuova istanza vuota di container a partire dal
       template scelto, usata ogni volta che serve aprire un container dello stesso tipo
    5) bestFitIsFeasible(item_to_pack, container) --> verifica che un item possa essere impaccato in un container;
       per ogni EP valido crea una SingleSolutionFeasible passandole il RS corrente dell'EP
       (container.ep_residual_space), che computeMerit userà per calcolare il merito. Usata dal
       best-fit (serve l'elenco completo per poter scegliere il merito massimo).
    5b) firstFitIsFeasible(item_to_pack, container) --> variante di bestFitIsFeasible per il first-fit:
        stessa iterazione rotazioni/EP, ma ritorna alla prima soluzione fattibile trovata (lista
        con un solo elemento) senza calcolarne il merito, per non sprecare lavoro inutile al
        first-fit e non falsare il confronto dei tempi con il best-fit.
    6) packItemIntoContainer(best_solution) --> impacca l'item, aggiorna gli extreme points e,
       tramite updateResidualSpace, il loro Residual Space
    7) canTakeProjection(item_new, other, direction) --> verifica proiezioni per generare la
       posizione dei nuovi extreme points (Algoritmo 1 del paper)
    8) shrinkResidualSpace(ep_pos, rs, item) --> dato il RS attuale di un EP, lo restringe se
        l'item passato si frappone lungo un asse tra l'EP e ciò che stava tracciando finora
        (Sez. 4.3 del paper, criterio Residual Space). Blocco geometrico elementare, riusato sia
        da updateResidualSpace (un item alla volta) sia da packItemIntoContainer in fase di
        inizializzazione dei nuovi EP (contro tutti gli item già piazzati nel container)
    9) updateResidualSpace(container, item) --> Algoritmo 2 del paper: dopo il piazzamento di
        item, aggiorna il RS di tutti gli EP superstiti del container richiamando
        shrinkResidualSpace contro il solo item appena piazzato; chiamata da packItemIntoContainer
    """

class PackingMethods:

    @staticmethod
    def loadItems(df_items):
        items_list = []
        for idx, row in df_items.iterrows():
            new_item = Item(
                item_id=idx,
                width=row['width'],
                depth=row['depth'],
                height=row['height'],
                weight=row['weight'],
                value=row['value'],
                allowed_rotations=row['allowedRotations'],
                gravity_strength=row['gravityStrength']
            )
            items_list.append(new_item)
        return items_list

    @staticmethod
    def loadContainer(df_vehicles, vehicle_type):
        # Costruisce il container "template" per il SOLO vehicle_type richiesto
        # (df_vehicles.loc[vehicle_type], indice = colonna 'type' di vehicles.csv).
        # newContainerInstance ricava da questo template una copia vuota ogni volta
        # che il solver deve aprire un nuovo container dello stesso tipo.
        row = df_vehicles.loc[vehicle_type]
        return Container(
            type_name=vehicle_type,
            width=row['width'],
            depth=row['depth'],
            height=row['height'],
            max_weight=row['maxWeight'],
            max_value=row['maxValue']
        )


    @staticmethod
    def sortedItemsByAHW(items):
    #Ordina gli oggetti basandosi sulle loro dimensioni massime potenziali
        def getBestMetrics(item):
            max_h = 0
            max_area = 0
            
            for rot_idx in item.allowed_rotations:
                item.setRotation(rot_idx)
                max_area = max(max_area, item.curr_width * item.curr_depth)
                max_h = max(max_h, item.curr_height)
                
            return max_area, max_h, item.weight

        sorted_list = sorted(items, key= getBestMetrics, reverse=True)
        return sorted_list

    @staticmethod
    def newContainerInstance(template: Container):
        # Apre un nuovo container dello stesso tipo del template (nessun costo,
        # nessuna scelta automatica: il tipo è quello deciso a monte da chi ha
        # chiamato loadContainer): "aprire un container" è copiare il template
        # in un'istanza vuota, pronta per essere riempita.
        return Container(
            type_name=template.type,
            width=template.width,
            depth=template.depth,
            height=template.height,
            max_weight=template.max_weight,
            max_value=template.max_value
        )

    @staticmethod
    def bestFitIsFeasible(item_to_pack: Item, container: Container):
        #Verifica peso e valore item (basta uno dei due a sforare per essere infeasible)
        if item_to_pack.weight > container.remaining_weight:
            return None
        if item_to_pack.value > container.remaining_value:
            return None

        feasible_solutions = []

        # Salvo lo stato corrente per ripristinarlo a fine funzione (l'item non è ancora piazzato)
        saved_rotation = item_to_pack.curr_rotation_number

        # Itero su tutte le rotazioni ammesse per questo item
        for rot_idx in item_to_pack.allowed_rotations:
            item_to_pack.setRotation(rot_idx)

            for ep in container.extreme_points:
                (ex, ey, ez) = ep
                (item_to_pack.x_position, item_to_pack.y_position, item_to_pack.z_position) = (ex, ey, ez)

                #Verifica limiti container (x->depth, y->width, z->height)
                if not (ex + item_to_pack.curr_depth <= container.depth and
                        ey + item_to_pack.curr_width <= container.width and
                        ez + item_to_pack.curr_height <= container.height):
                    continue

                #Verifica sovrapposizioni con altri oggetti nel container
                overlapping = False
                for box_placed in container.items_placed:
                    if item_to_pack.boxesOverlap(box_placed):
                        overlapping = True
                        break
                if overlapping:
                    continue

                #Verifica Gravity Strength
                if ez == 0:
                    pass  # tocca il pavimento, sempre supportato
                else:
                    current_support_area = 0.0
                    min_support_area = (item_to_pack.curr_width * item_to_pack.curr_depth *
                                        (item_to_pack.gravity_strength / 100.0))
                    for box_placed in container.items_placed:
                        current_support_area += item_to_pack.getSupportArea(box_placed)
                    if current_support_area + 1e-9 < min_support_area:
                        continue

                feasible_solution = SingleSolutionFeasible(
                    container,
                    item_to_pack,
                    item_width=item_to_pack.curr_width,
                    item_depth=item_to_pack.curr_depth,
                    item_height=item_to_pack.curr_height,
                    ep=ep,
                    rotation=item_to_pack.curr_rotation_number,
                    rs=container.ep_residual_space[ep])
                feasible_solution.computeMerit()
                feasible_solutions.append(feasible_solution)

        # Ripristino lo stato dell'item (non è ancora piazzato qui)
        item_to_pack.setRotation(saved_rotation)
        (item_to_pack.x_position, item_to_pack.y_position, item_to_pack.z_position) = (None, None, None)

        if not feasible_solutions:
            return None
        return feasible_solutions

    @staticmethod
    def firstFitIsFeasible(item_to_pack: Item, container: Container):
        # Variante "first fit" di bestFitIsFeasible: stessa iterazione rotazioni/EP, ma si
        # ferma (return) alla PRIMA soluzione fattibile trovata, e non chiama mai
        # computeMerit() perché il first-fit non lo usa - calcolarlo per ogni combinazione
        # sarebbe lavoro sprecato e falserebbe il confronto dei tempi di esecuzione con il
        # best-fit. bestFitIsFeasible non viene toccata (resta quella usata dal best-fit)
        # per non rischiare di comprometterla: la duplicazione dei controlli
        # bounds/overlap/gravity qui sotto è voluta, non un refactor condiviso.
        if item_to_pack.weight > container.remaining_weight:
            return None
        if item_to_pack.value > container.remaining_value:
            return None

        saved_rotation = item_to_pack.curr_rotation_number

        for rot_idx in item_to_pack.allowed_rotations:
            item_to_pack.setRotation(rot_idx)

            for ep in container.extreme_points:
                (ex, ey, ez) = ep
                (item_to_pack.x_position, item_to_pack.y_position, item_to_pack.z_position) = (ex, ey, ez)

                #Verifica limiti container (x->depth, y->width, z->height)
                if not (ex + item_to_pack.curr_depth <= container.depth and
                        ey + item_to_pack.curr_width <= container.width and
                        ez + item_to_pack.curr_height <= container.height):
                    continue

                #Verifica sovrapposizioni con altri oggetti nel container
                overlapping = False
                for box_placed in container.items_placed:
                    if item_to_pack.boxesOverlap(box_placed):
                        overlapping = True
                        break
                if overlapping:
                    continue

                #Verifica Gravity Strength
                if ez == 0:
                    pass  # tocca il pavimento, sempre supportato
                else:
                    current_support_area = 0.0
                    min_support_area = (item_to_pack.curr_width * item_to_pack.curr_depth *
                                        (item_to_pack.gravity_strength / 100.0))
                    for box_placed in container.items_placed:
                        current_support_area += item_to_pack.getSupportArea(box_placed)
                    if current_support_area + 1e-9 < min_support_area:
                        continue

                # Trovata la prima soluzione fattibile: niente merito, si ripristina lo
                # stato dell'item e si ritorna subito (nessun'altra rotazione/EP viene provata).
                feasible_solution = SingleSolutionFeasible(
                    container,
                    item_to_pack,
                    item_width=item_to_pack.curr_width,
                    item_depth=item_to_pack.curr_depth,
                    item_height=item_to_pack.curr_height,
                    ep=ep,
                    rotation=item_to_pack.curr_rotation_number,
                    rs=container.ep_residual_space[ep])

                item_to_pack.setRotation(saved_rotation)
                (item_to_pack.x_position, item_to_pack.y_position, item_to_pack.z_position) = (None, None, None)
                return [feasible_solution]

        # Ripristino lo stato dell'item (non è ancora piazzato qui)
        item_to_pack.setRotation(saved_rotation)
        (item_to_pack.x_position, item_to_pack.y_position, item_to_pack.z_position) = (None, None, None)
        return None


    @staticmethod
    def packItemIntoContainer(solution: SingleSolutionFeasible):
        #Variabili prese dalla soluzione
        container = solution.container
        item = solution.item

        #Aggiornamento Item
        (ex, ey, ez) = solution.ep
        (item.x_position, item.y_position, item.z_position) = (ex, ey, ez)
        item.curr_width = solution.item_width
        item.curr_depth = solution.item_depth
        item.curr_height = solution.item_height
        item.curr_rotation_number = solution.item_rotation

        #Aggiornamento Container
        container.remaining_weight -= item.weight
        container.remaining_value -= item.value
        container.items_placed.append(item)


        # L'EP della soluzione è stato consumato dall'item appena piazzato: va tolto
        # dalla lista degli EP disponibili del container (e dal relativo RS).
        if solution.ep in container.extreme_points:
            container.extreme_points.remove(solution.ep)
            del container.ep_residual_space[solution.ep]

        # Algoritmo 2 (Sez. 4.3): l'item appena piazzato può ridurre il Residual Space
        # degli EP superstiti, se si frappone lungo un asse tra l'EP e ciò che stava tracciando.
        PackingMethods.updateResidualSpace(container, item)

        # Per ogni direzione, tra tutti gli altri item nel container, si cerca quello più
        # vicino su cui l'item appena piazzato può proiettare uno spigolo (canTakeProjection).
        # max_bounds tiene il valore scalare (coordinata) del candidato migliore trovato finora
        # per quella direzione (-1 = nessuno ancora); new_ex_points il punto 3D corrispondente
        # ((None, None, None) finché non se ne trova uno valido).
        max_bounds = {"YX": -1,
                      "YZ": -1,
                      "XY": -1,
                      "XZ": -1,
                      "ZX": -1,
                      "ZY": -1 }
        new_ex_points = {"YX": (None, None, None),
                      "YZ": (None, None, None),
                      "XY": (None, None, None),
                      "XZ": (None, None, None),
                      "ZX": (None, None, None),
                      "ZY": (None, None, None) }

        for other in container.items_placed:
            if other == item: continue

            # --- DIREZIONI CON SUPPORTO SU Y ---
            # YX: proiettiamo lo spigolo x (xk+dk) verso Y, cerchiamo supporto su faccia X
            if PackingMethods.canTakeProjection(item, other, "YX"):
                potential_y = other.y_position + other.curr_width
                if potential_y > max_bounds["YX"]:
                    max_bounds["YX"] = potential_y
                    new_ex_points["YX"] = (item.x_position + item.curr_depth, potential_y, item.z_position)

            # YZ: proiettiamo lo spigolo z (zk+hk) verso Y, cerchiamo supporto su faccia Z
            if PackingMethods.canTakeProjection(item, other, "YZ"):
                potential_y = other.y_position + other.curr_width
                if potential_y > max_bounds["YZ"]:
                    max_bounds["YZ"] = potential_y
                    new_ex_points["YZ"] = (item.x_position, potential_y, item.z_position + item.curr_height)

            # --- DIREZIONI CON SUPPORTO SU X ---
            # XY: proiettiamo lo spigolo y (yk+wk) verso X, cerchiamo supporto su faccia Y
            if PackingMethods.canTakeProjection(item, other, "XY"):
                potential_x = other.x_position + other.curr_depth
                if potential_x > max_bounds["XY"]:
                    max_bounds["XY"] = potential_x
                    new_ex_points["XY"] = (potential_x, item.y_position + item.curr_width, item.z_position)

            # XZ: proiettiamo lo spigolo z (zk+hk) verso X, cerchiamo supporto su faccia Z
            if PackingMethods.canTakeProjection(item, other, "XZ"):
                potential_x = other.x_position + other.curr_depth
                if potential_x > max_bounds["XZ"]:
                    max_bounds["XZ"] = potential_x
                    new_ex_points["XZ"] = (potential_x, item.y_position, item.z_position + item.curr_height)

            # --- DIREZIONI CON SUPPORTO SU Z ---
            # ZX: proiettiamo lo spigolo x (xk+dk) verso Z, cerchiamo supporto su faccia X
            if PackingMethods.canTakeProjection(item, other, "ZX"):
                potential_z = other.z_position + other.curr_height
                if potential_z > max_bounds["ZX"]:
                    max_bounds["ZX"] = potential_z
                    new_ex_points["ZX"] = (item.x_position + item.curr_depth, item.y_position, potential_z)

            # ZY: proiettiamo lo spigolo y (yk+wk) verso Z, cerchiamo supporto su faccia Y
            if PackingMethods.canTakeProjection(item, other, "ZY"):
                potential_z = other.z_position + other.curr_height
                if potential_z > max_bounds["ZY"]:
                    max_bounds["ZY"] = potential_z
                    new_ex_points["ZY"] = (item.x_position, item.y_position + item.curr_width, potential_z)

        # I 3 vertici diretti dell'item sono sempre candidati EP validi, indipendentemente
        # dalla presenza di altri item (coprono il caso in cui nessun "other" fa da supporto
        # in una direzione, equivalente al caso "container vuoto" del paper).
        base_pts = [
            (item.x_position + item.curr_depth, item.y_position, item.z_position),
            (item.x_position, item.y_position + item.curr_width, item.z_position),
            (item.x_position, item.y_position, item.z_position + item.curr_height)
        ]

        # Inserimento finale nella lista degli EP del container
        for p in (list(new_ex_points.values()) + base_pts):
            if p not in container.extreme_points and p != (None, None, None):
                # Verifichiamo i limiti fisici del bin
                if p[0] <= container.depth and p[1] <= container.width and p[2] <= container.height:
                    container.extreme_points.append(p)
                    # RS iniziale del nuovo EP: si parte dalle pareti del container e si
                    # restringe contro ogni item già piazzato (incluso quello appena inserito),
                    # per non sovrastimare lo spazio libero fin dalla creazione dell'EP.
                    rs = (container.depth - p[0], container.width - p[1], container.height - p[2])
                    for placed_item in container.items_placed:
                        rs = PackingMethods.shrinkResidualSpace(p, rs, placed_item)
                    container.ep_residual_space[p] = rs

        # Ordinamento EP (z, y, x non decrescente)
        container.extreme_points.sort(key=lambda p: (p[2], p[1], p[0]))


    @staticmethod
    def canTakeProjection(item_new, other, direction):
        """
        Verifica se il punto spigolo dell'item_new può essere proiettato
        sulla faccia dell'other nella direzione specificata.
        """
        # Coordinate e dimensioni item_new (nuovo)
        x_new, y_new, z_new = item_new.x_position, item_new.y_position, item_new.z_position
        w_new, d_new, h_new = item_new.curr_width, item_new.curr_depth, item_new.curr_height

        # Coordinate e dimensioni other (già presente)
        x_other, y_other, z_other = other.x_position, other.y_position, other.z_position
        w_other, d_other, h_other = other.curr_width, other.curr_depth, other.curr_height


        if direction == "YX":
            # Punto (x_new+d_new, y_new, z_new) proiettato in Y, cerchiamo supporto su X
            # Requisito: Il punto deve essere nel range X e Z dell'other
            # e trovarsi 'davanti' (y maggiore) rispetto a other
            return (x_other <= x_new + d_new < x_other + d_other) and (z_other <= z_new < z_other + h_other) and (y_other + w_other <= y_new)

        elif direction == "YZ":
            # Punto (x_new, y_new, z_new+h_new) proiettato in Y, cerchiamo supporto su Z
            return (x_other <= x_new < x_other + d_other) and (y_other + w_other <= y_new) and (z_other <= z_new + h_new < z_other + h_other)

        elif direction == "XY":
            # Punto (x_new, y_new+w_new, z_new) proiettato in X, cerchiamo supporto su Y
            return (y_other <= y_new + w_new < y_other + w_other) and (z_other <= z_new < z_other + h_other) and (x_other + d_other <= x_new)

        elif direction == "XZ":
            # Punto (x_new, y_new, z_new+h_new) proiettato in X, cerchiamo supporto su Z
            return (y_other <= y_new < y_other + w_other) and (z_other <= z_new + h_new < z_other + h_other) and (x_other + d_other <= x_new)

        elif direction == "ZX":
            # Punto (x_new+d_new, y_new, z_new) proiettato in Z, cerchiamo supporto su X
            return (x_other <= x_new + d_new < x_other + d_other) and (y_other <= y_new < y_other + w_other) and (z_other + h_other <= z_new)

        elif direction == "ZY":
            # Punto (x_new, y_new+w_new, z_new) proiettato in Z, cerchiamo supporto su Y
            return (y_other <= y_new + w_new < y_other + w_other) and (x_other <= x_new < x_other + d_other) and (z_other + h_other <= z_new)

        return False

    @staticmethod
    def shrinkResidualSpace(ep_pos, rs, item):
        """
        Restringe (se necessario) il Residual Space di un EP considerando UN item già
        piazzato: se l'item si frappone lungo un asse tra l'EP e ciò che stava tracciando,
        il RS su quell'asse si riduce alla distanza dalla faccia vicina dell'item.
        Ricostruzione della funzione "isOnSide" dell'Algoritmo 2 del paper (non definita
        esplicitamente nel testo), derivata dalla definizione di RS come distanza dalla
        parete o dall'item più vicino.
        """
        (ex, ey, ez) = ep_pos
        (rs_depth, rs_width, rs_height) = rs
        (ix, iy, iz) = (item.x_position, item.y_position, item.z_position)
        (i_depth, i_width, i_height) = (item.curr_depth, item.curr_width, item.curr_height)

        # Blocco lungo depth/width: l'item deve condividere la stessa fascia di height dell'EP
        if iz <= ez < iz + i_height:
            # L'item è "davanti" all'EP lungo depth e copre la sua posizione lungo width?
            if ex <= ix and iy <= ey < iy + i_width:
                rs_depth = min(rs_depth, ix - ex)
            # L'item è "davanti" all'EP lungo width e copre la sua posizione lungo depth?
            if ey <= iy and ix <= ex < ix + i_depth:
                rs_width = min(rs_width, iy - ey)

        # Blocco lungo height: l'item deve coprire l'EP sull'impronta depth/width
        if ez <= iz and ix <= ex < ix + i_depth and iy <= ey < iy + i_width:
            rs_height = min(rs_height, iz - ez)

        return (rs_depth, rs_width, rs_height)

    @staticmethod
    def updateResidualSpace(container, item):
        """
        Algoritmo 2 del paper: dopo aver piazzato item, aggiorna incrementalmente il RS
        di tutti gli EP superstiti del container, confrontandoli con il solo item appena
        piazzato (non con l'intera storia del container: per questo resta economico).
        """
        for ep_pos in container.extreme_points:
            container.ep_residual_space[ep_pos] = PackingMethods.shrinkResidualSpace(
                ep_pos, container.ep_residual_space[ep_pos], item)








