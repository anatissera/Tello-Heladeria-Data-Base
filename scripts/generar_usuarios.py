import os
import csv
import random
from faker import Faker

fake = Faker("es_ES")
OUTPUT_DIR = "data/fake"

SUCURSALES = [
    (1, "Microcentro"),
    (2, "Catamarca"),
    (3, "Barrio Norte"),
    (4, "Refinor"),
    (5, "Lobo de la Vega"),
    (6, "Quara"),
    (7, "Casa Central"),
    (8, "Tafí"),
]

NUM_EMPLEADOS_ACTIVOS = 8 
NUM_ENCARGADOS_ACTIVOS = 3

os.makedirs(OUTPUT_DIR, exist_ok=True)

usuarios = []
empleados = []
proveedores = []
admins = []

for id_suc, nombre_suc in SUCURSALES:
    for _ in range(NUM_ENCARGADOS_ACTIVOS):
        dni = str(fake.unique.random_number(digits=8))
        usuarios.append([dni, fake.name(), fake.date_of_birth(minimum_age=18, maximum_age=65),
                         fake.unique.email(), id_suc, True, "empleado", True])
        empleados.append([dni, True])  
    
    for _ in range(NUM_EMPLEADOS_ACTIVOS - NUM_ENCARGADOS_ACTIVOS):
        dni = str(fake.unique.random_number(digits=8))
        usuarios.append([dni, fake.name(), fake.date_of_birth(minimum_age=18, maximum_age=65),
                         fake.unique.email(), id_suc, True, "empleado", False])
        empleados.append([dni, False])

    for _ in range(random.randint(1, 3)):
        dni = str(fake.unique.random_number(digits=8))
        usuarios.append([dni, fake.name(), fake.date_of_birth(minimum_age=18, maximum_age=65),
                         fake.unique.email(), id_suc, False, "empleado",
                         random.choice([True, False])])
        empleados.append([dni, random.choice([True, False])])

for _ in range(4):  
    dni = str(fake.unique.random_number(digits=8))
    usuarios.append([dni, fake.name(), fake.date_of_birth(minimum_age=25, maximum_age=65),
                     fake.unique.email(), 7, True, "administrador", False])
    admins.append([dni])

dni = str(fake.unique.random_number(digits=8))
usuarios.append([dni, fake.name(), fake.date_of_birth(minimum_age=25, maximum_age=65),
                 fake.unique.email(), 7, False, "administrador", False])
admins.append([dni])

for _ in range(2): 
    dni = str(fake.unique.random_number(digits=8))
    usuarios.append([dni, fake.name(), fake.date_of_birth(minimum_age=18, maximum_age=65),
                     fake.unique.email(), 7, True, "proveedor", False])
    proveedores.append([dni])

dni = str(fake.unique.random_number(digits=8))
usuarios.append([dni, fake.name(), fake.date_of_birth(minimum_age=18, maximum_age=40),
                 fake.unique.email(), 7, False, "proveedor", False])
proveedores.append([dni])

with open(os.path.join(OUTPUT_DIR, "usuarios.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["dni", "nombre", "fecha_nacimiento", "mail", "id_suc", "activo", "tipo", "es_encargado"])
    writer.writerows(usuarios)

with open(os.path.join(OUTPUT_DIR, "empleados.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["dni", "es_encargado"])
    writer.writerows(empleados)

with open(os.path.join(OUTPUT_DIR, "administradores.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["dni"])
    writer.writerows(admins)

with open(os.path.join(OUTPUT_DIR, "proveedores.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["dni"])
    writer.writerows(proveedores)

print("Archivos generados en", OUTPUT_DIR)