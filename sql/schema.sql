CREATE SCHEMA IF NOT EXISTS app;
SET search_path TO app, public;

DO $$
BEGIN
  IF to_regtype('app.pedido_estado') IS NULL THEN
    CREATE TYPE app.pedido_estado AS ENUM ('emitido','preparado','entregado','cancelado');
  END IF;
END $$;

-- TABLA SUCURSAL

CREATE TABLE app.sucursal (
  id_suc     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre     TEXT NOT NULL,
  calle      TEXT NOT NULL,
  numero     INTEGER CHECK (numero > 0),
  piso       TEXT,
  depto      TEXT,
  localidad  TEXT NOT NULL,
  cp         TEXT NOT NULL
);

CREATE INDEX ON app.sucursal(localidad);
-- Para evitar sucursales con mismo nombre y misma dirección:
CREATE UNIQUE INDEX uq_sucursal_nombre_dir
  ON app.sucursal (nombre, calle, numero, COALESCE(piso,''), COALESCE(depto,''), localidad, cp);

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

CREATE INDEX ON app.pedido(ID_suc);
CREATE INDEX ON app.pedido(DNI_empleado);
CREATE INDEX ON app.pedido(DNI_admin);

-- Integridad
ALTER TABLE app.pedido
  ADD CONSTRAINT ck_pedido_admin_segun_estado
  CHECK (estado = 'emitido' OR DNI_admin IS NOT NULL);
-- no se puede pasar un pedido de "emitido" a otro estado sin haberle asignado un administrador


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
    ID_producto INTEGER NOT NULL
                REFERENCES app.producto(ID_producto)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
    ID_pedido   INTEGER NOT NULL
                REFERENCES app.pedido(ID_pedido)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
    cantidad    INTEGER NOT NULL CHECK (cantidad > 0),
    PRIMARY KEY (ID_producto, ID_pedido)
);
CREATE INDEX ON app.contiene(ID_pedido);



-- Manejo de Inconsistencias

-- si un pedido cambia a estado "entregado" tiene que existir una fila asociada en entrega
CREATE OR REPLACE FUNCTION app.chk_pedido_entregado()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.estado = 'entregado' THEN
    IF NOT EXISTS (
      SELECT 1 FROM app.entrega e
      WHERE e.ID_pedido = NEW.ID_pedido
    ) THEN
      RAISE EXCEPTION 
        'No se puede marcar como entregado el pedido %: falta la fila en entrega',
        NEW.id_pedido;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- asociamos la función a la tabla pedido, para que corra antes de UPDATE o INSERT
CREATE TRIGGER trg_chk_pedido_entregado
BEFORE INSERT OR UPDATE ON app.pedido
FOR EACH ROW
EXECUTE FUNCTION app.chk_pedido_entregado();



-- no permitir entrega si el pedido está cancelado o no existe
CREATE OR REPLACE FUNCTION app.chk_entrega_permitida()
RETURNS TRIGGER AS $$
DECLARE v_estado app.pedido_estado;
BEGIN
  SELECT estado INTO v_estado
  FROM app.pedido
  WHERE ID_pedido = NEW.ID_pedido
  FOR UPDATE;

  -- si no existe pedido -> error
  IF v_estado IS NULL THEN
    RAISE EXCEPTION 'Pedido % inexistente', NEW.ID_pedido;
  END IF;

  -- si el pedido está cancelado -> error
  IF v_estado = 'cancelado' THEN
    RAISE EXCEPTION 'No se puede registrar entrega para pedido CANCELADO (%)',
      NEW.ID_pedido;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_chk_entrega_permitida
BEFORE INSERT OR UPDATE ON app.entrega
FOR EACH ROW
EXECUTE FUNCTION app.chk_entrega_permitida();



-- marca automáticamente el pedido como "entregado" cuando se inserta o actualiza la entrega
CREATE OR REPLACE FUNCTION app.auto_marcar_pedido_entregado()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE app.pedido
     SET estado = 'entregado'
   WHERE ID_pedido = NEW.ID_pedido
     AND estado <> 'entregado'; -- solo si no está ya entregado
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_pedido_entregado
AFTER INSERT OR UPDATE ON app.entrega
FOR EACH ROW
EXECUTE FUNCTION app.auto_marcar_pedido_entregado();

