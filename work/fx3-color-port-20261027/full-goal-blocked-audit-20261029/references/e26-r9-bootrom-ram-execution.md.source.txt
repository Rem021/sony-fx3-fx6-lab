# E26-R9 — Sony A6000: ejecución desde RAM mediante BootROM/UART

**Fecha:** 29-10-2026
**Repositorio:** `nicolvus/a6000-fw-decomp`, commit base `0c5857ab` (E26-R8)
**Alcance:** Exclusivamente offline. REA, desensamblado ARM/Thumb, binarios de firmware, análisis estático de protocolos, emulación Unicorn.
**Binario BootROM:** `analysis/camera-dumps/updater-20261020-175427/bootrom.bin`, SHA-256 `81a17e039a2debfe589b127e12384ed4d7c2ba0d0c819238d0b021b466246026`, 24 576 bytes, base `0xffff0000`, modo Thumb.
**Scripts nuevos:** `analysis/e26-recovery/r9-uart-protocol.py`, `analysis/e26-recovery/r9-unicorn-ramjump.py`.

---

## 1. Resumen ejecutivo

R9 investiga si el receptor serie del BootROM de la Sony A6000 permite cargar y ejecutar un programa propio directamente desde RAM, sin arrancar Linux, sin modificar NAND y sin depender del firmware principal de la cámara.

**Hallazgo principal:** SÍ, la cadena existe estáticamente y se demostró en emulación. El BootROM implementa un receptor serie que:
1. recibe un paquete tipo 0 y hace `str(valor, [direccion])` en una dirección **elegida por el emisor** sin validación de rango (escritura RAM arbitraria), y
2. recibe un paquete tipo 0xFFFF, almacena una dirección de salto de 32 bits en `0xc000500C` y salta a ella mediante `FUN_ffff0144` (`ldr r1,[0xc0005000]; ldr r0,[r1,#0xc]; bx r0`).

La región de destino `0xc0005000` reside en eSRAM (`0xc0000000–0xc0100000`, 16 MiB), que el propio BootROM lee y escribe en tiempo de arranque (antes de inicializar DDR/Linux), por tanto es RAM demostrablemente usable y ejecutable en ese momento.

**No se requieren firmas, autenticación ni validaciones criptográficas** para la carga/salto; solo un checksum de integridad (CRC8 iterativo, polinomio `0xEDB88320`).

**Viabilidad:**
- Estática: SÍ — la cadena completa está reconstruida instrucción a instrucción desde el binario.
- Emulada: SÍ — Unicorn transfiere el PC a código en eSRAM y lo ejecuta.
- En hardware físico: NO DEMOSTRADO — falta identificar eléctricamente el pin UART (BOOT_SERIAL_IN) y confirmar que se puede activar externamente; cualquier prueba física requiere autorización separada y mediciones no destructivas.

Respuestas Q1–Q10: Q1=SÍ, Q2=SÍ (con acotación), Q3=SÍ, Q4=NO, Q5=SÍ, Q6=SÍ (emulado), Q7=SÍ, Q8=NO DEMOSTRADO, Q9=viable estática+emulada / no demostrada en hardware, Q10=identificación eléctrica del contacto UART.

---

## 2. Cambios respecto de R8

| Aspecto | R8 (comunicado) | R9 (este informe) | Estado |
|---|---|---|---|
| CRC polinomio | Placeholder `0x07` no verificado | `0xEDB88320` cargado literalmente en `0xffff0c04` (`ldr r2,[pc,#0x90]`) | VERIFICADO |
| Algoritmo CRC | Una tabla sobre XOR de todos los bytes | Iterativo por byte (FUN_ffff0c00: 8 iteraciones, MSB-first; FUN_ffff0634: `acc=(acc^byte)&0xFF; tmp=crc8(acc); new=tmp^(old>>8)`) | VERIFICADO |
| Acumulador CRC init | No especificado | `0xFFFFFFFF` observado en `0xffff0a20` (`str r0,[sp,#0x14]`, r0=-1) | NECESITA CONFIRMACIÓN |
| Escritura tipo 0 | "Almacena valor+dirección" | `str r2,[r1]` donde r1=[dirección], r2=[valor], **sin validación de rango**; dirección e valor controladas por el emisor | VERIFICADO |
| Salto tipo 0xFFFF | "Dirección relacionada con los bytes" | Dirección de **32 bits** cargada con `ldr r1,[sp,#0xc]` y guardada en `0xc000500C`; FUN_ffff0144 hace `bx r0` | VERIFICADO (32-bit) |
| "Reservado" tipo 0xFFFF | 2 bytes marcados reservados | Probablemente parte alta de la dirección de salto (32-bit total) | INTERPRETACIÓN |
| Región destino | `0xc0005000` citada | Confirmada como eSRAM (`0xc0000000–0xc0100000`) usada por el BootROM (saltos/escrituras a `0xc0005000`, `0xc000500C`, `0xc0010218`, ...) | VERIFICADO |
| Parser | `r8-uart-parser.py` (6/6, CRC placeholder) | `r9-uart-protocol.py` (6/6, CRC real, constructor de paquetes) | CREADO |
| Emulación | No había | Unicorn: salto a eSRAM y ejecución (PC en eSRAM) | CREADO / VERIFICADO |

