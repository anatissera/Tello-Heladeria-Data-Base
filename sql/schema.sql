CREATE SCHEMA IF NOT EXISTS app;
SET search_path TO app, public;

DO $$
BEGIN
  IF to_regtype('app.pedido_estado') IS NULL THEN
    CREATE TYPE app.pedido_estado AS ENUM ('emitido','preparado','entregado','cancelado');
  END IF;
END $$;


-- TABLA DIRECCION

CREATE TABLE app.direccion (
  id_direccion INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  calle        TEXT NOT NULL,
  numero       INTEGER CHECK (numero > 0),
  piso         TEXT,              
  depto        TEXT,
  localidad    TEXT NOT NULL,
  cp           TEXT,
  UNIQUE (calle, numero, piso, depto, localidad, cp) -- para no duplicados ta ok?
);

-- TABLA SUCURSAL

CREATE TABLE app.sucursal (
  id_suc        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre        TEXT NOT NULL,
  id_direccion INTEGER REFERENCES app.direccion(id_direccion) 
                ON UPDATE CASCADE 
                ON DELETE RESTRICT
);

CREATE INDEX ON app.sucursal(id_direccion); -- para los joisn con id_Dire

-- TABLA USUARIO

CREATE TABLE app.usuario(
    dni                 TEXT PRIMARY KEY,
    nombre              TEXT NOT NULL,
    fecha_nacimiento    DATE,
    mail                TEXT UNIQUE,
    id_suc              INTEGER REFERENCES app.sucursal(id_suc) 
                        ON UPDATE CASCADE 
                        ON DELETE RESTRICT,
    activo              BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX ON app.usuario(id_suc);

-- SUBTIPOS DE USUARIOS

CREATE TABLE app.proveedor (
    dni     TEXT PRIMARY KEY REFERENCES app.usuario(dni) 
            ON UPDATE CASCADE 
            ON DELETE CASCADE
);

CREATE TABLE app.empleado(
    dni     TEXT PRIMARY KEY REFERENCES app.usuario(dni) 
            ON UPDATE CASCADE 
            ON DELETE CASCADE
    es_encargado    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE app.administrador(
    dni     TEXT PRIMARY KEY REFERENCES app.usuario(dni) 
            ON UPDATE CASCADE 
            ON DELETE CASCADE
);

-- CATEGORIA Y FAMILIA

-- nose si conviene ids by default si es que queremos usar los ids ya asignados o no 
CREATE TABLE app.categoria (
    id_categoria INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE app.familia (
    id_familia INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);


CREATE TABLE app.producto (
  id_producto  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre       TEXT NOT NULL,
  id_categoria INTEGER NOT NULL
                REFERENCES app.categoria(id_categoria)
                ON UPDATE CASCADE
                ON DELETE RESTRICT, 
  id_familia   INTEGER NOT NULL
                REFERENCES app.familia(id_familia)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
    CONSTRAINT uq_producto UNIQUE (nombre, id_categoria, id_familia)
);


CREATE INDEX ON app.producto(id_categoria);
CREATE INDEX ON app.producto(id_familia);


CREATE TABLE app.pedido (
  id_pedido     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  estado        app.pedido_estado NOT NULL DEFAULT 'emitido',
  fecha_emision TIMESTAMP NOT NULL DEFAULT now(),
  id_suc        INTEGER NOT NULL
                REFERENCES app.sucursal(id_suc)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,       
  dni_empleado  TEXT
                REFERENCES app.empleado(dni)
                ON UPDATE CASCADE
                ON DELETE SET NULL,       -- si se va un empleado, guardo el pedido ig
  dni_admin     TEXT
                REFERENCES app.administrador(dni)
                ON UPDATE CASCADE
                ON DELETE SET NULL
);


CREATE INDEX ON app.pedido(id_suc);
CREATE INDEX ON app.pedido(dni_empleado);


CREATE TABLE app.entrega (
  id_pedido       INTEGER PRIMARY KEY
                  REFERENCES app.pedido(id_pedido)
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,     
  dni_proveedor   TEXT NOT NULL
                  REFERENCES app.proveedor(dni)
                  ON UPDATE CASCADE
                  ON DELETE RESTRICT,     
  dni_empleado    TEXT
                  REFERENCES app.empleado(dni)
                  ON UPDATE CASCADE
                  ON DELETE SET NULL,     
  fecha_recepcion TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX ON app.entrega(dni_proveedor);


-- NOSE si hay que hacer una tabla de contiene ??