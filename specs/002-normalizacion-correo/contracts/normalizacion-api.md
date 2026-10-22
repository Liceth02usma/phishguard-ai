# Contrato: API pública de normalización

Módulo: `src/level2_agent/normalizacion/__init__.py`. Consumidores: poller (ahora),
specs 003–05 (banderas/URLs/adjuntos) y spec 11 (persistencia con vista enmascarada).

## Funciones públicas

### `normalizar_desde_gmail(raw_bytes: bytes, message_id: str) -> EmailData`

- **Entrada**: bytes crudos del mensaje (Gmail `format="raw"`, Base64 url-safe ya decodificado) y el ID del mensaje de Gmail.
- **Salida**: `EmailData` con `origen="gmail"`, `message_id` dado, todos los campos legacy y nuevos poblados y coherentes.
- **Errores**: NO lanza por entrada malformada — degrada con `ENTRADA_DEGRADADA` + `revision_manual=True` (AC-NORM-06). Solo `TypeError` si `raw_bytes` no es `bytes`.

### `normalizar_desde_eml(contenido: bytes) -> EmailData`

- **Entrada**: contenido de un archivo `.eml` (bytes).
- **Salida**: ídem con `origen="api"`, `message_id` = cabecera `Message-ID` o generado determinista (`hash sha256[:16]` del contenido) si falta.
- **Errores**: idéntica política de degradación.

### `normalizar_desde_api(payload: dict[str, Any]) -> EmailData`

- **Entrada**: payload JSON de la futura API. Formato provisional **[VERIFICAR: spec 12]**:
  `{ "raw"?: str_base64, "subject"?: str, "from"?: str, "to"?: str, "text"?: str, "html"?: str, "headers"?: {k: v} }`.
  Con `raw` usa el camino MIME; sin él, construye `CorreoBruto` desde campos.
- **Salida**: `origen="api"`.
- **Errores**: payload sin ningún campo útil → `ENTRADA_DEGRADADA`.

### `enmascarar_para_terceros(email_data: EmailData) -> EmailData`

- **Entrada**: `EmailData` normalizado (o legacy).
- **Salida**: copia con PII enmascarada en `subject`, `recipient`, `textBody`, `htmlBody`
  (truncado a `LIMITE_CARACTERES_TEXTO`), `headers` y valores de `cabeceras` — EXCEPTO la
  cabecera `From` (remitente exento, FR-005) y excepto `message_id`/`origen`/hashes.
- **Garantía (AC-NORM-04)**: la salida no contiene direcciones de correo ni secuencias de
  13–19 dígitos sin enmascarar. Idempotente: `f(f(x)) == f(x)`.
- **Uso obligatorio**: antes de enviar texto de correo al modelo de lenguaje (Art. 0.6/V.4)
  o persistirlo (spec 11).

### `enmascarar_texto(texto: str) -> str`

Función pura de bajo nivel (reexportada): correos → `j***@empresa.com`; dígitos
13–19 (con espacios/guiones opcionales) → `[NÚMERO_OCULTO]`.

## Conducta de límites (FR-004) — parte del contrato observable

| Condición | Observador en el `EmailData` devuelto |
|---|---|
| `len(raw) > LIMITE_BYTES_CORREO` | `"LIMITE_EXCEDIDO" in banderas` y `revision_manual=True` |
| `len(texto_limpio) > 20_000` (antes de acotar) | ídem + `texto_limpio` mide exactamente 20 000 |
| `len(urls) > 200` (antes de acotar) | ídem + `len(urls) == 200` (primeras 200) |
| `len(adjuntos) > 20` | ídem + `len(adjuntos) == 20` |
| profundidad MIME > 10 | ídem + partes profundas ignoradas |

En el límite exacto NO hay bandera. Varias excedencias acumulan UNA sola entrada
`"LIMITE_EXCEDIDO"`.

## Garantías transversales

- Sin red: ninguna función consulta servicios externos.
- Sin escritura a disco; adjuntos solo en memoria con SHA-256 (Art. V.5).
- Determinismo: misma entrada → mismo `EmailData` (los hashes y el ID generado son
  funciones del contenido).
- `model_dump()` no incluye `htmlBody` (nunca persistido).
