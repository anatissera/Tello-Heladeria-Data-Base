WITH params AS (
  SELECT
    ARRAY[/* ids a ENTREGADO */     2,3,4, 8,9, 12,13, 14,15,16]::int[] AS delivered_ids,
    ARRAY[/* ids a PREPARADO */     5,10, 11]::int[]                             AS prepared_ids,
    ARRAY[/* ids a EMITIDO  */      6, 7]::int[]                                AS emitted_ids,
    ARRAY[/* ids a CANCELADO*/      /* ej: 17 */]::int[]                     AS canceled_ids
),
prov AS (
  SELECT COALESCE((SELECT dni FROM app.proveedor LIMIT 1), '30-00000000-0') AS dni_prov
),

upd_delivered AS (
  UPDATE app.pedido p
  SET estado = 'entregado'::app.pedido_estado
  FROM params
  WHERE p.id_pedido = ANY(params.delivered_ids)
  RETURNING p.id_pedido, p.dni_empleado
),
ins_entrega AS (
  INSERT INTO app.entrega(id_pedido, dni_proveedor, dni_empleado)
  SELECT u.id_pedido, prov.dni_prov, u.dni_empleado
  FROM upd_delivered u CROSS JOIN prov
  ON CONFLICT (id_pedido) DO NOTHING
  RETURNING id_pedido
),

upd_prepared AS (
  UPDATE app.pedido p
  SET estado = 'preparado'::app.pedido_estado
  FROM params
  WHERE p.id_pedido = ANY(params.prepared_ids)
  RETURNING p.id_pedido
),

upd_emitted AS (
  UPDATE app.pedido p
  SET estado = 'emitido'::app.pedido_estado
  FROM params
  WHERE p.id_pedido = ANY(params.emitted_ids)
  RETURNING p.id_pedido
),

upd_canceled AS (
  UPDATE app.pedido p
  SET estado = 'cancelado'::app.pedido_estado
  FROM params
  WHERE p.id_pedido = ANY(params.canceled_ids)
  RETURNING p.id_pedido
)

SELECT
  (SELECT count(*) FROM upd_delivered) AS pedidos_marcados_entregado,
  (SELECT count(*) FROM ins_entrega)   AS entregas_creadas,
  (SELECT count(*) FROM upd_prepared)  AS pedidos_marcados_preparado,
  (SELECT count(*) FROM upd_emitted)   AS pedidos_marcados_emitido,
  (SELECT count(*) FROM upd_canceled)  AS pedidos_marcados_cancelado;