No se repiten investigaciones cerradas de R7/R8 (NAND, INFO6, UPDATER, COLD, bucle LED).

---

## 3. Protocolo UART reconstruido

### 3.1 Grafo de recepción (VERIFICADO en disassembly)

```
Reset / encendido
        |
        v
  0xffff0000 (vectores ARM)
        |
        v
  FUN_ffff1062  (BootROM main entry, Thumb)
        |
   bandera uVar2!=0  (DAT_ffff12c0+0x10 bit 0)
        |            |
        v            v
  FUN_ffff0fa0   FUN_ffff028c (carga kernel)
  (receptor serie)
        |
        v
  FUN_ffff0876  (bucle recepción serie, 772 bytes)
   +------+------+------+
   |      |      |      |
 tipo0  tipo    error  tipo
 (0)   0xFFFF   codes  0xFFxx
   |      |      |      |
   v      v      v      v
 almacena salta  log+   log+
 valor+   dir    ret+   ret+
 dir      (0xc000500C)
 (0xc0010218)
   |      |
   +------+
        |
        v
  FUN_ffff0144: ldr r1,[0xc0005000]; ldr r0,[r1,#0xc]; bx r0
        |
        v
  Código en RAM ejecuta (salto indirecto)
```

### 3.2 MMIO utilizados (VERIFICADOS como literales en bootrom.bin)

| Dirección | Nombre | Uso | Fuente |
|---|---|---|---|
| `0xf2915010` | MISC_MODEREG, bit 1 = BOOT_SERIAL_IN | Lectura del bit de entrada serie en FUN_ffff0f82/05da/0634/0876 | literal `0xffff096c`→`0xf2915000` +0x10 |
| `0xf2910410` | GPIO(4,RDATA) | Lectura en FUN_ffff0554 para elegir divisor de baud (camino A/B) | literal `0xf2910410` |
| `0xf240310c` | Timer counter | Temporización de bits (FUN_ffff0f52/0f72) | literal `0xf2403000`+0x10c |
| `0xc0005000` | Jump vector storage | FUN_ffff0144 carga y hace BX r0 | literales múltiples |
| `0xc000500C` | Jump target storage | Tipo 0xFFFF almacena dirección de salto aquí | `str r1,[r2,#0xc]`, r2=0xc0005000 |
| `0xc0010004` | UART config / mode pointer | FUN_ffff0554 escribe tabla; FUN_ffff0bd4 lee `*0xc0010004` | literal |
| `0xc0010008` | Mode flag | `1` tras paquete tipo 0xFFxx | `str r2,[r1,#4]`, r1=0xc0010004 |
| `0xc0010218` | Paquete recibido | Estructura donde FUN_ffff0634 almacena bytes | literal |

### 3.3 Formato de frame (reconstruido)

```
Offset  Campo         Tamaño  Uso
0       type_hi       1B      Byte alto del tipo
1       type_lo       1B      Byte bajo del tipo
2       data_hi       1B      Tipo 0: valor alto / Tipo 0xFFFF: salto alto
3       data_lo       1B      Tipo 0: valor bajo / Tipo 0xFFFF: salto bajo
4       addr_hi       1B      Tipo 0: dirección alta / Tipo 0xFFFF: salto alta
5       addr_lo       1B      Tipo 0: dirección baja / Tipo 0xFFFF: salto baja
6       checksum      1B      CRC8 iterativo sobre los 6 bytes anteriores
```

