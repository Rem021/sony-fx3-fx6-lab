# Sony A6000 — Silent Shutter

[![módulos](https://img.shields.io/endpoint?url=https://nicolvus.github.io/a6000-fw-decomp/badge-modulos.json)](https://nicolvus.github.io/a6000-fw-decomp/progress/)
[![sesiones](https://img.shields.io/endpoint?url=https://nicolvus.github.io/a6000-fw-decomp/badge-sesiones.json)](https://nicolvus.github.io/a6000-fw-decomp/progress/)
[![pruebas](https://img.shields.io/endpoint?url=https://nicolvus.github.io/a6000-fw-decomp/badge-pruebas.json)](https://nicolvus.github.io/a6000-fw-decomp/progress/)

**Hito alcanzado: la Sony A6000 (ILCE-6000) dispara en silencio.** Con el firmware modificado **3.23** instalado en la cámara
real, el obturador mecánico deja de accionarse en la captura normal y la cámara hace fotos sin error. Es el resultado de la
ingeniería inversa del firmware 3.21 de la A6000 (BIONZ + microcontrolador Darwin) y de un parche de **2 bytes** sobre Darwin.

> **Estado:** funcional en una cámara real, confirmado por el usuario tras instalar la 3.23 (T040, 27-10-2026). Las capturas y
> medidas de esa validación aún no están archivadas en el repositorio (ver [Límites](#límites-y-riesgos)).
> Instalar firmware modificado puede dejar la cámara inservible. **No hay recuperación independiente demostrada.** Úsalo bajo tu
> responsabilidad y solo tras leer [Riesgos](#límites-y-riesgos).

## Cómo funciona

El obturador de la A6000 lo gobierna **Darwin**, un microcontrolador aparte (`darwin_core`), que mueve las cortinillas mecánicas
y las rearma tras cada foto. La solución actúa sobre Darwin en dos pasos, apilados:

| Paso | Cambio en `darwin_core.bin` (3.21) | Efecto |
|---|---|---|
| **Tipo 0** | `0x20c78..0x20c7f` → `b 0x20c8e; nop; nop; nop` | La función de tipo de mecanismo `0x20c74` devuelve siempre 0 (rama que ya existe en el firmware, «sin bobinas»): no se activan P4D/P4E |
| **B1a** | `0x1fe6a: 28 46 → 0a e0` (2 bytes) | La compuerta `0x1fe66` devuelve siempre 0 sin leer su estado; los arrancadores eligen la lista `[0,7,8,9,10]` de la máquina exterior, que **no usa el motor del obturador** en captura ni en rearme |

Resultado: la captura y el rearme normales no llegan a las primitivas que accionan P40/P41, y la exposición la determina el
sensor (lectura y reinicio por filas) en lugar de las cortinillas. Detalle, direcciones y veredictos en el informe
[E25](docs/capture/e25-desactivacion-mecanica.md) y la [auditoría independiente E25-06](docs/capture/e25-06-auditoria-independiente-paquetes.md).

Los paquetes de firmware se construyen, verifican y auditan offline antes de tocar la cámara (69 comprobaciones de empaquetado y
una batería de 21 pruebas independientes sobre cabecera FDAT, cifrado, sumas y diferencias de bytes).

## Versiones: qué es la 3.22, la 3.23 y la 3.24

Sony solo publicó hasta la **3.21**. Las demás versiones las generé yo con el firmware oficial y solo cambian el Darwin; el resto del paquete
es el oficial. El actualizador de la cámara solo acepta versiones **estrictamente mayores** que la instalada, así que cada paso necesita un número nuevo.

| Versión | Origen | Qué hace |
|---|---|---|
| **3.21** | Oficial de Sony | Darwin original: el obturador mecánico se acciona con normalidad |
| **3.22** | Mía (T024, 26-10-2026) | **Apaga las bobinas.** Darwin «tipo 0»: la función de tipo de mecanismo `0x20c74` devuelve siempre 0 (rama que ya existe en el firmware, «sin bobinas»), así que los cuatro escritores de P4D/P4E dejan de activarlas. El resto del mecanismo sigue funcionando |
| **3.23** | Mía (T040, 27-10-2026) | 3.22 **+ B1a**: la compuerta `0x1fe66` devuelve siempre 0 y Darwin ya no acciona el **mecanismo completo** (P40/P41) en captura ni rearme. Es la versión que dispara en silencio |
| **3.24** | Mía, solo recuperación | Darwin **oficial** con versión 3.24, para volver atrás: con la 3.23 instalada, el guard solo admite un número mayor |

La 3.22 fue el primer paso: demostró que la cámara acepta un firmware con Darwin propio (el actualizador solo comprueba un CRC-32) y que
apagar las bobinas no la bloquea. La 3.23 pasó de apagar las bobinas a apagar el mecanismo entero. Por eso la instalación documentada
va de 3.22 a 3.23, que fue mi ruta real. El efecto «sin bobinas» de la 3.22 es **estático** (lectura del código), no una medida física.

## Línea temporal del hito

| Fecha | Qué pasó |
|---|---|
| 20-10-2026 | Primeras pruebas en cámara (RAM, NVRAM); incidente de arranque recuperado con backup NVRAM |
| 26-10-2026 | Darwin tipo 0 preparado como FDAT 3.22 |
| 27-10-2026 | E23: con ShutMode 0 forzado, `r5` controla la exposición (T035–T039) |
| 27-10-2026 | E25: candidato B1a (2 bytes) y paquetes 3.23/3.24 preparados y auditados offline (E25-05, E25-06) |
| 27-10-2026 | **T040:** SHA-256 de ambos paquetes verificados, guard de versiones medido (3.22 < 3.23 < 3.24), NVRAM volcada, **3.23 (B1a) instalado**; la cámara arranca en 3.23 |
| 27-10-2026 | **El usuario confirma que la cámara dispara en silencio y sin error** |

## Instalación (3.21 o 3.22 → 3.23)

Requisitos: A6000 con firmware **3.21 o 3.22**, batería cargada, cable USB y [`pmca-console`](https://github.com/ma1co/Sony-PMCA-RE).
El actualizador solo acepta versiones estrictamente mayores que la instalada, y la 3.23 lo es sobre ambas. **Probado únicamente desde la 3.22** (T040):
la 3.22 ya llevaba el Darwin «tipo 0» (desactivar bobinas) y la 3.23 añade B1a (no accionar el mecanismo completo). Desde la 3.21 original
debería funcionar igual, porque el paquete 3.23 es un firmware completo (tar oficial con solo los dos ficheros de Darwin cambiados) y no un parche
incremental, pero **no se ha probado**. El repositorio **no incluye** firmware de Sony, volcados ni binarios; los paquetes se generan a partir de tu
propio firmware (ver [E25-05](docs/capture/e25-05-preparacion-paquetes-323-324.md)).

1. **Backup de NVRAM** en modo servicio antes de nada: `scripts/senser_backup_dump.py` (guarda los volcados fuera del repositorio).
2. **Verifica el SHA-256** del paquete 3.23 (`4c21353d…`) y del de recuperación 3.24 (`e1345aff…`) con `scripts/recovery/r1_manifest.py verify`.
3. **Mide el guard** sin flashear (`fdat_guard_probe.py`): debe rechazar tu versión instalada y aceptar la 3.23 y la 3.24.
4. Flashea el 3.23 con `pmca-console firmware`; la cámara se reinicia sola y `pmca info` debe dar **3.23**.
5. Registra la prueba en [registro-pruebas-camara.md](docs/capture/registro-pruebas-camara.md) (T040 es el modelo).

**Volver atrás:** `analysis/darwin-patch/fdat/recuperacion-324/firmware_packed.dat` restaura el Darwin oficial como versión 3.24.
Solo funciona si la cámara sigue llegando al actualizador.

## Qué se ha medido en las imágenes (3.23)

- **Imágenes completas:** la cámara guarda en la tarjeta el JPEG de 6000×4000 y el RAW (ARW) de 6024×4024, sin obturador mecánico. El callback de la
  app de pruebas solo recibe un JPEG reducido de 1616×1080; las medidas serias se hacen sobre el ARW (T044).
- **Disparo y rearme:** 36 de 36 disparos en ráfagas de 6 y 10 de 10 sueltos; rearme de 0,7–1,0 s entre disparos y latencia de 2,6–2,9 s a velocidades rápidas.
- **Error de apertura:** tras un disparo, `CameraEx` puede tardar hasta ~1 s en poder reabrirse; con un reintento no hay fallos (T045).
- **Exposición — limitación medida ([E25-10](docs/capture/e25-10-exposicion-por-fila.md)):** sin cortina trasera, el sensor se reinicia a la vez y se lee por filas, y
  la exposición de la fila `i` es **T + ≈7 ms + 15,2 µs·i** (lectura completa ≈ 61 ms). Por eso, con ISO fijo, la velocidad no escala la exposición de 1/4000 a 1/500
  y la fila inferior recibe hasta 3,7× la superior; de 1/60 en adelante el efecto pesa poco. No lo introduce B1a (ya se veía con la 3.22). **T046 (parches en RAM) lo explica:**
  con ShutMode 0 el reinicio es por filas, la exposición es uniforme y vale (4219 − `r5`) × 15,2 µs. Falta que la foto use ese modo con `r5` calculado a partir de la
  velocidad y una vía permanente (el parche es de BIONZ, no de Darwin): E25-11.

## Límites y riesgos

- **Sin recuperación independiente de Darwin** ([E24-04](docs/capture/e24-04-dictamen-seguridad.md), [E25-04](docs/capture/e25-04-recuperabilidad-y-decision.md)):
  la 3.24 solo sirve si el actualizador sigue accesible. Un Darwin que no arranque podría no tener vuelta atrás por USB.
- **Validación física sin archivar:** el funcionamiento lo ha confirmado el usuario en la cámara; faltan capturas de ejemplo,
  medidas de obturador y de rearme (E25-01 en [PENDIENTES](docs/PENDIENTES.md)).
- **Escenarios de error sin medir:** la operación 5 de Darwin (P40/P41=3, XOR=0) y P4B/P4C siguen activos; su efecto físico no se ha medido.
- **Copia de respaldo en el mismo disco** (R1): falta la copia externa.

## Contexto de la investigación

- **Firmware analizado:** A6000 3.21 (sensor IMX210, `av-cam`, `libObj.so`, `darwin_core`), comparado con la **A7S 3.20** (IMX235, que
  sí ofrece Silent) y la **A6300 2.01**.
- **Método:** análisis estático con REA y Ghidra, contrastado con bytes e instrucciones; cada afirmación se etiqueta `VERIFICADO`,
  `INFERENCIA` o `NO_VERIFICADO`. Política en [docs/STATE.md](docs/STATE.md).
- **Pruebas en cámara:** [registro T001–T040](docs/capture/registro-pruebas-camara.md), con backup NVRAM previo.
- **Descartado por el camino:** vía volátil por RAM ([E25-02](docs/capture/e25-02-validacion-candidato-y-via-volatil.md)) y el control de
  Silent de la A7S, que la A6000 no tiene ([S401](docs/capture/s401-a7s-silent-control-path.md)).

![progreso](https://nicolvus.github.io/a6000-fw-decomp/progress/progress.svg)

<sub>Badges y tablero: <https://nicolvus.github.io/a6000-fw-decomp/progress/> · índice de sesiones: <https://nicolvus.github.io/a6000-fw-decomp/>.
Los publica el flujo [Pages](.github/workflows/pages.yml) desde `site/` con `scripts/build_pages_status.py`.</sub>

## Navegación

| Necesito… | Voy a… |
|---|---|
| Contexto mínimo para retomar | [knowledge/CURRENT.md](knowledge/CURRENT.md) |
| Conclusiones y límites vigentes | [docs/STATE.md](docs/STATE.md) |
| Qué falta | [docs/PENDIENTES.md](docs/PENDIENTES.md) |
| Informes por subsistema | [docs/INDEX.md](docs/INDEX.md) |
| Registro de pruebas en cámara | [docs/capture/registro-pruebas-camara.md](docs/capture/registro-pruebas-camara.md) |
| Historial cronológico | [knowledge/PROGRESS.md](knowledge/PROGRESS.md) |
| Subproyecto del obturador | [projects/electronic-shutter/](projects/electronic-shutter/README.md) |
| README anterior (investigación previa al hito) | [docs/history/README-historial-2026-10-27.md](docs/history/README-historial-2026-10-27.md) |
| Uso por agentes | [docs/agent/README.md](docs/agent/README.md), [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md) |

## Estructura

| Ruta | Contenido |
|---|---|
| `docs/` | Estado, pendientes, índice, correcciones e informes (`docs/capture/`) |
| `knowledge/` | Resumen operativo (`CURRENT.md`) e historial (`PROGRESS.md`) |
| `analysis/` | Evidencia por sesión, `darwin-patch/` (paquetes, no versionados) y volcados de cámara (no versionados) |
| `scripts/` | Volcado de NVRAM, estado de cámara, recuperación (`recovery/`), empaquetado (`e25_05/`), auditoría (`e25_06/`), REA y conocimiento |
| `tests/` | Verificadores por informe; los que necesitan firmware no versionado fallan o se omiten según el caso |
| `projects/electronic-shutter/` | Subproyecto del obturador electrónico |
| `site/` | Página de estado en GitHub Pages |

## Reproducir y verificar

```bash
source .venv/bin/activate
python -m pytest tests/test_e25_06_auditoria.py -q   # auditoría de los paquetes (necesita los paquetes locales)
python3 scripts/recovery/r1_manifest.py verify       # integridad de la copia de respaldo
python3 scripts/knowledge/search.py text "concepto"  # buscar sin releer el repositorio
```

## Seguridad y contribución

- No se suben firmware, `*.bin`/`*.elf`, volcados ni binarios de Sony. Commits convencionales.
- Toda prueba en cámara lleva backup NVRAM previo y se anota en el registro.
- Toda tarea actualiza [docs/PENDIENTES.md](docs/PENDIENTES.md) en el mismo commit.
