-- === STAGING (carga cruda desde CSV) ===
CREATE SCHEMA IF NOT EXISTS staging;

-- productos crudos
DROP TABLE IF EXISTS staging.productos_raw;
CREATE TABLE staging.productos_raw(
  id_ext    TEXT,
  nombre    TEXT,
  categoria TEXT,
  familia   TEXT
);

-- pedidos crudos canon (una fila por item) - todo TEXT
DROP TABLE IF EXISTS staging.pedidos_raw;
CREATE TABLE staging.pedidos_raw(
  sucursal      TEXT,
  producto      TEXT,
  categoria     TEXT,
  familia       TEXT,
  cantidad      TEXT,
  fecha_emision TEXT,
  dni_empleado  TEXT,
  dni_admin     TEXT
);

\copy staging.productos_raw(id_ext,nombre,categoria,familia) FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/catalog/productos.csv' CSV HEADER;

-- === Cargar TODOS los pedidos desde processed/ ===
-- _pedidos_unificado_tmp.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_1;
CREATE TABLE staging.tmp_1 ("sucursal" TEXT, "fecha_emision" TEXT, "dni_empleado" TEXT, "dni_admin" TEXT, "producto" TEXT, "categoria" TEXT, "familia" TEXT, "cantidad" TEXT);
\copy staging.tmp_1 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/_pedidos_unificado_tmp.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT
  NULLIF(TRIM(t."sucursal"),'') AS sucursal,
  NULLIF(TRIM(t."producto"),'') AS producto,
  NULLIF(TRIM(t."categoria"),'')  AS categoria,
  NULLIF(TRIM(t."familia"),'')  AS familia,
  NULLIF(TRIM(t."cantidad"),'') AS cantidad,
  NULLIF(TRIM(t."fecha_emision"),'') AS fecha_emision,
  NULLIF(TRIM(t."dni_empleado"),'') AS dni_empleado,
  NULLIF(TRIM(t."dni_admin"),'') AS dni_admin
FROM staging.tmp_1 t
WHERE COALESCE(NULLIF(TRIM(t."cantidad"),'')::int, 0) > 0;

-- pedidos_suc_catam1.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_2;
CREATE TABLE staging.tmp_2 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_2 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_catam1.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_2 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_catam2.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_3;
CREATE TABLE staging.tmp_3 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_3 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_catam2.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_3 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_catam3.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_4;
CREATE TABLE staging.tmp_4 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_4 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_catam3.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_4 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_catam4.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_5;
CREATE TABLE staging.tmp_5 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_5 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_catam4.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_5 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_catam5.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_6;
CREATE TABLE staging.tmp_6 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_6 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_catam5.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_6 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_monteagudo1.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_7;
CREATE TABLE staging.tmp_7 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_7 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_monteagudo1.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_7 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_monteagudo2.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_8;
CREATE TABLE staging.tmp_8 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_8 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_monteagudo2.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_8 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_monteagudo3.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_9;
CREATE TABLE staging.tmp_9 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_9 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_monteagudo3.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_9 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_monteagudo4.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_10;
CREATE TABLE staging.tmp_10 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_10 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_monteagudo4.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_10 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_sept1.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_11;
CREATE TABLE staging.tmp_11 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_11 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_sept1.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_11 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_sept2.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_12;
CREATE TABLE staging.tmp_12 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_12 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_sept2.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_12 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_sept3.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_13;
CREATE TABLE staging.tmp_13 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_13 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_sept3.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_13 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_yerba1.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_14;
CREATE TABLE staging.tmp_14 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_14 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_yerba1.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_14 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_yerba2.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_15;
CREATE TABLE staging.tmp_15 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_15 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_yerba2.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_15 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_yerba3.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_16;
CREATE TABLE staging.tmp_16 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_16 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_yerba3.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_16 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';