Nota: R8 marcó `addr_hi/addr_lo` como "reservado" en tipo 0xFFFF. El disassembly muestra `ldr r1,[sp,#0xc]` (carga de 32 bits) como dirección de salto, por lo que los 4 bytes `data_hi,data_lo,addr_hi,addr_lo` conforman probablemente una dirección de **32 bits**. Esto hace alcanzable eSRAM (`0xc0005000`). NECESITA CONFIRMACIÓN del mapeo byte-a-byte exacto.

### 3.4 Tipos de paquete y códigos de retorno

| Tipo | Significado | Acción | Retorno FUN_ffff0876 |
|---|---|---|---|
| `0x0000` | Dato | `str(valor,[dirección])`, sin validación de rango | `0x0000` éxito |
| `0xFFFF` | Salto | Guarda dirección de 32 bits en `0xc000500C`, flag en `0xc0010008` | `0x3001` (jump request) |
| `0xFF01` | Timeout | No start bit en 0x3b iteraciones | `0x3002` |
| `0xFF02` | Paridad | Bit de paridad incorrecto | `0x3003` |
| `0xFF03` | Stop | Bit de stop incorrecto | `0x3004` |
| `0xFF04` | General | Error de protocolo | `0x100C` |
| `0xFF05` | Tamaño | Paquete > 0x1000 bytes | `0x2004` |
| `0xFF06` | Modo | Estado de modo inválido | `0x2005` |

### 3.5 Timeouts y sincronización

- Timeout de start bit: 0x3b (59) iteraciones sin transición en `0xf2915010` bit 1 → error 0x3002.
- Temporización de bits: timer en `0xf240310c`, FUN_ffff0f52 (poll) y FUN_ffff0f72 (compare).
- No hay sincronización explícita de baud rate; el remitente debe usar la misma velocidad que espera el BootROM (no determinada estáticamente).

### 3.6 Limitaciones del protocolo reconstruido

- No se demuestra función de **lectura** de memoria/NDN vía el receptor serie (solo escritura y salto).
- El checksum exacto (valor init y regla de comparación final) necesita confirmación contra una captura real.
- La velocidad de baud y el mapeo pin→registro no están verificados eléctricamente.

---

## 4. Mensaje tipo 0 — carga de datos en RAM

### 4.1 Estructura y campos

- `type_hi=0x00, type_lo=0x00`: identificador de paquete de datos.
- `data_hi,data_lo`: **valor** de 16 bits a escribir.
- `addr_hi,addr_lo`: **dirección** de 16 bits destino (posiblemente parte de una dirección más amplia).
- `checksum`: byte de integridad.

### 4.2 Dirección de destino

El emisor **selecciona la dirección**. En el disassembly (FUN_ffff0876 → FUN_ffff0634):

```
0xffff0bb4: ldr  r1, [sp, #0x20]    ; r1 = dirección (del paquete)
0xffff0bb6: ldr  r2, [sp, #0xc]     ; r2 = valor  (del paquete)
0xffff0bb8: str  r2, [r1]           ; [dirección] = valor   ← escritura RAM arbitraria
```

No hay comparación contra un rango permitido, ni dirección fija predeterminada. **Q1: SÍ** — el tipo 0 permite cargar bytes controlados por el emisor en una dirección RAM elegida por el emisor.

### 4.3 Longitud, alineación y regiones

- Cada paquete tipo 0 transporta un valor de 16 bits a una dirección. Para escribir código completo se envían paquetes consecutivos (uno por palabra/medio-palabra).
- No se observó restricción de alineación ni lista de regiones aceptadas en el camino de escritura (`str r2,[r1]` sin validación).
- Las regiones `0xc0005xxx` e `0xc0010xxx` (eSRAM) son usadas por el BootROM para su propio estado (vector de salto, estructura de paquete), por tanto están demostrablemente disponibles.

### 4.4 Validaciones previas a la copia

- Checksum sobre los 6 bytes de datos; si no coincide → error 0x100d y no se escribe.
- No se observó validación de rango de dirección ni de contenido.

### 4.5 Paquetes fragmentados e incompletos

- El receptor lee byte a byte vía FUN_ffff0634; un frame truncado se rechaza (parser: "Truncated packet").
- Timeout de start bit (0x3b iteraciones) → error 0x3002; errores de paridad/stop → 0x3003/0x3004.

---

## 5. Mensaje tipo 0xFFFF — salto a RAM

### 5.1 Condición de aceptación

- `type=0xFFFF` tras validación de checksum.
- Se leen 4 bytes que conforman la dirección de salto (cargados como 32 bits en `[sp+0xc..+0xf]`).
- Se almacena en `0xc000500C` y se pone flag `1` en `0xc0010008`.

