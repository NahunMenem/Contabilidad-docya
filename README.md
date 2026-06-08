# DocYa Contabilidad API

Servicio independiente para llevar la contabilidad de DocYa SAS (calendario de
vencimientos como primer modulo, con espacio para sumar libro IVA, comprobantes
y balance anual mas adelante).

Vive como **servicio separado** del backend principal de DocYa para no afectar
ese sistema en producción: comparte la misma base de datos Postgres, pero todas
sus tablas viven en un schema propio (`contabilidad`), aislado de `public`.

## 1. Crear las tablas

Corré la migración una sola vez contra la base de datos compartida (no toca
ninguna tabla existente):

```bash
psql "$DATABASE_URL" -f migrations/001_init_contabilidad_schema.sql
```

## 2. Variables de entorno

Copiá `.env.example` a `.env` (local) o cargalas como variables de entorno en
Railway:

- `DATABASE_URL`: la misma cadena de conexión que usa el backend principal.
- `JWT_SECRET` / `JWT_ALGORITHM`: el **mismo secreto** que firma el `docya_token`
  en el backend principal (cópialo desde sus variables de entorno — así esta API
  valida las mismas sesiones sin duplicar el login).
- `CORS_ORIGINS`: dominios del panel que va a consumir esta API.

## 3. Correr en local

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Documentación interactiva en `http://localhost:8001/docs`.

## 4. Deploy en Railway

1. Subí esta carpeta a un repo de GitHub propio.
2. Creá un nuevo servicio en Railway apuntando a ese repo (Railway detecta el
   `Procfile` y el `requirements.txt` automáticamente).
3. Cargá las variables de entorno del paso 2.
4. (Opcional pero recomendado) Generá un `JWT_SECRET` nuevo y más fuerte para
   **todo** el sistema con `openssl rand -hex 32`, y actualizalo tanto acá como
   en el backend principal.

## Endpoints

Todos requieren `Authorization: Bearer <docya_token>` (el mismo token que ya
usa el panel de administración).

- `GET    /contabilidad/obligaciones` — listar obligaciones fiscales
- `POST   /contabilidad/obligaciones` — crear una obligación
- `PUT    /contabilidad/obligaciones/{id}` — editar
- `DELETE /contabilidad/obligaciones/{id}` — eliminar
- `POST   /contabilidad/obligaciones/{id}/marcar-presentada` — marcar un período como cumplido (`{"periodo": "2026-06"}` o `{"periodo": "2026"}`)
- `GET    /health` — chequeo de salud