-- pedidos_suc_yerba4.csv -> tmp + mapeo por nombre
DROP TABLE IF EXISTS staging.tmp_17;
CREATE TABLE staging.tmp_17 ("producto_id" TEXT, "producto" TEXT, "familia" TEXT, "categoria" TEXT, "pozo" TEXT, "salon" TEXT, "mandar" TEXT);
\copy staging.tmp_17 FROM 'C:/Users/anapt/Repositorios/TP1-Bases_de_datos/data/processed/pedidos_suc_yerba4.csv' CSV HEADER;
INSERT INTO staging.pedidos_raw(sucursal, producto, categoria, familia, cantidad, fecha_emision, dni_empleado, dni_admin)
SELECT v.sucursal,
       NULLIF(TRIM(t."producto"),'') AS producto,
       NULLIF(TRIM(t."categoria"),'')  AS categoria,
       NULLIF(TRIM(t."familia"),'')  AS familia,
       v.cantidad,
       NULL AS fecha_emision,
       NULL AS dni_empleado,
       NULL AS dni_admin
FROM staging.tmp_17 t
CROSS JOIN LATERAL (
  VALUES ('pozo', NULLIF(TRIM(t."pozo"),'')), ('salon', NULLIF(TRIM(t."salon"),'')), ('mandar', NULLIF(TRIM(t."mandar"),''))
) AS v(sucursal, cantidad)
WHERE v.cantidad IS NOT NULL AND v.cantidad <> '' AND v.cantidad <> '0';


-- === DIMENSIONES ===
INSERT INTO app.categoria(nombre)
SELECT DISTINCT TRIM(categoria) FROM staging.productos_raw WHERE NULLIF(TRIM(categoria),'') IS NOT NULL
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO app.categoria(nombre)
SELECT DISTINCT TRIM(categoria) FROM staging.pedidos_raw WHERE NULLIF(TRIM(categoria),'') IS NOT NULL
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO app.familia(nombre)
SELECT DISTINCT TRIM(familia) FROM staging.productos_raw WHERE NULLIF(TRIM(familia),'') IS NOT NULL
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO app.familia(nombre)
SELECT DISTINCT TRIM(familia) FROM staging.pedidos_raw WHERE NULLIF(TRIM(familia),'') IS NOT NULL
ON CONFLICT (nombre) DO NOTHING;

-- Productos desde productos.csv
INSERT INTO app.producto(nombre, id_categoria, id_familia)
SELECT DISTINCT TRIM(p.nombre), c.id_categoria, f.id_familia
FROM staging.productos_raw p
JOIN app.categoria c ON c.nombre = TRIM(p.categoria)
JOIN app.familia   f ON f.nombre = TRIM(p.familia)
WHERE NULLIF(TRIM(p.nombre),'') IS NOT NULL
ON CONFLICT (nombre, id_categoria, id_familia) DO NOTHING;

-- Productos que aparezcan solo en pedidos
INSERT INTO app.producto(nombre, id_categoria, id_familia)
SELECT DISTINCT TRIM(r.producto), c.id_categoria, f.id_familia
FROM staging.pedidos_raw r
JOIN app.categoria c ON c.nombre = TRIM(r.categoria)
JOIN app.familia   f ON f.nombre = TRIM(r.familia)
WHERE NULLIF(TRIM(r.producto),'') IS NOT NULL
ON CONFLICT (nombre, id_categoria, id_familia) DO NOTHING;

-- SUCURSALES (dirección inline)
INSERT INTO app.sucursal (nombre, calle, numero, piso, depto, localidad, cp)
SELECT DISTINCT
  INITCAP(pr.sucursal),
  'Av. ' || INITCAP(pr.sucursal),
  1, NULL, NULL, INITCAP(pr.sucursal), '0000'
FROM staging.pedidos_raw pr
WHERE NULLIF(TRIM(sucursal),'') IS NOT NULL
ON CONFLICT DO NOTHING;