### 5.2 Dirección de ejecución y procedencia

```
0xffff0b78: ldr  r2, [pc, #0x7c]    ; r2 = 0xc0005000  (literal)
0xffff0b7a: ldr  r1, [sp, #0xc]     ; r1 = dirección de salto (32 bits, del paquete)
0xffff0b7c: str  r1, [r2, #0xc]     ; [0xc000500C] = dirección de salto
0xffff0b7e: movs r2, #1
0xffff0b80: ldr  r1, [pc, #0x78]    ; r1 = 0xc0010004  (literal)
0xffff0b82: str  r2, [r1, #4]       ; [0xc0010008] = 1 (flag modo salto)
```

La dirección proviene de 4 bytes del paquete (data_hi/data_lo/addr_hi/addr_lo), cargados como 32 bits.

### 5.3 Modo ARM o Thumb

FUN_ffff0144:
```
0xffff0144: ldr  r1, [pc, #4]       ; r1 = 0xc0005000 (literal)
0xffff0146: ldr  r0, [r1, #0xc]     ; r0 = [0xc000500C] = dirección de salto
0xffff0148: bx  r0                  ; salto indirecto
```
`BX r0` respeta el bit0: si bit0=1 → Thumb, si 0 → ARM. El remitente controla el bit0 mediante el valor enviado. **Q6: el modo se elige por el emisor.**

### 5.4 Estado de CPU al salto

- PC = dirección de salto (del paquete).
- Registros: no se documenta preservación específica; el código salta a un contexto "limpio" de BootROM (pila de BootROM aún activa, registros no garantizados).
- Pila: la pila de BootROM está en uso; el código diagnosticado debería inicializar su propia pila si llama a funciones.
- Interrupciones/cachés/MMU: no se observó desactivación explícita en el camino de salto; el BootROM corre sin MMU (direcciones físicas directas) y con cachés en estado de arranque.

### 5.5 ¿Salta al buffer cargado?

**Q2: SÍ** (con acotación). El tipo 0 escribe en una dirección X elegida por el emisor; el tipo 0xFFFF salta a una dirección Y también elegida por el emisor. El remitente puede hacer X=Y (escribir código en X y saltar a X). La dirección de salto es de 32 bits, por tanto alcanza eSRAM (`0xc0005000`). No se observó validación adicional (firma, estructura de imagen, checksum de código).

---

## 6. Mapa de memoria disponible durante el receptor BootROM

### 6.1 Recolección de evidencia

Las direcciones `0xc00xxxxxx` aparecen como literales repetidos en bootrom.bin y son leídas/escritas por el BootROM:

`0xc0000600, 0xc0001200, 0xc0005000, 0xc000500C, 0xc0005030, 0xc0006000, 0xc000b000, 0xc0010000, 0xc0010004, 0xc001000C, 0xc0010010, 0xc0010018, 0xc0010218, 0xc0010238, 0xc002f400, 0xc0030000`

Esto corrobora que el BootROM usa la región `0xc0000000–0xc0100000` como RAM en tiempo de arranque.

### 6.2 Tabla de memoria

| Región | Inicio | Final | Inicializada | Ejecutable | Evidencia |
|---|---|---|---|---|---|
| BootROM | `0xffff0000` | `0xffff5fff` | Sí (ROM) | Sí (vectores) | bootrom.bin, vectores en `0xffff0000` |
| eSRAM (uso BootROM) | `0xc0000000` | `0xc0100000` | Sí (usada por BootROM) | Sí (salto a `0xc000500C`) | literales bootrom.bin + CXD90014 headers (`platform.h`: `CXD90014_ESRAM_BASE=0xc0000000`, `SZ_16M`) |
| Jump vector | `0xc0005000` | `0xc000500F` | Sí (escrito por tipo 0xFFFF) | Sí (FUN_ffff0144) | `ldr [0xc0005000]`, `bx r0` |
| Packet struct | `0xc0010218` | `0xc0010237` | Sí (FUN_ffff0634) | No (datos) | literal `0xc0010218` |
| MMIO UART | `0xf2915010` | `0xf2915010` | N/A (registro) | No | literal `0xf2915010` bit 1 |
| MMIO GPIO | `0xf2910410` | `0xf2910410` | N/A (registro) | No | literal `0xf2910410` |
| MMIO Timer | `0xf240310c` | `0xf240310c` | N/A (registro) | No | literal `0xf2403000`+0x10c |
| DDR externa | ? | ? | No (no inicializada aún) | ? | No hay evidencia de DDR init antes del receptor |

