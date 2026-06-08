-- Crea el schema "contabilidad" y sus tablas dentro de la MISMA base de datos
-- que usa el backend principal de DocYa. No modifica ni toca ninguna tabla
-- existente del schema "public" (users, admins, liquidaciones_*, etc).
--
-- Como correrlo:
--   psql "$DATABASE_URL" -f migrations/001_init_contabilidad_schema.sql
-- (o pegar el contenido en tu cliente de Postgres preferido: psql, DBeaver, etc.)

CREATE SCHEMA IF NOT EXISTS contabilidad;

-- Catalogo de obligaciones fiscales / contables que hay que cumplir
-- (IVA, cargas sociales, Ingresos Brutos, Ganancias, balance anual, etc.)
CREATE TABLE IF NOT EXISTS contabilidad.obligaciones_fiscales (
    id                      SERIAL PRIMARY KEY,
    nombre                  TEXT NOT NULL UNIQUE,
    organismo               TEXT NOT NULL,
    periodicidad            TEXT NOT NULL CHECK (periodicidad IN ('mensual', 'anual')),
    dia_vencimiento         SMALLINT NOT NULL CHECK (dia_vencimiento BETWEEN 1 AND 31),
    mes_vencimiento         SMALLINT CHECK (mes_vencimiento BETWEEN 1 AND 12),
    -- Las obligaciones mensuales no pueden vencer el dia 29-31: no todos los
    -- meses los tienen (ej. febrero). Las anuales si, porque su mes es fijo.
    CONSTRAINT dia_valido_segun_periodicidad CHECK (periodicidad = 'anual' OR dia_vencimiento <= 28),
    notas                   TEXT,
    activa                  BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_periodo_cumplido TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Historial de presentaciones/pagos marcados como realizados, por periodo.
-- Sirve de auditoria: quien lo marco y cuando.
CREATE TABLE IF NOT EXISTS contabilidad.presentaciones (
    id              SERIAL PRIMARY KEY,
    obligacion_id   INTEGER NOT NULL REFERENCES contabilidad.obligaciones_fiscales(id) ON DELETE CASCADE,
    periodo         TEXT NOT NULL,
    marcado_por     TEXT,
    marcado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (obligacion_id, periodo)
);

CREATE INDEX IF NOT EXISTS idx_presentaciones_obligacion
    ON contabilidad.presentaciones (obligacion_id);

-- Carga inicial: obligaciones tipicas de una SAS Responsable Inscripta en IVA
-- con Ingresos Brutos en CABA. Los dias de vencimiento son ORIENTATIVOS:
-- ARCA y AGIP publican un cronograma que cambia cada año segun la terminacion
-- de CUIT. Ajustarlos desde la pantalla de Contabilidad una vez confirmados
-- con el contador.
INSERT INTO contabilidad.obligaciones_fiscales
    (nombre, organismo, periodicidad, dia_vencimiento, mes_vencimiento, notas, activa)
VALUES
    ('IVA - Posicion mensual (F. 2002)', 'ARCA (ex-AFIP)', 'mensual', 15, NULL,
     'Segun terminacion de CUIT (grupo 2-3-4). Ajustar con el cronograma general de vencimientos de ARCA del año en curso.', TRUE),
    ('Cargas sociales - SUSS (F. 931)', 'ARCA (ex-AFIP)', 'mensual', 10, NULL,
     'Segun terminacion de CUIT. Ajustar con el cronograma general de vencimientos de ARCA.', TRUE),
    ('Ingresos Brutos CABA', 'AGIP', 'mensual', 18, NULL,
     'Verificar el calendario de vencimientos de AGIP para el periodo.', TRUE),
    ('Anticipos de Ganancias - Sociedades', 'ARCA (ex-AFIP)', 'mensual', 15, NULL,
     'Se activan recien despues de presentar la primera DDJJ anual de Ganancias Sociedades.', FALSE),
    ('DDJJ anual Ganancias Sociedades + Balance', 'ARCA (ex-AFIP) / Contador', 'anual', 31, 5,
     'Vence aproximadamente 5 meses despues del cierre de ejercicio. Ajustar mes y dia segun la fecha real de cierre societario de DocYa SAS.', TRUE)
ON CONFLICT (nombre) DO NOTHING;
