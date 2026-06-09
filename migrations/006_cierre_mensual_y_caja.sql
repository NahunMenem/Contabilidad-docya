-- Cierre mensual administrativo y libro de caja manual.
--
-- Como correrlo:
--   psql "$DATABASE_URL" -f migrations/006_cierre_mensual_y_caja.sql

CREATE TABLE IF NOT EXISTS contabilidad.cierres_mensuales (
    periodo              TEXT PRIMARY KEY,
    consultas_cargadas   BOOLEAN NOT NULL DEFAULT FALSE,
    facturas_emitidas    BOOLEAN NOT NULL DEFAULT FALSE,
    gastos_cargados      BOOLEAN NOT NULL DEFAULT FALSE,
    medicos_liquidados   BOOLEAN NOT NULL DEFAULT FALSE,
    iva_revisado         BOOLEAN NOT NULL DEFAULT FALSE,
    agip_revisado        BOOLEAN NOT NULL DEFAULT FALSE,
    caja_conciliada      BOOLEAN NOT NULL DEFAULT FALSE,
    cerrado              BOOLEAN NOT NULL DEFAULT FALSE,
    notas                TEXT,
    cerrado_por          TEXT,
    cerrado_en           TIMESTAMPTZ,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contabilidad.movimientos_caja (
    id              SERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('ingreso', 'egreso')),
    categoria       TEXT NOT NULL,
    descripcion     TEXT NOT NULL,
    monto           NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    medio           TEXT,
    referencia      TEXT,
    notas           TEXT,
    creado_por      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_movimientos_caja_fecha
    ON contabilidad.movimientos_caja (fecha);
