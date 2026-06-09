-- Comprobantes emitidos y gastos/compras para preparar resumen mensual de IVA.
-- Mantiene la carga manual: no toma datos automaticamente del backend principal.
--
-- Como correrlo:
--   psql "$DATABASE_URL" -f migrations/004_comprobantes_gastos_resumen.sql

CREATE TABLE IF NOT EXISTS contabilidad.comprobantes_emitidos (
    id                         SERIAL PRIMARY KEY,
    fecha                      DATE NOT NULL,
    tipo_comprobante           TEXT NOT NULL DEFAULT 'Factura',
    letra                      TEXT NOT NULL DEFAULT 'B',
    punto_venta                INTEGER NOT NULL CHECK (punto_venta >= 1),
    numero                     INTEGER NOT NULL CHECK (numero >= 1),
    receptor_nombre            TEXT NOT NULL,
    receptor_documento         TEXT,
    condicion_iva_receptor     TEXT,
    concepto                   TEXT NOT NULL,
    importe_neto               NUMERIC(12,2) NOT NULL CHECK (importe_neto >= 0),
    iva_pct                    NUMERIC(6,3) NOT NULL DEFAULT 21 CHECK (iva_pct >= 0 AND iva_pct <= 100),
    iva_debito                 NUMERIC(12,2) NOT NULL CHECK (iva_debito >= 0),
    importe_total              NUMERIC(12,2) NOT NULL CHECK (importe_total >= 0),
    cae                        TEXT,
    cae_vencimiento            DATE,
    estado                     TEXT NOT NULL DEFAULT 'emitido' CHECK (estado IN ('borrador', 'emitido', 'anulado')),
    notas                      TEXT,
    creado_por                 TEXT,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_comprobante_emitido UNIQUE (tipo_comprobante, punto_venta, numero)
);

CREATE INDEX IF NOT EXISTS idx_comprobantes_emitidos_fecha
    ON contabilidad.comprobantes_emitidos (fecha);

CREATE TABLE IF NOT EXISTS contabilidad.gastos_compras (
    id                     SERIAL PRIMARY KEY,
    fecha                  DATE NOT NULL,
    proveedor_nombre       TEXT NOT NULL,
    proveedor_cuit         TEXT,
    tipo_comprobante       TEXT NOT NULL DEFAULT 'Factura',
    letra                  TEXT,
    punto_venta            INTEGER CHECK (punto_venta IS NULL OR punto_venta >= 1),
    numero                 INTEGER CHECK (numero IS NULL OR numero >= 1),
    concepto               TEXT NOT NULL,
    categoria              TEXT,
    importe_neto           NUMERIC(12,2) NOT NULL CHECK (importe_neto >= 0),
    iva_pct                NUMERIC(6,3) NOT NULL DEFAULT 21 CHECK (iva_pct >= 0 AND iva_pct <= 100),
    iva_credito            NUMERIC(12,2) NOT NULL CHECK (iva_credito >= 0),
    percepciones           NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (percepciones >= 0),
    importe_total          NUMERIC(12,2) NOT NULL CHECK (importe_total >= 0),
    deducible_iva          BOOLEAN NOT NULL DEFAULT TRUE,
    notas                  TEXT,
    creado_por             TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gastos_compras_fecha
    ON contabilidad.gastos_compras (fecha);
