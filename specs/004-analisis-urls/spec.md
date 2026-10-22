# Feature Specification: Análisis y Expansión de URLs

**Feature Branch**: `feature/analisis-urls`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Extraer y normalizar todas las URLs, detectar trucos de enmascaramiento y expandir acortadores sin exponer la red interna."

## Context

**Problema**: las URLs de un correo no se extraen ni analizan de forma sistemática; los enlaces que muestran un destino y llevan a otro, o los acortadores, pasan sin revisión.

**Objetivo**: extraer y normalizar todas las URLs, detectar trucos de enmascaramiento y expandir acortadores sin exponer la red interna.

**Fuente**: `docs/PLAN_MODIFICACIONES_PHISHGUARD.md`, módulo M04b y catálogo 5.2.

**Depende de**: 02.

## User Scenarios & Testing

### User Story 1 - Extracción, banderas y expansión segura de URLs (Priority: P1)

Para cada correo, se extraen y normalizan las URLs, se detectan trucos de enmascaramiento (texto distinto del destino, IP, acortador, punycode, TLD de riesgo, etc.), se expanden acortadores de una lista configurable con límite de saltos y tiempo, validando la IP destino en cada salto (protección SSRF), sin descargar contenido ni ejecutar JavaScript, y saneando parámetros sensibles antes de cualquier consulta externa.

**Why this priority**: las URLs son el vector principal de phishing. Sin extracción y expansión segura, los enlaces engañosos pasan sin revisión y el sistema es vulnerable a SSRF.

**Independent Test**: dar un correo con URLs conocidas y verificar las banderas activadas, la expansión y que ninguna conexión fue a una IP privada.

**Acceptance Scenarios**:

1. **AC-URL-01**: un enlace con texto `https://banco.com` y destino `http://evil.example` activa `URL_TEXTO_DISTINTO_DESTINO`.
2. **AC-URL-02**: ninguna expansión se conecta a direcciones privadas, loopback o de metadatos, ni tras una redirección ni cuando un DNS resuelve a una IP privada (servidor local de prueba que redirige a 127.0.0.1).
3. **AC-URL-03**: la expansión se detiene a los 5 saltos y a los 5 s y registra `REDIRECCION_EXCESIVA` (probar 4, 5 y 6 saltos).
4. **AC-URL-04**: no se descarga el cuerpo de ninguna respuesta durante la expansión.
5. **AC-URL-05**: URLs duplicadas tras normalizar se reportan una sola vez.
6. **AC-URL-06**: una URL con `?token=abc&email=a@b.com` se sanea antes de salir de la función de consulta externa.
7. **AC-URL-07**: una URL malformada, vacía o de 100 000 caracteres no lanza excepción no controlada.

### Edge Cases

- 4, 5 y 6 saltos de redirección.
- URL vacía, malformada, de 100 000 caracteres.
- DNS que resuelve a IP privada tras redirección.
- URL con parámetros sensibles.

## Requirements

### Functional Requirements

- **FR-001** (RF1): Extraer URLs de `href`, `src`, `action` y texto plano; deduplicar tras normalizar (host en minúsculas, sin fragmentos ni parámetros de seguimiento conocidos) conservando la URL original para el reporte.
- **FR-002** (RF2): Banderas del catálogo 5.2: `URL_TEXTO_DISTINTO_DESTINO`, `URL_HOST_IP`, `URL_ACORTADA`, `URL_ARROBA`, `URL_PUNYCODE`, `URL_TLD_RIESGO`, `URL_SUBDOMINIOS_EXCESIVOS`, `URL_PUERTO_NO_ESTANDAR`, `URL_HTTP_SIN_CIFRADO`, `URL_LARGA` (> 200 caracteres), `URL_PARAMETROS_SENSIBLES`, `REDIRECCION_EXCESIVA`, `URL_DOMINIO_NUEVO`.
- **FR-003** (RF3): Expansión solo de acortadores de una lista configurable: método HEAD (o GET sin descargar el cuerpo), máximo 5 saltos, 5 s por URL, solo `http` y `https`.
- **FR-004** (RF4): Protección contra SSRF: nunca conectar a direcciones privadas, de enlace local, loopback o de metadatos de nube (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16, ::1, fc00::/7, fe80::/10). Se resuelve el DNS y se valida la IP antes de conectar, en cada salto.
- **FR-005** (RF5): No ejecutar JavaScript ni descargar contenido.
- **FR-006** (RF6): Si la reputación de la URL ya es conocida por la caché de VirusTotal, no se expande por conexión directa.
- **FR-007** (RF7): Antes de cualquier consulta externa se eliminan de la URL los parámetros sensibles (`token`, `key`, `session`, `email`, `user`, `code`, `password`) y los valores con forma de correo.

## Success Criteria

### Measurable Outcomes

- **SC-001**: todas las URLs de un correo se extraen, normalizan y reportan sin duplicados.
- **SC-002**: ninguna expansión se conecta a una IP privada/loopback/metadata, ni siquiera tras redirección.
- **SC-003**: la expansión se detiene en 5 saltos o 5 s y registra `REDIRECCION_EXCESIVA`.

## Assumptions

- **Fuera de alcance**: consulta a VirusTotal (spec 06), códigos QR y análisis de adjuntos.
- **Hint para plan**: Strategy para banderas, Adapter para resolución DNS y cliente HTTP (para simularlos), `urllib.parse` y `ipaddress` de la biblioteca estándar; pruebas de seguridad con servidor local.