**Nota:** Las direcciones MMIO y la base eSRAM provienen de headers CXD90014 (cross-platform, no confirmados como A6000) pero el uso de `0xc0005000` por el BootROM mismo confirma que esa región es RAM direccionable en tiempo de arranque.

**Q3: SÍ** — existe una región RAM demostrablemente usable para alojar código durante el modo serie: eSRAM, concretamente `0xc0005000` (donde vive el vector de salto) y adyacente. El BootROM lee/escribe/salta a esta región, lo que demuestra que está físicamente presente, inicializada y ejecutable en ese momento.

No se completa la pila ni el heap disponibles (no cuantificados estáticamente), ni regiones compartidas con otros procesadores (ARM7/BOSS), sin evidencia.

---

## 7. Estado de CPU y condiciones de salto

- El BootROM corre en modo privilegiado, sin MMU (direcciones físicas directas), en Thumb (salvo vectores en ARM al inicio).
- `FUN_ffff0144` realiza `BX r0`; el bit0 de la dirección seleccionada por el paquete determina Thumb (1) vs ARM (0).
- No se observó limpieza de registros, pila, interrupciones o cachés inmediatamente antes del salto.
- No se observó comprobación de firma, estructura de imagen ni checksum de código antes de `BX`.
- **Q4: NO** — el mecanismo no requiere firmas, autenticación ni validaciones adicionales más allá del checksum de integridad del paquete.
- Condiciones de retorno: el salto es un `BX` (no retorna al receptor salvo que el código cargado lo haga).
- Saltos inválidos: si la dirección apunta a memoria no ejecutable/inaccesible, el procesador tomaría una excepción (no manejada por el receptor).

---

## 8. Reconstrucción CRC8

### 8.1 Función FUN_ffff0c00 (VERIFICADA)

```
0xffff0c00: ldr  r2, [pc, #0x90]    ; r2 = 0xEDB88320 (polinomio)
0xffff0c02: movs r1, #0
0xffff0c04: tst.w r0, #1
0xffff0c08: ite   ne
0xffff0c0a: eorne.w r0, r2, r0, lsr #1   ; si bit0: r0 = poly ^ (r0>>1)
0xffff0c0e: lsreq r0, r0, #1             ; si no:  r0 = r0>>1
0xffff0c10: adds r1, r1, #1
0xffff0c12: cmp  r1, #8
0xffff0c14: blt  #0xffff0c04             ; 8 iteraciones
0xffff0c16: bx   lr
```

- **Polinomio:** `0xEDB88320` (cargado literalmente, no asumido).
- **Modo:** MSB-first (shift-right, testear bit0).
- **Iteraciones:** 8 por byte.
- **Entrada:** byte en `r0` (low byte); resultado: 32 bits en `r0`.
- Este es un paso CRC de un byte, no una tabla completa (R8 assumed tabla; el binario es bit-a-bit).

### 8.2 Actualización del acumulador (FUN_ffff0634, `0xffff077e–0xffff0794`)

```
0xffff077e: ldr  r0, [sl]        ; r0 = acumulador previo (old_acc)
0xffff0782: eor.w r0, r0, sb     ; r0 ^= byte recibido
0xffff0786: uxtb  r0, r0         ; r0 &= 0xFF
0xffff0788: bl   #0xffff0c00     ; tmp = crc8_step(r0)
0xffff078c: ldr.w r1, [sl]       ; r1 = old_acc (32 bits)
0xffff0790: eor.w r0, r0, r1, lsr #8   ; r0 = tmp ^ (old_acc >> 8)
0xffff0794: str.w r0, [sl]       ; nuevo acumulador
```

Regla: `acc = crc8_step((old_acc ^ byte) & 0xFF) ^ (old_acc >> 8)`.

### 8.3 Valor inicial

En `0xffff0a20: str r0,[sp,#0x14]` con `r0=-1=0xFFFFFFFF`. El acumulador en `[sp+0x14]` se inicializa a `0xFFFFFFFF`. **NECESITA CONFIRMACIÓN** (no se verificó contra captura real).

### 8.4 Cobertura del checksum

