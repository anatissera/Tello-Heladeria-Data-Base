
heladeria/
├── sql/
│   ├── schema.sql                     # DDL con Producto/Variedad, ítems con unidad, entregas parciales
│   ├── seed.sql                       # Datos
│   └── reports.sql                    # Consulta parametrizada (sucursal + rango de fechas)
│                                        acá podríamos hacer:
│                                        un report_top_variedades.sql 
│                                        (Consulta parametrizada (sucursal + rango de fechas)
│                                        para ver comportamiento de clientes de una sucursal en un tiempo dado)
│                                        un query_producto_mas_pedido.sql
│                                        (KPI global. No tendría parámetros, agrupa por producto (Helado, Paleta, 
│                                        Torta). Sirve para dashboards o reportes de negocio generales)│   
│
└── scripts/
    └── run_sqlite.py                  # Crea DB, carga seeds y ejecuta las consultas demo