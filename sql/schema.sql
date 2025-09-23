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
    id_producto  INTEGER PRIMARY KEY,  -- lo cargás vos desde el CSV
    nombre       TEXT NOT NULL,
    id_categoria INTEGER NOT NULL
                REFERENCES app.categoria(id_categoria)
                ON UPDATE CASCADE
                ON DELETE RESTRICT, 
    id_familia   INTEGER 
                REFERENCES app.familia(id_familia)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
    CONSTRAINT uq_producto UNIQUE (nombre, id_categoria, id_familia)
);

CREATE INDEX ON app.producto(id_categoria);
CREATE INDEX ON app.producto(id_familia);

CREATE TABLE app.pedido (
  ID_pedido     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  estado        app.pedido_estado NOT NULL DEFAULT 'emitido',
  fecha_emision TIMESTAMP NOT NULL DEFAULT now(),
  ID_suc        INTEGER NOT NULL
                REFERENCES app.sucursal(ID_suc)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,       
  DNI_empleado  TEXT NOT NULL
                REFERENCES app.empleado(DNI)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,       -- no puedo borrar empleado si tiene pedidos, lo desactivo no más, para eso el campo activo
  DNI_admin     TEXT NOT NULL
                REFERENCES app.administrador(DNI)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
);

CREATE INDEX ON app.pedido(ID_suc);
CREATE INDEX ON app.pedido(DNI_empleado);
CREATE INDEX ON app.pedido(DNI_admin);



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
                  ON DELETE RESTRICT,     
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

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM app.proveedor) THEN
    -- Usa cualquier sucursal disponible para el usuario del proveedor default
    INSERT INTO app.usuario(dni, nombre, id_suc, activo)
    SELECT '30-00000000-0', 'Proveedor Default', id_suc, TRUE
    FROM app.sucursal
    LIMIT 1
    ON CONFLICT (dni) DO NOTHING;

    INSERT INTO app.proveedor(dni) VALUES ('30-00000000-0')
    ON CONFLICT DO NOTHING;
  END IF;
END$$;


CREATE OR REPLACE FUNCTION app.chk_pedido_entregado()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  v_prov TEXT;
BEGIN
  IF NEW.estado = 'entregado' THEN
    -- si no existe entrega, crearla
    IF NOT EXISTS (SELECT 1 FROM app.entrega e WHERE e.id_pedido = NEW.id_pedido) THEN
      SELECT COALESCE((SELECT dni FROM app.proveedor LIMIT 1), '30-00000000-0')
        INTO v_prov;

      INSERT INTO app.entrega(id_pedido, dni_proveedor, dni_empleado)
      VALUES (NEW.id_pedido, v_prov, NEW.dni_empleado)
      ON CONFLICT DO NOTHING;
    END IF;
  END IF;
  RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS trg_chk_pedido_entregado ON app.pedido;
CREATE TRIGGER trg_chk_pedido_entregado
BEFORE INSERT OR UPDATE OF estado ON app.pedido
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



-- validación

-- asegura: dni_empleado ⇒ existe en app.empleado, activo = TRUE, es_encargado = TRUE y misma sucursal (u.id_suc = NEW.id_suc).
--          dni_admin ⇒ existe en app.administrador, activo = TRUE y misma sucursal.

CREATE OR REPLACE FUNCTION app.pedido_validate_roles()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  v_emp_ok  boolean;
  v_adm_ok  boolean;
BEGIN
  -- Permitir NULLs si tu modelo lo permite (ajusta si querés que sean obligatorios)
  IF NEW.dni_empleado IS NOT NULL THEN
    SELECT EXISTS (
      SELECT 1
      FROM app.usuario u
      JOIN app.empleado e ON e.dni = u.dni
      WHERE u.dni = NEW.dni_empleado
        AND u.activo = TRUE
        AND u.id_suc = NEW.id_suc
        AND e.es_encargado = TRUE
    ) INTO v_emp_ok;

    IF NOT v_emp_ok THEN
      RAISE EXCEPTION 'Empleado % no es encargado activo de la sucursal %',
        NEW.dni_empleado, NEW.id_suc
      USING ERRCODE = '23514'; -- check_violation
    END IF;
  END IF;

  IF NEW.dni_admin IS NOT NULL THEN
    SELECT EXISTS (
      SELECT 1
      FROM app.usuario u
      JOIN app.administrador a ON a.dni = u.dni
      WHERE u.dni = NEW.dni_admin
        AND u.activo = TRUE
        AND u.id_suc = NEW.id_suc
    ) INTO v_adm_ok;

    IF NOT v_adm_ok THEN
      RAISE EXCEPTION 'Administrador % no es activo de la sucursal %',
        NEW.dni_admin, NEW.id_suc
      USING ERRCODE = '23514';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

-- Trigger en pedido
DROP TRIGGER IF EXISTS trg_pedido_validate_roles_ins ON app.pedido;
DROP TRIGGER IF EXISTS trg_pedido_validate_roles_upd ON app.pedido;

CREATE TRIGGER trg_pedido_validate_roles_ins
BEFORE INSERT ON app.pedido
FOR EACH ROW
EXECUTE FUNCTION app.pedido_validate_roles();

CREATE TRIGGER trg_pedido_validate_roles_upd
BEFORE UPDATE OF id_suc, dni_empleado, dni_admin ON app.pedido
FOR EACH ROW
EXECUTE FUNCTION app.pedido_validate_roles();