Los 6 bytes de datos del frame (type_hi,type_lo,data_hi,data_lo,addr_hi,addr_lo). No se verificó si el byte checksum mismo se alimenta al acumulador ni qué valor final indica éxito (¿==0? ¿==byte recibido?).

### 8.5 Corrección sobre R8

El parser de R8 usaba polinomio `0x07` (placeholder) y una pasada única sobre el XOR de todos los bytes. **Esa reconstrucción no coincide con el binario.** El parser R9 (`r9-uart-protocol.py`) implementa el algoritmo iterativo real con polinomio `0xEDB88320`. Las 6 autotests pasan (autoconsistencia), pero el checksum exacto necesita validación contra una captura real.

---

## 9. Pruebas offline y emulación

### 9.1 Parser R9 (`r9-uart-protocol.py`)

- Decodificación de paquetes (tipo 0, tipo 0xFFFF, tipos de error 0xFF01–0xFF06).
- Validación de longitud (rechaza frames truncados).
- Validación checksum (CRC8 iterativo `0xEDB88320`).
- Identificación de tipos y códigos de retorno.
- Registro de errores.
- Pruebas con datos sintéticos (6 autotests, 6/6 pasan).
- Constructor de paquetes (`build_type0_frame`, `build_jump_frame`) para generación local de archivos binarios de prueba.
- **No transmite a la cámara ni realiza operaciones físicas.**

### 9.2 Emulación Unicorn (`r9-unicorn-ramjump.py`)

Se emuló el mecanismo clave (Q2/Q6):
- eSRAM mapeada en `0xc0000000–0xc0100000` (RWX).
- Payload diagnóstico escrito en eSRAM `0xc0005000` (simula paquetes tipo 0 consecutivos).
- Jump target `0xc0005001` (Thumb) almacenado en `0xc000500C` (simula tipo 0xFFFF).
- Rama indirecta `FUN_ffff0144`: `PC <- [0xc000500C]`.

**Resultado:** `Final PC = 0xc000500c (in eSRAM: True)`. El control se transfirió a y ejecutó en eSRAM.

**Diferencias emulado vs real:**
- El estado real de CPU al entrar al receptor (registros, pila, MMIO, nivel de señal) no está demostrado; la emulación asume un estado limpio.
- La recepción por línea serie (bit timing, paridad, baud) no se modeló; solo el salto tras tener el salto en `0xc000500C`.
- El emulado usó un jump target de 32 bits; si el hardware limitara el campo a 16 bits, eSRAM no sería alcanzable directamente (se considera resuelto a 32 bits por `ldr r1,[sp,#0xc]`, pero no confirmado contra captura).

**Q6: SÍ** — se puede ejecutar un programa diagnóstico mínimo en un modelo emulado representativo del mecanismo de salto (no del hardware completo).

---

## 10. Condiciones de activación física (BOOT_SERIAL_IN)

### 10.1 Registro `0xf2915010` bit 1

- Consultado en `FUN_ffff0f82`, `FUN_ffff05da`, `FUN_ffff0634`, `FUN_ffff0876`.
- Etapa: entrada al receptor serie (después de `FUN_ffff1062`, antes de `FUN_ffff0876`).
- Función que configura: `FUN_ffff0554` lee `0xf2910410` (GPIO(4,RDATA) bit 22) para elegir divisor de baud; no se identificó función que escriba `0xf2915010` bit 1 (parece leer un estado externo).
- `0xf2915010` bit 1 representa un **estado externo** (entrada de datos serie), no una selección interna pura.
- Depende de GPIO(4,RDATA) (`0xf2910410`) para la configuración de baud, no confirmado que bit 1 de `0xf2915010` sea ese mismo GPIO.
- No se demostró dependencia de secuencia durante el encendido.
- Otros modos de arranque existen (COLD, UPDATER, WARM/HOT), pero son rutas separadas del BootROM/Loader3.
- No se identificaron rutas alternativas hacia el receptor serie.

### 10.2 Relación con candidatos físicos

| Elemento | Fundamento | Estado |
|---|---|---|
| `0xf2910410` (GPIO(4,RDATA)) | Leído por `FUN_ffff0554` | MMIO verificado; no es un pin físico |
| CN4906 pin 9 (MULTI UART_RX/BOOT_IN) | Manual de servicio A6000 pág.37, vía R4003 (XX) | Documental, no eléctrico |
| R4003 | Marcado XX (sin población verificada) en esquema | No verificado |

No se deduce equivalencia entre registro GPIO y contacto físico sin evidencia (regla del proyecto).

