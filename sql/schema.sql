CREATE SCHEMA IF NOT EXISTS app;
SET search_path TO app, public;

DO $$
BEGIN
  IF to_regtype('app.pedido_estado') IS NULL THEN
    CREATE TYPE app.pedido_estado AS ENUM ('emitido','preparado','entregado','cancelado');
  END IF;
END $$;


-- creería que no necesitamos tabla dirección porque solo lo tiene sucursal.

-- TABLA DIRECCION

CREATE TABLE app.direccion (
  ID_direccion INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  calle        TEXT NOT NULL,
  numero       INTEGER CHECK (numero > 0),
  piso         TEXT,              
  depto        TEXT,
  localidad    TEXT NOT NULL,
  cp           TEXT NOT NULL,
  UNIQUE (calle, numero, piso, depto, localidad, cp) -- para no duplicados ta ok? -> yo opino que sí pueden vivir en el mismo departamento, capaz son los padres de Athina que viven en la misma casa no sé.
);

-- TABLA SUCURSAL

CREATE TABLE app.sucursal (
  ID_suc        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre        TEXT NOT NULL,
  ID_direccion INTEGER REFERENCES app.direccion(ID_direccion) 
                ON UPDATE CASCADE 
                ON DELETE RESTRICT
);

CREATE INDEX ON app.sucursal(id_direccion); -- para los joisn con id_Dire

-- TABLA USUARIO

CREATE TABLE app.usuario(
    DNI                 TEXT PRIMARY KEY,
    nombre              TEXT NOT NULL,
    fecha_nacimiento    DATE,
    mail                TEXT UNIQUE,
    ID_suc              INTEGER REFERENCES app.sucursal(ID_suc) 
                        ON UPDATE CASCADE 
                        ON DELETE RESTRICT,
    activo              BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX ON app.usuario(id_suc);

-- SUBTIPOS DE USUARIOS

CREATE TABLE app.proveedor (
    DNI     TEXT PRIMARY KEY REFERENCES app.usuario(DNI) 
            ON UPDATE CASCADE 
            ON DELETE CASCADE
);

CREATE TABLE app.empleado(
    DNI     TEXT PRIMARY KEY REFERENCES app.usuario(DNI) 
            ON UPDATE CASCADE 
            ON DELETE CASCADE,
    es_encargado    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE app.administrador(
    DNI     TEXT PRIMARY KEY REFERENCES app.usuario(DNI) 
            ON UPDATE CASCADE 
            ON DELETE CASCADE
);

-- CATEGORIA Y FAMILIA

-- nose si conviene ids by default si es que queremos usar los ids ya asignados o no 
CREATE TABLE app.categoria (
    ID_categoria INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE app.familia (
    ID_familia INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);


CREATE TABLE app.producto (
  ID_producto  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre       TEXT NOT NULL,
  ID_categoria INTEGER NOT NULL
                REFERENCES app.categoria(ID_categoria)
                ON UPDATE CASCADE
                ON DELETE RESTRICT, 
  ID_familia   INTEGER NOT NULL
                REFERENCES app.familia(ID_familia)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
    CONSTRAINT uq_producto UNIQUE (nombre, ID_categoria, ID_familia)
);


CREATE INDEX ON app.producto(ID_categoria);
CREATE INDEX ON app.producto(ID_familia);


CREATE TABLE app.pedido (
  ID_pedido     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  estado        app.pedido_estado NOT NULL DEFAULT 'emitido',
  fecha_emision TIMESTAMP NOT NULL DEFAULT now(),
  ID_suc        INTEGER NOT NULL
                REFERENCES app.sucursal(ID_suc)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,       
  DNI_empleado  TEXT
                REFERENCES app.empleado(DNI)
                ON UPDATE CASCADE
                ON DELETE SET NULL,       -- si se va un empleado, guardo el pedido ig
  DNI_admin     TEXT
                REFERENCES app.administrador(DNI)
                ON UPDATE CASCADE
                ON DELETE SET NULL
);

CREATE INDEX ON app.pedido(id_suc);
CREATE INDEX ON app.pedido(dni_empleado);


CREATE TABLE app.entrega (
  ID_pedido       INTEGER PRIMARY KEY
                  REFERENCES app.pedido(ID_pedido)
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,     
  DNI_proveedor   TEXT NOT NULL
                  REFERENCES app.proveedor(DNI)
                  ON UPDATE CASCADE
                  ON DELETE RESTRICT,     
  DNI_empleado    TEXT
                  REFERENCES app.empleado(DNI)
                  ON UPDATE CASCADE
                  ON DELETE SET NULL,     
  fecha_recepcion TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX ON app.entrega(DNI_proveedor);


-- Relación Contiene

CREATE TABLE app.contiene (
    id_producto INTEGER NOT NULL
                REFERENCES app.producto(id_producto)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
    id_pedido   INTEGER NOT NULL
                REFERENCES app.pedido(id_pedido)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
    cantidad    INTEGER NOT NULL CHECK (cantidad > 0),
    PRIMARY KEY (id_producto, id_pedido)
);
CREATE INDEX ON app.contiene(id_pedido);