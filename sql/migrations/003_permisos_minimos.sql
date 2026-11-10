-- La aplicación solo necesita leer ventas y productos.
REVOKE ALL ON productos, ventas FROM agentflow_app;
GRANT SELECT ON productos, ventas TO agentflow_app;