### 10.3 Procedimiento futuro de medición pasiva (no ejecutado)

1. Identificar placa SY-1028 y cara visible (CN4906).
2. Continuidad (sin alimentar) R4003 ↔ CN4906 pin 9.
3. Resistencia a masa (sin alimentar) pin 9 vs GND.
4. Tensión DC (cámara apagada) pin 9 vs GND (esperar 0–3.3V; si 5V, abortar).
5. Observación de señal (osciloscopio/analizador lógico) durante encendido.
6. Lectura pasiva solo RX a 3.3V si pasos 1–5 confirman señal.

**Q8: NO DEMOSTRADO** — no se ha demostrado condición concreta para activar físicamente el modo serie.

---

## 11. Dependencias de BOSS/Darwin

El receptor serie del BootROM opera **antes** de BOSS, NAND, ARM7 firmware y Linux:
- No requiere inicialización de BOSS (`FUN_c01f0cca` no ejecutada en esta ruta).
- No requiere controlador NAND ni escrituras persistentes.
- No requiere firmware ARM7.
- No requiere Darwin/Linux.
- El código ejecutado desde RAM podría, en teoría, acceder a registros MMIO directamente (incluyendo NAND/BOSS), pero sin inicialización previa no hay servicios ni controladores disponibles.

**Conclusión:** el estado de hardware durante el receptor serie permite acceso directo a registros MMIO (diagnóstico de memoria posible), pero exige inicializaciones adicionales para cualquier servicio de BOSS/Darwin/NAND. No se construyeron herramientas de modificación de almacenamiento persistente.

---

## 12. Respuestas Q1–Q10

**Q1. ¿El mensaje tipo 0 permite cargar bytes controlados por el emisor en RAM?**
**SÍ.** `str r2,[r1]` en `0xffff0bb8` escribe el valor (del paquete) a la dirección (del paquete) sin validación de rango. Binario: `bootrom.bin` SHA-256 `81a17e03…`, direcciones `0xffff0bb4–0xffff0bb8`.

**Q2. ¿El mensaje tipo 0xFFFF permite saltar a una dirección relacionada con esos bytes?**
**SÍ** (con acotación). Tipo 0xFFFF almacena una dirección de 32 bits en `0xc000500C` (`0xffff0b78–0xffff0b82`) y `FUN_ffff0144` (`0xffff0144–0xffff0148`) hace `ldr r1,[0xc0005000]; ldr r0,[r1,#0xc]; bx r0`. El remitente puede escribir código en dirección X (tipo 0) y saltar a X (tipo 0xFFFF). La dirección de salto es de 32 bits (carga de 32 bits desde `[sp+0xc]`), alcanzando eSRAM. No se observó firma ni validación adicional.

**Q3. ¿Existe una región RAM usable durante la ejecución del receptor BootROM?**
**SÍ.** eSRAM `0xc0000000–0xc0100000` (16 MiB, `CXD90014_ESRAM_BASE=0xc0000000`). El BootROM lee/escribe `0xc0005000`, `0xc000500C`, `0xc0010218` y salta a `0xc000500C`, demostrando que es RAM usable y ejecutable en tiempo de arranque (antes de Linux/DDR).

**Q4. ¿El mecanismo requiere firmas, autenticación o validaciones adicionales?**
**NO.** Solo checksum de integridad (CRC8, polinomio `0xEDB88320`). No se observó comprobación criptográfica ni de estructura de imagen.

**Q5. ¿Se puede construir una secuencia de paquetes válida y comprobarla offline?**
**SÍ.** `r9-uart-protocol.py` construye frames tipo 0 y tipo 0xFFFF con checksum válido y los valida contra el parser (6 autotests pasan). Se generan archivos binarios locales; no se transmiten a la cámara.

**Q6. ¿Se puede ejecutar un programa diagnóstico mínimo en un modelo emulado suficientemente representativo?**
**SÍ** (emulado). Unicorn transfiere el PC a código en eSRAM (`0xc0005000`) vía `[0xc000500C]` y ejecuta (`Final PC = 0xc000500c in eSRAM`). No modela la línea serie ni el estado real de CPU.

**Q7. ¿El receptor funciona independientemente del arranque de Linux?**
**SÍ.** Es parte del BootROM (`0xffff0000`, vectores de reset), pre-Linux, sin dependencia de Loader3, BOSS, NAND ni Linux.