-- USUARIOS (si vienen en largo)
INSERT INTO app.usuario(dni, nombre, id_suc, activo)
SELECT DISTINCT pr.dni_empleado, 'Empleado '||pr.dni_empleado, s.id_suc, TRUE
FROM staging.pedidos_raw pr JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)
WHERE NULLIF(TRIM(pr.dni_empleado),'') IS NOT NULL
ON CONFLICT (dni) DO NOTHING;

INSERT INTO app.empleado(dni)
SELECT DISTINCT pr.dni_empleado
FROM staging.pedidos_raw pr
WHERE NULLIF(TRIM(pr.dni_empleado),'') IS NOT NULL
ON CONFLICT (dni) DO NOTHING;

INSERT INTO app.usuario(dni, nombre, id_suc, activo)
SELECT DISTINCT pr.dni_admin, 'Admin '||pr.dni_admin, s.id_suc, TRUE
FROM staging.pedidos_raw pr JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)
WHERE NULLIF(TRIM(pr.dni_admin),'') IS NOT NULL
ON CONFLICT (dni) DO NOTHING;

INSERT INTO app.administrador(dni)
SELECT DISTINCT pr.dni_admin
FROM staging.pedidos_raw pr
WHERE NULLIF(TRIM(pr.dni_admin),'') IS NOT NULL
ON CONFLICT (dni) DO NOTHING;

-- Índice único para no duplicar cabeceras
CREATE UNIQUE INDEX IF NOT EXISTS uq_pedido_natural
ON app.pedido (id_suc, fecha_emision, dni_empleado, dni_admin);

-- CABECERAS
WITH cab AS (
  SELECT DISTINCT s.id_suc,
    NULLIF(TRIM(pr.fecha_emision),'') AS fecha_txt,
    NULLIF(TRIM(pr.dni_empleado),'')  AS dni_empleado,
    NULLIF(TRIM(pr.dni_admin),'')     AS dni_admin
  FROM staging.pedidos_raw pr
  JOIN app.sucursal s ON s.nombre = INITCAP(pr.sucursal)
)
INSERT INTO app.pedido(id_suc, fecha_emision, dni_empleado, dni_admin)
SELECT id_suc,
  CASE WHEN fecha_txt ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}( [0-9]{2}(:[0-9]{2})?)?$' THEN fecha_txt::timestamp
       ELSE timestamp '2000-01-01 00:00:00' END,
  dni_empleado, dni_admin
FROM cab
ON CONFLICT DO NOTHING;

-- ÍTEMS (contiene)  (cantidad > 0)
INSERT INTO app.contiene(id_producto, id_pedido, cantidad)
SELECT p.id_producto, ped.id_pedido, NULLIF(TRIM(pr.cantidad),'')::int
FROM staging.pedidos_raw pr
JOIN app.categoria c ON c.nombre = TRIM(pr.categoria)
JOIN app.familia   f ON f.nombre = TRIM(pr.familia)
JOIN app.producto  p ON p.nombre = TRIM(pr.producto)
                     AND p.id_categoria = c.id_categoria
                     AND p.id_familia   = f.id_familia
JOIN app.sucursal  s ON s.nombre = INITCAP(pr.sucursal)
JOIN app.pedido   ped ON ped.id_suc = s.id_suc
  AND ped.fecha_emision = CASE
      WHEN NULLIF(TRIM(pr.fecha_emision),'') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}( [0-9]{2}(:[0-9]{2})?)?$' THEN pr.fecha_emision::timestamp
      ELSE timestamp '2000-01-01 00:00:00'
  END
  AND (ped.dni_empleado IS NOT DISTINCT FROM NULLIF(TRIM(pr.dni_empleado),''))
  AND (ped.dni_admin    IS NOT DISTINCT FROM NULLIF(TRIM(pr.dni_admin),''))
WHERE COALESCE(NULLIF(TRIM(pr.cantidad),'')::int, 0) > 0;
