DROP SCHEMA IF EXISTS app CASCADE;
CREATE SCHEMA app;
SET search_path TO app, public;

DO $$
BEGIN
  IF to_regtype('app.pedido_estado') IS NULL THEN
    CREATE TYPE app.pedido_estado AS ENUM ('emitido', 'aprobado', 'preparado', 'entregado', 'cancelado');
  END IF;
END $$;

-- SUCURSAL

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

-- USUARIO

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

CREATE TABLE app.categoria (
    ID_categoria INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE app.familia (
    ID_familia INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

-- PRODUCTO

CREATE TABLE app.producto (
    id_producto  INTEGER PRIMARY KEY, 
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

-- PEDIDO

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
                ON DELETE RESTRICT,      -- no puedo borrar empleado si tiene pedidos, lo desactivo no más, para eso el campo activo 
  DNI_admin     TEXT 
                REFERENCES app.administrador(DNI)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
);

CREATE INDEX ON app.pedido(ID_suc);
CREATE INDEX ON app.pedido(DNI_empleado);
CREATE INDEX ON app.pedido(DNI_admin);

-- ENTREGA

CREATE TABLE app.entrega (
  ID_pedido       INTEGER PRIMARY KEY
                  REFERENCES app.pedido(ID_pedido)
                  ON UPDATE CASCADE
                  ON DELETE CASCADE,     
  DNI_proveedor   TEXT NOT NULL
                  REFERENCES app.proveedor(DNI)
                  ON UPDATE CASCADE
                  ON DELETE RESTRICT,     
  DNI_empleado    TEXT NOT NULL
                  REFERENCES app.empleado(DNI)
                  ON UPDATE CASCADE
                  ON DELETE RESTRICT,     
  fecha_recepcion TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX ON app.entrega(DNI_proveedor);


-- Relación CONTIENE

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

CREATE OR REPLACE FUNCTION app.chk_pedido_entregado()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  v_prov TEXT;
  v_dni_empleado_receptor TEXT; 
BEGIN
  IF NEW.estado = 'entregado' THEN
    IF NOT EXISTS (SELECT 1 FROM app.entrega e WHERE e.id_pedido = NEW.id_pedido) THEN
      
      SELECT COALESCE((SELECT dni FROM app.proveedor LIMIT 1), '30-00000000-0') INTO v_prov;

      SELECT u.dni INTO v_dni_empleado_receptor
      FROM app.usuario u
      JOIN app.empleado e ON e.dni = u.dni
      WHERE u.id_suc = NEW.id_suc
        AND u.activo = TRUE
      LIMIT 1;

      IF v_dni_empleado_receptor IS NULL THEN
          RAISE EXCEPTION 'No se puede marcar como entregado: No existe un empleado activo en la sucursal de destino (%) para registrar la recepción.', NEW.id_suc;
      END IF;

      INSERT INTO app.entrega(id_pedido, dni_proveedor, dni_empleado)
      VALUES (NEW.id_pedido, v_prov, v_dni_empleado_receptor) 
      ON CONFLICT DO NOTHING;
    END IF;
  END IF;
  RETURN NEW;
END;
$$;


CREATE TRIGGER trg_chk_pedido_entregado
AFTER INSERT OR UPDATE OF estado ON app.pedido
FOR EACH ROW
EXECUTE FUNCTION app.chk_pedido_entregado();


CREATE OR REPLACE FUNCTION app.chk_entrega_permitida()
RETURNS TRIGGER AS $$
DECLARE v_estado app.pedido_estado;
BEGIN
  SELECT estado INTO v_estado
  FROM app.pedido
  WHERE ID_pedido = NEW.ID_pedido
  FOR UPDATE;

  IF v_estado IS NULL THEN
    RAISE EXCEPTION 'Pedido % inexistente', NEW.ID_pedido;
  END IF;

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

CREATE OR REPLACE FUNCTION app.auto_marcar_pedido_entregado()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE app.pedido
     SET estado = 'entregado'
   WHERE ID_pedido = NEW.ID_pedido
     AND estado <> 'entregado';
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_pedido_entregado
AFTER INSERT OR UPDATE ON app.entrega
FOR EACH ROW
EXECUTE FUNCTION app.auto_marcar_pedido_entregado();


CREATE OR REPLACE FUNCTION app.chk_empleado_sucursal_entrega()
RETURNS TRIGGER AS $$
DECLARE
  v_id_suc_pedido INTEGER;
  v_id_suc_empleado INTEGER;
BEGIN
  SELECT ID_suc INTO v_id_suc_pedido
  FROM app.pedido
  WHERE ID_pedido = NEW.ID_pedido;


  IF NEW.DNI_empleado IS NOT NULL THEN
    SELECT u.ID_suc INTO v_id_suc_empleado
    FROM app.usuario u
    JOIN app.empleado e ON e.DNI = u.DNI
    WHERE u.DNI = NEW.DNI_empleado
      AND u.activo = TRUE;

    IF v_id_suc_empleado IS NULL THEN
        RAISE EXCEPTION 'El empleado receptor (DNI: %) no está registrado como empleado activo.', NEW.DNI_empleado;
    END IF;

    IF v_id_suc_empleado IS DISTINCT FROM v_id_suc_pedido THEN
      RAISE EXCEPTION 
        'El empleado receptor (DNI: %) pertenece a la sucursal %, pero el pedido requiere un empleado de la sucursal % (destino).',
        NEW.DNI_empleado, v_id_suc_empleado, v_id_suc_pedido;
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_chk_empleado_sucursal_entrega
BEFORE INSERT OR UPDATE OF DNI_empleado, ID_pedido ON app.entrega
FOR EACH ROW
EXECUTE FUNCTION app.chk_empleado_sucursal_entrega();

CREATE OR REPLACE FUNCTION app.chk_pedido_flujo_estado()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN

  IF OLD.estado = 'emitido' THEN
  
    IF NEW.dni_admin IS NOT NULL AND OLD.dni_admin IS NULL AND NEW.estado = 'emitido' THEN
        NEW.estado := 'aprobado';
        
    ELSIF NEW.estado = 'cancelado' THEN
        IF NEW.dni_admin IS NULL OR OLD.dni_admin IS NOT NULL THEN
             RAISE EXCEPTION 'La cancelación de un pedido EMITIDO debe ser realizada y trazada por el Administrador.';
        END IF;
        
    END IF;
  
  END IF;

  IF NEW.estado = 'cancelado' AND OLD.estado IN ('aprobado', 'preparado', 'entregado') THEN
      RAISE EXCEPTION 'Un pedido no puede ser cancelado después de haber sido aprobado. Solo puede ser cancelado en estado EMITIDO.';
  END IF;
  
  IF NEW.estado IN ('preparado', 'entregado') AND OLD.estado <> 'aprobado' THEN
      RAISE EXCEPTION 'El pedido % debe estar en estado APROBADO para pasar a %.', NEW.id_pedido, NEW.estado;
  END IF;

  IF OLD.estado = 'cancelado' AND NEW.estado <> 'cancelado' THEN
    RAISE EXCEPTION 'El pedido ya está CANCELADO y su estado no puede ser modificado.';
  END IF;

  IF NEW.estado = 'emitido' AND OLD.estado <> 'emitido' THEN
      RAISE EXCEPTION 'El pedido % no puede volver al estado EMITIDO.', NEW.id_pedido;
  END IF;

  IF OLD.estado = 'entregado' AND NEW.estado IS DISTINCT FROM 'entregado' THEN
    RAISE EXCEPTION 'El pedido % ya está ENTREGADO y su estado no puede modificarse.', NEW.id_pedido;
  END IF;
  
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_chk_pedido_flujo_estado
BEFORE UPDATE OF estado, dni_admin ON app.pedido
FOR EACH ROW
WHEN (OLD.estado IS DISTINCT FROM NEW.estado OR OLD.dni_admin IS DISTINCT FROM NEW.dni_admin)
EXECUTE FUNCTION app.chk_pedido_flujo_estado();


-- validación

-- asegura: dni_empleado ⇒ existe en app.empleado, activo = TRUE, es_encargado = TRUE y misma sucursal (u.id_suc = NEW.id_suc).
--          dni_admin ⇒ existe en app.administrador, activo = TRUE y misma sucursal.


CREATE OR REPLACE FUNCTION app.pedido_validate_roles()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  v_emp_ok  boolean;
  v_adm_ok  boolean;
BEGIN
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
      RAISE EXCEPTION 'Empleado % no es encargado activo %',
        NEW.dni_empleado, NEW.id_suc
      USING ERRCODE = '23514';
    END IF;
  END IF;

  IF NEW.dni_admin IS NOT NULL THEN
    SELECT EXISTS (
      SELECT 1
      FROM app.usuario u
      JOIN app.administrador a ON a.dni = u.dni
      WHERE u.dni = NEW.dni_admin
        AND u.activo = TRUE
    ) INTO v_adm_ok;

    IF NOT v_adm_ok THEN
      RAISE EXCEPTION 'Administrador % no está activo %',
        NEW.dni_admin, NEW.id_suc
      USING ERRCODE = '23514';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;


CREATE TRIGGER trg_pedido_validate_roles_ins
BEFORE INSERT ON app.pedido
FOR EACH ROW
EXECUTE FUNCTION app.pedido_validate_roles();

CREATE TRIGGER trg_pedido_validate_roles_upd
BEFORE UPDATE OF id_suc, dni_empleado, dni_admin ON app.pedido
FOR EACH ROW
EXECUTE FUNCTION app.pedido_validate_roles();


CREATE OR REPLACE FUNCTION app.chk_admin_central()
RETURNS TRIGGER AS $$
DECLARE
  v_suc_admin INTEGER;
  v_cc INTEGER;
BEGIN
  SELECT id_suc INTO v_suc_admin
  FROM app.usuario
  WHERE dni = NEW.dni; 
  SELECT id_suc INTO v_cc
  FROM app.sucursal
  WHERE nombre = 'Casa Central'
  LIMIT 1;

  IF v_cc IS NULL THEN
    RAISE EXCEPTION 'No se encontró la sucursal Casa Central';
  END IF;

  IF v_suc_admin IS DISTINCT FROM v_cc THEN
    RAISE EXCEPTION
      'Un administrador solo puede pertenecer a Casa Central (id_suc = %). El usuario tiene ID_suc %.', v_cc, v_suc_admin;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_chk_admin_central
BEFORE INSERT ON app.administrador
FOR EACH ROW
EXECUTE FUNCTION app.chk_admin_central();

CREATE OR REPLACE FUNCTION app.chk_proveedor_central()
RETURNS TRIGGER AS $$
DECLARE
  v_suc_prov INTEGER;
  v_cc INTEGER;
BEGIN
  SELECT id_suc INTO v_suc_prov
  FROM app.usuario
  WHERE dni = NEW.dni; 

  SELECT id_suc INTO v_cc
  FROM app.sucursal
  WHERE nombre = 'Casa Central'
  LIMIT 1;

  IF v_cc IS NULL THEN
    RAISE EXCEPTION 'No se encontró la sucursal Casa Central';
  END IF;

  IF v_suc_prov IS DISTINCT FROM v_cc THEN
    RAISE EXCEPTION
      'Un proveedor solo puede pertenecer a Casa Central (id_suc = %). El usuario tiene ID_suc %.', v_cc, v_suc_prov;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_chk_proveedor_central
BEFORE INSERT ON app.proveedor
FOR EACH ROW
EXECUTE FUNCTION app.chk_proveedor_central();

CREATE OR REPLACE FUNCTION app.chk_roles_casa_central_usuario()
RETURNS TRIGGER AS $$
DECLARE
  v_cc INTEGER;
  v_es_central_role BOOLEAN;
  v_rol_nombre TEXT;
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.id_suc IS NOT DISTINCT FROM OLD.id_suc THEN
    RETURN NEW;
  END IF;
  
  SELECT EXISTS (SELECT 1 FROM app.administrador WHERE DNI = NEW.DNI) OR
         EXISTS (SELECT 1 FROM app.proveedor WHERE DNI = NEW.DNI)
    INTO v_es_central_role;

  IF NOT v_es_central_role THEN
    RETURN NEW;
  END IF;

  SELECT id_suc INTO v_cc
  FROM app.sucursal
  WHERE nombre = 'Casa Central'
  LIMIT 1;

  IF v_cc IS NULL THEN
    RAISE EXCEPTION 'No se encontró la sucursal Casa Central';
  END IF;
  
  IF EXISTS (SELECT 1 FROM app.administrador WHERE DNI = NEW.DNI) THEN
      v_rol_nombre := 'administrador';
  ELSE
      v_rol_nombre := 'proveedor';
  END IF;

  IF NEW.id_suc IS DISTINCT FROM v_cc THEN
    RAISE EXCEPTION
      'No se puede cambiar la sucursal del % % a ID_suc %. Este rol solo puede pertenecer a Casa Central (ID_suc = %).',
      v_rol_nombre, NEW.DNI, NEW.id_suc, v_cc;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_chk_roles_casa_central_usuario
BEFORE INSERT OR UPDATE OF ID_suc ON app.usuario
FOR EACH ROW
EXECUTE FUNCTION app.chk_roles_casa_central_usuario();