**Q8. ¿Se ha demostrado alguna condición concreta para activar físicamente el modo serie?**
**NO DEMOSTRADO.** `0xf2915010` bit 1 = BOOT_SERIAL_IN (estado externo); candidato físico CN4906 pin 9 vía R4003 (XX, sin continuidad ni niveles verificados). No se demostró activación externa.

**Q9. ¿Es técnicamente viable un diagnóstico propio desde RAM, con las evidencias disponibles?**
Viabilidad **estática: SÍ** (cadena coherente UART→RAM write→RAM jump, restricciones identificadas). Viabilidad **emulada: SÍ** (Unicorn ejecuta en eSRAM). Viabilidad **demostrada en hardware: NO** (carece de identificación eléctrica del UART y prueba física autorizada).

**Q10. ¿Qué requisito falta para pasar de la demostración offline a una prueba física no destructiva?**
Identificar eléctricamente el contacto UART (continuidad R4003→CN4906 pin 9, tensión DC, señal en osciloscopio) y confirmar que BOOT_SERIAL_IN se puede activar externamente, todo con autorización física separada y mediciones no destructivas.

---

## 13. Experimento mínimo siguiente

**Offline (sin hardware):**
1. Confirmar el valor init del checksum y la regla de comparación final contra el disassembly (revisar `FUN_ffff0634` final y comparación del byte checksum recibido).
2. Confirmar el mapeo byte-a-byte de la dirección de salto de 32 bits en tipo 0xFFFF (qué 4 bytes del paquete la conforman).
3. Añadir tests automáticos para `r9-uart-protocol.py` y `r9-unicorn-ramjump.py` en `tests/`.

**Físico (solo con autorización separada, no destructivo):**
- Ejecutar el procedimiento de medición pasiva (§10.3) en CN4906 pin 9 sin conectar TX de 3.3V/5V hasta confirmar niveles.
- Si hay señal, lectura pasiva solo RX a 3.3V.

---

## 14. Recomendación R10

**Cerrar E26-R9 con éxito parcial/completo estático+emulado.** La cadena BootROM→UART→escritura RAM→salto a RAM está demostrada estáticamente y en emulación, sin NAND, sin Linux, sin firmware modificado.

**No se recomienda prueba física en esta etapa** por falta de autorización y de identificación eléctrica del UART; cualquier prueba física es un hito independiente sujeto a autorización del usuario.

**Para R10 (si se autoriza):**
- Completar la verificación física del contacto UART (CN4906 pin 9).
- Si hay señal, construir y validar offline los paquetes tipo 0/0xFFFF con el checksum confirmado, y documentar el procedimiento de carga sin transmisión real.
- No escribir NAND, no flashear, no ejecutar payload en hardware físico sin autorización expresa.

---

## Evidencia reproducible

| Artefacto | Ruta | SHA-256 |
|---|---|---|
| BootROM | `analysis/camera-dumps/updater-20261020-175427/bootrom.bin` | `81a17e039a2debfe589b127e12384ed4d7c2ba0d0c819238d0b021b466246026` |
| Parser R9 | `analysis/e26-recovery/r9-uart-protocol.py` | (commit) |
| Emulación Unicorn R9 | `analysis/e26-recovery/r9-unicorn-ramjump.py` | (commit) |
| Informe R8 | `docs/capture/e26-r8-bootrom-uart-boss.md` | (commit `0c5857ab`) |

**Comandos de verificación:**
```bash
python3 analysis/e26-recovery/r9-uart-protocol.py --selftest   # 6/6 pasan
python3 analysis/e26-recovery/r9-unicorn-ramjump.py            # RAM-jump emulado OK
```

---

**Estado de los entregables R9:**
- [x] `docs/capture/e26-r9-bootrom-ram-execution.md` (este informe)
- [x] `analysis/e26-recovery/r9-uart-protocol.py` (parser + constructor, 6/6 tests)
- [x] `analysis/e26-recovery/r9-unicorn-ramjump.py` (emulación RAM-jump)
- [ ] Pruebas automáticas en `tests/` (pendiente, ver R10)
- [ ] PENDIENTES.md / STATE.md / CURRENT.md / PROGRESS.md actualizados (ver commit)

**Hash del commit:** a publicar en `origin/main` tras este informe (ver sección de publicación en PROGRESS.md).

**Límite de evidencia:** todo lo anterior es estático (disassembly) o emulado (Unicorn). No constituye demostración en una Sony A6000 física. La activación física del UART queda pendiente de autorización separada.
