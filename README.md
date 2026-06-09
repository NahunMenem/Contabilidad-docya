# DocYa Contabilidad API

Servicio independiente para llevar la contabilidad operativa de DocYa SAS:
calendario de vencimientos, libro manual de consultas, comprobantes emitidos,
gastos/compras, ajustes de IVA y resumen mensual para revisar con el contador
antes de cargar ARCA.

Vive como **servicio separado** del backend principal de DocYa para no afectar
ese sistema en producción: comparte la misma base de datos Postgres, pero todas
sus tablas viven en un schema propio (`contabilidad`), aislado de `public`.

## 1. Crear las tablas

Corré la migración una sola vez contra la base de datos compartida (no toca
ninguna tabla existente):

```bash
psql "$DATABASE_URL" -f migrations/001_init_contabilidad_schema.sql
psql "$DATABASE_URL" -f migrations/002_libro_consultas.sql
psql "$DATABASE_URL" -f migrations/003_ajustes_iva_mensuales.sql
psql "$DATABASE_URL" -f migrations/004_comprobantes_gastos_resumen.sql
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
- `GET    /contabilidad/parametros-facturacion` — ver porcentajes de comisión DocYa, comisión MP e IVA
- `PUT    /contabilidad/parametros-facturacion` — actualizar esos porcentajes (se aplican a las consultas nuevas)
- `GET    /contabilidad/registros-consultas?desde=&hasta=` — listar consultas del libro (filtro opcional por fecha)
- `POST   /contabilidad/registros-consultas` — registrar una consulta facturada
- `DELETE /contabilidad/registros-consultas/{id}` — eliminar un registro
- `GET    /contabilidad/comprobantes-emitidos?desde=&hasta=` — listar comprobantes emitidos manuales
- `POST   /contabilidad/comprobantes-emitidos` — cargar factura/NC/ND emitida con CAE opcional
- `PUT    /contabilidad/comprobantes-emitidos/{id}` — editar comprobante
- `DELETE /contabilidad/comprobantes-emitidos/{id}` — eliminar comprobante
- `GET    /contabilidad/gastos-compras?desde=&hasta=` — listar compras/gastos con IVA credito
- `POST   /contabilidad/gastos-compras` — cargar gasto/proveedor
- `PUT    /contabilidad/gastos-compras/{id}` — editar gasto/proveedor
- `DELETE /contabilidad/gastos-compras/{id}` — eliminar gasto/proveedor
- `GET    /contabilidad/ajustes-iva/{periodo}` — ver el ajuste manual de IVA crédito de un período (`YYYY-MM`)
- `PUT    /contabilidad/ajustes-iva/{periodo}` — guardar ese ajuste (otros créditos / notas)
- `GET    /contabilidad/resumen-iva/{periodo}` — resumen mensual de IVA debito/credito estimado
- `GET    /contabilidad/arca/checklist/{periodo}` — pendientes antes de revisar/cargar ARCA
- `GET    /contabilidad/exportaciones/iva/{periodo}.csv` — CSV simple del resumen mensual
- `GET    /health` — chequeo de salud

## Importante ARCA

Esta API prepara la informacion interna y los importes estimados. No reemplaza
la presentacion en ARCA, no emite CAE por WebService y no sube automaticamente
Libro IVA Digital / IVA Simple. La carga final debe revisarla el contador contra
los servicios vigentes de ARCA.
