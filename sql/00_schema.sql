-- =============================================================================
-- Esquema base de dominio — amenazas, indicadores, sub_indicadores, clases,
-- inmuebles
-- =============================================================================
--
-- Hallazgo de la validación de portabilidad (2026-09-08): estas 5 tablas tienen
-- `managed = False` en api/models.py (Django las consulta, no las administra),
-- y hasta ahora no existía ningún CREATE TABLE versionado para ellas en el
-- repositorio — `02_amenaza_sismo.sql` y este mismo tipo de script siempre
-- asumieron que ya existían. Sin este archivo, un `manage.py migrate` sobre una
-- base nueva falla en `0001_Evaluacion` con `relation "inmuebles" does not
-- exist`, porque esa migración crea `evaluacion` con una FK hacia `inmuebles`.
--
-- Debe aplicarse ANTES que 01_amenaza_incendio.sql / 02_amenaza_sismo.sql y
-- antes de `manage.py migrate`. Idempotente vía `IF NOT EXISTS`.
-- =============================================================================

CREATE TABLE IF NOT EXISTS inmuebles (
    id                  SERIAL PRIMARY KEY,
    manzana             VARCHAR(50),
    predio              VARCHAR(255),
    rol_sii             VARCHAR(25) UNIQUE NOT NULL,
    direccion           VARCHAR(255),
    geom                GEOMETRY(MultiPolygon, 4326),
    region              VARCHAR(100),
    fecha_creacion      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS amenazas (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(100) UNIQUE NOT NULL,
    descripcion     TEXT,
    fecha_creacion  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS indicadores (
    id              SERIAL PRIMARY KEY,
    amenaza_id      INTEGER NOT NULL,
    nombre          VARCHAR(100) NOT NULL,
    descripcion     TEXT,
    peso            DECIMAL(2,2) NOT NULL CHECK (peso >= 0 AND peso <= 1),
    activo          BOOLEAN DEFAULT TRUE,
    fecha_creacion  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (amenaza_id, nombre),
    FOREIGN KEY (amenaza_id) REFERENCES amenazas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sub_indicadores (
    id              SERIAL PRIMARY KEY,
    indicador_id    INTEGER NOT NULL,
    nombre          VARCHAR(100) NOT NULL,
    descripcion     TEXT,
    peso            DECIMAL(5,4) NOT NULL CHECK (peso >= 0 AND peso <= 1),
    activo          BOOLEAN DEFAULT TRUE,
    fecha_creacion  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (indicador_id, nombre),
    FOREIGN KEY (indicador_id) REFERENCES indicadores(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clases (
    id                SERIAL PRIMARY KEY,
    sub_indicador_id  INTEGER NOT NULL,
    nombre            VARCHAR(100) NOT NULL,
    valor             INTEGER NOT NULL CHECK (valor >= 0),
    descripcion       TEXT,
    activo            BOOLEAN DEFAULT TRUE,
    fecha_creacion    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (sub_indicador_id, nombre),
    FOREIGN KEY (sub_indicador_id) REFERENCES sub_indicadores(id) ON DELETE CASCADE
);

-- Nota: `evaluacion` NO va en este archivo — la crea Django
-- (api/migrations/0001_Evaluacion.py en adelante). Su comportamiento real de
-- ON DELETE (CASCADE en id_inmueble, RESTRICT en id_subindicador) se corrige
-- en api/migrations/0005_fix_evaluacion_on_delete.py, no acá.
