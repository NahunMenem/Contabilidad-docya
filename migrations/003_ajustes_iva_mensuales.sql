-- Ajuste manual de IVA credito por periodo (otros creditos: honorarios del
-- contador, servicios locales con IVA discriminado, etc. que no salen del
-- libro de consultas pero igual se pueden descontar del IVA neto a declarar).
--
-- Como correrlo:
--   psql "$DATABASE_URL" -f migrations/003_ajustes_iva_mensuales.sql

CREATE TABLE IF NOT EXISTS contabilidad.ajustes_iva_mensuales (
    periodo         TEXT PRIMARY KEY,  -- formato 'YYYY-MM'
    otros_creditos  NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (otros_creditos >= 0),
    notas           TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
