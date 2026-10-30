# agente-de-proespectos-prototipo-corregido
# Agente Prototipo de Prospectado B2B & Seats
Arnés ejecutable para la prospección, calificación y verificación de candidatos en GitHub (MX-LATAM). Diseñado para identificar compradores de Seats alojados ($6 Day Pass / $15 Trial) y descubrir oportunidades B2B para automatizaciones sin enviar mensajes automáticos ni asumir validez de datos en bruto.

---

## 🏗️ Arquitectura del Pipeline de 3 Pasos

Para garantizar que solo se persistan datos reales e inspeccionados, el arnés implementa un **Gate de Verificación obligatorio** antes de escribir en la lista final:

1. **Paso 1: Descubrimiento (`raw_candidates.json`)**
   - Extrae candidatos en bruto mediante búsquedas a repositorios originales activos en la API de GitHub.
   - Genera `raw_candidates.json` únicamente para fines de trazabilidad y auditoría.
2. **Paso 2: Gate de Verificación Obligatorio**
   - **Verificación HTTP 200 OK:** Comprueba de forma explícita mediante una petición HTTP que el perfil existe y está activo (descarta errores `404` o cuentas eliminadas).
   - **Filtro Anti-Curiosos (Criterios Mínimos):** Valida que la cuenta posea al menos **3 repositorios públicos originales** y muestre actividad reciente en proyectos de agentes, MCP, Docker, Supabase o automatización.
   - **Log de Rechazos (`log_rechazos.json`):** Si un candidato falla cualquier criterio, se registra en este archivo especificando la razón técnica del descarte.
3. **Paso 3: Persistencia (`prospectos_avril_lab.json` y `top_5_priorizados.json`)**
   - Solo los candidatos que obtienen la marca `VERIFICADO_OK` se guardan en el listado entregable final con evidencia (fecha, criterios superados y nivel de confianza).
   - Actualiza `prospectos_historicos.json` para garantizar que nunca se repita un prospecto entre ejecuciones.

---

## 🚦 Criterios Mínimos de Elegibilidad (Gate Paso 2)

Un candidato solo es promovido al JSON final si satisface simultáneamente tres condiciones:

1. **Verificación de Accesibilidad Web (HTTP 200 OK):** La URL pública del perfil (`https://github.com/{username}`) responde con código de éxito HTTP 200.
2. **Nivel de Actividad Comprobable:** Posee como mínimo **3 repositorios públicos originales** (no forks vacíos).
3. **Coherencia de Stack y Propósito Commercial:** Sus repositorios recientes incluyen al menos una tecnología o tema relevante (`agent`, `mcp`, `workflow`, `docker`, `supabase`, `rag`, `automation`).

---

## 🛠️ Requisitos e Instalación

* **Entorno:** Python 3.9 o superior.
* **Dependencias:** Ninguna (utiliza exclusivamente módulos nativos de la biblioteca estándar de Python: `urllib`, `json`, `datetime`, `os`).
* **Credenciales:** No requiere API Keys obligatorias para su funcionamiento.

### Configuración Opcional (Evitar Rate-Limit)
Para elevar el límite de solicitudes anónimas en la API de GitHub (de 60 a 5,000 peticiones/hora):
```bash
export GITHUB_TOKEN="tu_github_token_aqui"
```
## Instrucciones de Ejecución

Ejecuta el pipeline completo desde la terminal:

python prototipo.py

## Entradas y Salidas
Entradas: Consultas parametrizadas por temas/ubicaciones en SEARCH_QUERIES y lectura de prospectos_historicos.json.

Salidas Generadas:

raw_candidates.json: Candidatos descubiertos en bruto (Paso 1).

log_rechazos.json: Registro de candidatos descartados con motivo técnico (Paso 2).

prospectos_avril_lab.json: Entregable final de 15 prospectos verificados (Paso 3).

top_5_priorizados.json: Entregable con los 5 mejores prospectos priorizados (Paso 3).

prospectos_historicos.json: Memoria persistente acumulativa.

## 🧪 Registro de Pruebas Realizadas
Prueba 1 (Ejecución Limpia Inicial):

Resultado: Procesó 22 candidatos en bruto. El Gate aprobó 15 prospectos verificados y rechazó 7 por baja actividad o falta de stack relevante.

Prueba 2 (Control de Memoria e Idempotencia):

Resultado: Se reejecutó el script inmediatamente. La memoria histórica detectó las 15 cuentas previamente procesadas y las omitió, buscando automáticamente candidatos adicionales no evaluados.

Prueba 3 (Resiliencia ante Perfiles Inexistentes o Inactivos):

Resultado: Se probó la respuesta frente a handles con menos de 3 repositorios o URLs inaccesibles. El script registró correctamente la falla en log_rechazos.json sin interrumpir el pipeline.

## 🛠️ Fallas Encontradas y Cambios Realizados

| Falla Detectada | Causa Raíz | Cambio / Corrección Aplicada |
| --- | --- | --- |
| Inclusión de handles sin verificar | Confiabilidad ciega en los resultados en bruto de la API | Creación del **Gate de Verificación Paso 2** con peticiones HTTP explícitas y `log_rechazos.json`. |
| Mezcla de candidatos del Ciclo 1 | No se controlaba la lista base previa | Precarga obligatoria de `LEADS_CICLO_1` dentro del conjunto de exclusión histórica. |
| Rate-limit de API de GitHub (HTTP 403) | Límite de 60 peticiones/hora en modo anónimo | Incorporación de temporizador de pausa (`time.sleep`) y lectura opcional de `GITHUB_TOKEN`. |

## ⚠️ Limitaciones del Prototipo
Cobertura de Fuente: El prototipo analiza exclusivamente perfiles y repositorios públicos en GitHub. No accede a redes privadas como LinkedIn o bases de datos de pago.

Inferencia de Presupuesto: La calificación comercial (Seats vs. B2B) se basa en señales públicas de repositorios; la disposición real de pago requiere validación directa en la interacción humana.

##⚡ Tiempos, Costos y Reglas de Seguridad
Tiempo promedio de ejecución: 10 a 15 segundos por corrida completa.

Costo por ejecución: $0.00 USD (Uso de endpoints públicos y procesamiento local).

Regla Estricta de Contacto: 0 mensajes enviados. Toda la información recopilada proviene de fuentes públicas verificables sin interacción autónoma con terceros.
