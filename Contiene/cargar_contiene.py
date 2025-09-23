import pandas as pd
import random

productos = pd.read_csv("Supabase_producto.csv")
pedidos = pd.read_csv("Supabase_pedido.csv")

contiene_rows = []

for _, pedido in pedidos.iterrows():
    id_pedido = pedido["id_pedido"]

    num_productos = random.randint(1, 4)

    productos_sample = productos.sample(num_productos)

    for _, producto in productos_sample.iterrows():
        id_producto = producto["id_producto"]

        cantidad = random.randint(1, 5)

        contiene_rows.append({
            "id_producto": id_producto,
            "id_pedido": id_pedido,
            "cantidad": cantidad
        })

contiene = pd.DataFrame(contiene_rows)

contiene.to_csv("contiene.csv", index=False)

print("Generado contiene.csv con", len(contiene), "filas")