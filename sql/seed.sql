-- === STAGING (carga cruda desde CSV) ===
CREATE SCHEMA IF NOT EXISTS staging;

-- productos crudos (nombre, categoria, familia)
DROP TABLE IF EXISTS staging.productos_raw;
CREATE TABLE staging.productos_raw(
  nombre TEXT,
  categoria TEXT,
  familia TEXT
);

-- pedidos crudos (una fila por item)
DROP TABLE IF EXISTS staging.pedidos_raw;
CREATE TABLE staging.pedidos_raw(
  sucursal TEXT,
  fecha_emision TIMESTAMP,
  dni_empleado TEXT,
  dni_admin TEXT,
  producto TEXT,
  categoria TEXT,
  familia TEXT,
  cantidad INTEGER
);

\copy staging.productos_raw(nombre,categoria,familia) FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/catalog/productos.csv' CSV HEADER;

\copy staging.pedidos_raw FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/_pedidos_unificado_tmp.csv' CSV HEADER;

-- === DIMENSIONES ===
-- Categorías y Familias
INSERT INTO app.categoria(nombre)
SELECT DISTINCT TRIM(categoria) FROM staging.productos_raw WHERE NULLIF(TRIM(categoria),'') IS NOT NULL
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO app.familia(nombre)
SELECT DISTINCT TRIM(familia) FROM staging.productos_raw WHERE NULLIF(TRIM(familia),'') IS NOT NULL
ON CONFLICT (nombre) DO NOTHING;

-- Productos
INSERT INTO app.producto(nombre, id_categoria, id_familia)
SELECT DISTINCT
  TRIM(p.nombre), c.id_categoria, f.id_familia
FROM staging.productos_raw p
JOIN app.categoria c ON c.nombre = TRIM(p.categoria)
JOIN app.familia   f ON f.nombre = TRIM(p.familia)
WHERE NULLIF(TRIM(p.nombre),'') IS NOT NULL
ON CONFLICT (nombre, id_categoria, id_familia) DO NOTHING;

-- También considerar categorías/familias que aparezcan en pedidos aunque no figuren en productos.csv
INSERT INTO app.categoria(nombre)
SELECT DISTINCT TRIM(categoria) FROM staging.pedidos_raw WHERE NULLIF(TRIM(categoria),'') IS NOT NULL
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO app.familia(nombre)
SELECT DISTINCT TRIM(familia) FROM staging.pedidos_raw WHERE NULLIF(TRIM(familia),'') IS NOT NULL
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO app.producto(nombre, id_categoria, id_familia)
SELECT DISTINCT
  TRIM(r.producto), c.id_categoria, f.id_familia
FROM staging.pedidos_raw r
JOIN app.categoria c ON c.nombre = TRIM(r.categoria)
JOIN app.familia   f ON f.nombre = TRIM(r.familia)
WHERE NULLIF(TRIM(r.producto),'') IS NOT NULL
ON CONFLICT (nombre, id_categoria, id_familia) DO NOTHING;

-- === SUCURSALES (y direcciones dummy) ===
INSERT INTO app.direccion(calle,numero,piso,depto,localidad,cp)
SELECT DISTINCT
  'Av. '||INITCAP(sucursal), 1, NULL, NULL, INITCAP(sucursal), '0000'
FROM staging.pedidos_raw pr
WHERE NULLIF(TRIM(sucursal),'') IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO app.sucursal(nombre, id_direccion)
SELECT DISTINCT
  INITCAP(pr.sucursal) AS nombre, d.id_direccion
FROM staging.pedidos_raw pr
JOIN app.direccion d ON d.localidad = INITCAP(pr.sucursal) AND d.cp='0000'
ON CONFLICT DO NOTHING;

-- === USUARIOS detectados en pedidos (empleados/admins con DNIs) ===
INSERT INTO app.usuario(dni, nombre, id_suc, activo)
SELECT DISTINCT pr.dni_empleado, 'Empleado '||pr.dni_empleado, s.id_suc, TRUE
FROM staging.pedidos_raw pr
JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)
WHERE NULLIF(TRIM(pr.dni_empleado),'') IS NOT NULL
ON CONFLICT (dni) DO NOTHING;

INSERT INTO app.empleado(dni)
SELECT DISTINCT pr.dni_empleado
FROM staging.pedidos_raw pr
WHERE NULLIF(TRIM(pr.dni_empleado),'') IS NOT NULL
ON CONFLICT (dni) DO NOTHING;

INSERT INTO app.usuario(dni, nombre, id_suc, activo)
SELECT DISTINCT pr.dni_admin, 'Admin '||pr.dni_admin, s.id_suc, TRUE
FROM staging.pedidos_raw pr
JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)
WHERE NULLIF(TRIM(pr.dni_admin),'') IS NOT NULL
ON CONFLICT (dni) DO NOTHING;

INSERT INTO app.administrador(dni)
SELECT DISTINCT pr.dni_admin
FROM staging.pedidos_raw pr
WHERE NULLIF(TRIM(pr.dni_admin),'') IS NOT NULL
ON CONFLICT (dni) DO NOTHING;

-- === PEDIDOS (cabeceras) ===
WITH cab AS (
  SELECT DISTINCT
    s.id_suc,
    pr.fecha_emision,
    NULLIF(TRIM(pr.dni_empleado),'') AS dni_empleado,
    NULLIF(TRIM(pr.dni_admin),'')    AS dni_admin
  FROM staging.pedidos_raw pr
  JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)
)
INSERT INTO app.pedido(id_suc, fecha_emision, dni_empleado, dni_admin)
SELECT id_suc,
       COALESCE(fecha_emision, NOW()),
       dni_empleado,
       dni_admin
FROM cab
ON CONFLICT DO NOTHING;

-- === Ítems del pedido (contiene) ===
INSERT INTO app.contiene(id_producto, id_pedido, cantidad)
SELECT p.id_producto, ped.id_pedido, CAST(pr.cantidad AS INTEGER)
FROM staging.pedidos_raw pr
JOIN app.categoria c ON c.nombre = TRIM(pr.categoria)
JOIN app.familia   f ON f.nombre = TRIM(pr.familia)
JOIN app.producto  p ON p.nombre = TRIM(pr.producto)
                     AND p.id_categoria = c.id_categoria
                     AND p.id_familia   = f.id_familia
JOIN app.sucursal  s ON s.nombre = INITCAP(pr.sucursal)
JOIN app.pedido   ped ON ped.id_suc = s.id_suc
                      AND ped.fecha_emision = COALESCE(pr.fecha_emision, ped.fecha_emision)
                      AND (ped.dni_empleado IS NOT DISTINCT FROM NULLIF(TRIM(pr.dni_empleado),''))
                      AND (ped.dni_admin    IS NOT DISTINCT FROM NULLIF(TRIM(pr.dni_admin),''));

-- Fin de seed generado automáticamente.