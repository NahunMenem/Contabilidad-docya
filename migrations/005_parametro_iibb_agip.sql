-- Parametro configurable para estimar Ingresos Brutos AGIP/CABA.
-- Default orientativo: 3%. Confirmar alicuota real con contador segun actividad/NAES.
--
-- Como correrlo:
--   psql "$DATABASE_URL" -f migrations/005_parametro_iibb_agip.sql

ALTER TABLE contabilidad.parametros_facturacion
ADD COLUMN IF NOT EXISTS iibb_agip_pct NUMERIC(6,3) NOT NULL DEFAULT 3;
