-- Libro de consultas: registro manual de consultas facturadas por DocYa,
-- con calculo automatico de comision DocYa, comision de Mercado Pago e IVA
-- (debito sobre la comision DocYa, credito sobre la comision de MP).
--
-- Como correrlo:
--   psql "$DATABASE_URL" -f migrations/002_libro_consultas.sql

-- Parametros de calculo (porcentajes) editables desde la pantalla. Una sola
-- fila: se actualiza con UPDATE, no se crean filas nuevas.
CREATE TABLE IF NOT EXISTS contabilidad.parametros_facturacion (
    id                  SMALLINT PRIMARY KEY DEFAULT 1,
    comision_docya_pct  NUMERIC(6,3) NOT NULL DEFAULT 20,
    comision_mp_pct     NUMERIC(6,3) NOT NULL DEFAULT 6,
    iva_pct             NUMERIC(6,3) NOT NULL DEFAULT 21,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT parametros_facturacion_singleton CHECK (id = 1)
);

INSERT INTO contabilidad.parametros_facturacion (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- Cada fila es una consulta cargada manualmente para llevar el libro de IVA.
-- El precio es el valor total que paga el paciente; la comision DocYa (lo que
-- factura la SAS) y la comision de MP se derivan de ese monto con los
-- porcentajes vigentes al momento de la carga (quedan congelados en la fila
-- para que cambios futuros de alicuota no alteren registros historicos).
CREATE TABLE IF NOT EXISTS contabilidad.registros_consultas (
    id                  SERIAL PRIMARY KEY,
    fecha               DATE NOT NULL,
    medico              TEXT NOT NULL,
    tipo                TEXT NOT NULL,
    precio              NUMERIC(12,2) NOT NULL CHECK (precio >= 0),
    comision_docya_pct  NUMERIC(6,3) NOT NULL,
    comision_mp_pct     NUMERIC(6,3) NOT NULL,
    iva_pct             NUMERIC(6,3) NOT NULL,
    creado_por          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_registros_consultas_fecha
    ON contabilidad.registros_consultas (fecha);
