# E26-R10 — Ingeniería inversa del Sony USB Charger como ruta de recuperación de la Sony a6000

**Fecha:** 29-10-2026
**Repositorio:** `sony-a6000-electronic-shutter`
**Alcance:** Exclusivamente offline. Ingeniería inversa de binarios de firmware, análisis de descriptores USB, validación con scripts. No se conectó, encendió, depuró ni modificó la cámara. No se enviaron comandos experimentales al hardware físico.

---

## 1. Resumen ejecutivo

Se investigó exhaustivamente si la interfaz USB `054c:0994` (identificada por `lsusb` como `Sony Corp. ILCE-6000` / `ILCE-6000 in charging mode`) puede aprovecharse como ruta de recuperación de la Sony a6000 bloqueada tras la instalación del firmware 3.25, evitando una intervención física UART.

**Conclusión principal:** El componente que genera `054c:0994` ha sido identificado con evidencia de binario: **Darwin**, el microcontrolador FM3 que gestiona la energía y arranca con la cámara apagada. Su firmware `darwin_core.bin` contiene el descriptor USB completo (VID `0x054c`, PID `0x0994`, clase HID, endpoint EP1 IN interrupt de 8 bytes, cadenas "Sony" y "USB Charger") que coincide exactamente con el observado en la cámara física mediante `lsusb -v`.

Sin embargo, **no se encontró evidencia de que el USB Charger permita recuperación**. La interfaz HID declara únicamente un informe Input de 1 byte (sin informes Output ni Feature), no se identificaron manejadores de solicitudes de control (SETUP) ni peticiones específicas del fabricante, y no existe una cadena demostrada desde USB Charger hasta escritura de RAM, salto a ejecución, o activación de Updater Mode.

La única ruta de recuperación con evidencia estática y emulada sigue siendo **BootROM → UART → escritura RAM → salto a RAM** (E26-R9), pendiente de identificación física del contacto UART (CN4906 pin 9 vía R4003, sin continuidad verificada).

**Decisión de cierre: Opción B** — abandonar provisionalmente la ruta USB Charger y concentrar la recuperación en BootROM UART de R9. El módulo DWN de Darwin (tabla de salto de ~20 comandos) se registra como pista futura no demostrada.

---

## 2. Evidencia física ya disponible

Las observaciones siguientes provienen de pruebas físicas realizadas por el propietario (documentadas en E26-R10 §3) y no se reinterpretan como prueba de daño NAND, fallo de BIONZ ni fallo de Darwin:

| Observación | Detalle |
|---|---|
| Firmware original funcional | 3.23 |
| Firmware instalado antes del bloqueo | 3.25 |
| Actualizador mostró | 100 % y Done |
| Estado tras actualización | No arranca; pantalla negra; LED rojo inferior: 3 parpadeos lentos + 2 rápidos, repetidamente |
| Cámara apagada + USB | Linux detecta `054c:0994` Sony USB Charger |
| Al encender | El dispositivo USB desaparece; no se enumera otro dispositivo |
| Al apagar de nuevo | El dispositivo de carga no reaparece |
| Reinstalar batería | USB Charger vuelve a enumerarse |

**Descriptor USB completo observado** (`lsusb -v -d 054c:0994`, E26-R10 §3.2):

```
Negotiated speed: Full Speed (12Mbps)
idVendor  0x054c Sony Corp.
idProduct 0x0994
bcdUSB    2.00
bDeviceClass 0
bMaxPacketSize0 64
bNumConfigurations 1
Configuration: bNumInterfaces 1, bmAttributes 0x80, MaxPower 500mA
Interface: bInterfaceClass 3 (HID), bInterfaceSubClass 0, bInterfaceProtocol 0, bNumEndpoints 1
HID: bcdHID 1.11, wDescriptorLength 19
Endpoint: bEndpointAddress 0x81 EP1 IN, Interrupt, wMaxPacketSize 8, bInterval 1
```

**Descriptor HID extraído físicamente** (`/sys/bus/hid/devices/.../report_descriptor`):

```
05 01 09 00 a1 01 09 00 15 00 25 01 75 08 95 01 81 02 c0
```

Interpretación: Generic Desktop, Usage Undefined, Collection Application, Logical Min 0 / Max 1, Report Size 8 bits, Report Count 1, Input Data Variable Absolute, End Collection. **Informe Input de 1 byte. No declara informes Output ni Feature.**

EP0 existe para solicitudes de control USB independientemente de los endpoints declarados; la ausencia de endpoint OUT adicional no descarta peticiones específicas del fabricante en EP0.

**Captura pasiva de informes** (`/dev/hidraw6`): dispositivo abrible; en dos capturas de 10 s no se recibieron informes; una captura devolvió `Input/output error` confirmado por el propietario como causado por desconexión física de la cámara. No clasificado como fallo espontáneo de hardware.

**Comportamiento al encender:** Linux registra `USB disconnect`; después no aparece nueva enumeración. La investigación debe concentrarse en la interfaz que responde mientras la cámara está apagada.

---

## 3. Decodificación USB/HID

### 3.1 Descriptor USB completo en `darwin_core.bin`

Se localizó en `firmware/extracted/fw321/firmware.tar_unpacked/0640_darwin/darwin_core.bin` (SHA-256 `5f2be06d9885d154e8e0df46a611d6830d29754b4353f6e82cecfe66dd6a0bf4`, 157 276 bytes, binario ARM Cortex-M crudo con tabla de vectores en el offset 0) un descriptor USB Device en el offset de archivo `0x0239e4`, con el par VID/PID `4c 05 94 09` en `0x0239ec`.

**Validación offline:** el script `analysis/e26-recovery/r10-usb-descriptor-parse.py` recorre los descriptores a partir de ese offset y verifica cada campo contra el observado por `lsusb -v`. Las 4 pruebas unitarias de `tests/test_e26_r10_usb_charger.py` pasan.

| Campo | Observado (cámara) | Encontrado en `darwin_core.bin` | Coincide |
|---|---|---|---|
| bcdUSB | 2.00 | 0x0200 | SÍ |
| bDeviceClass | 0 | 0 | SÍ |
| bDeviceSubClass | 0 | 0 | SÍ |
| bDeviceProtocol | 0 | 0 | SÍ |
| bMaxPacketSize0 | 64 | 0x40 | SÍ |
| idVendor | 0x054c | 0x054c | SÍ |
| idProduct | 0x0994 | 0x0994 | SÍ |
| bcdDevice | — | 0x0100 | — |
| bNumConfigurations | 1 | 1 | SÍ |
| bConfigurationValue | — | 1 | — |
| bmAttributes | 0x80 | 0x80 | SÍ |
| MaxPower | 500 mA | 0xfa × 2 mA | SÍ |
| bInterfaceClass | 3 (HID) | 3 | SÍ |
| bInterfaceSubClass | 0 | 0 | SÍ |
| bInterfaceProtocol | 0 | 0 | SÍ |
| bNumEndpoints | 1 | 1 | SÍ |
| bcdHID | 1.11 | 0x0111 | SÍ |
| wDescriptorLength | 19 | 0x0013 | SÍ |
| Endpoint address | 0x81 IN | 0x81 | SÍ |
| Endpoint type | Interrupt | 0x03 | SÍ |
| wMaxPacketSize | 8 | 8 | SÍ |
| bInterval | 1 | 1 | SÍ |
| Cadena manufacturer | — | "Sony" | SÍ |
| Cadena product | — | "USB Charger" | SÍ |

La base de datos `usb.ids` del sistema confirma `054c:0994 = ILCE-6000 (aka Alpha-6000) in charging mode`.

### 3.2 Limitaciones del protocolo HID declarado

- **Un solo informe Input de 1 byte.** No hay informe Output ni Feature declarado.
- **EP1 IN, Interrupt, 8 bytes, intervalo 1 ms.** Dirección dispositivo → host solamente.
- **EP0 (solicitudes de control)** existe pero su despachador no fue identificado en el binario (ver §5).

Consecuencia: por la vía HID convencional **no existe un canal declarado host → dispositivo** para enviar comandos o bloques de datos. Cualquier comunicación host → dispositivo tendría que ir por EP0 (peticiones estándar o específicas del fabricante), cuyo manejador no fue localizado.

---

## 4. Arquitectura y mapa del controlador

### 4.1 ¿Qué componente genera `054c:0994`?

**Darwin (microcontrolador FM3 / MB9AF004B family).** Evidencia:

1. El descriptor USB con VID `0x054c` y PID `0x0994` reside en `darwin_core.bin`, el firmware de Darwin.
2. `darwin_core.bin` contiene la pila USB Function: strings `USBF_Init`, `USBF_CONNECT`, `USBF_Attach`, `USBF_UnAttach`, `USBF_Init error`, `USBF_CONNECT error`, `USBF_Attach error`.
3. Contiene strings de detección de cargador USB: `SONY Charger Detected.`, `APPLE Charger(1.0A) Detected.`, `APPLE Charger(2.0A) Detected.`, `Unknwon Charger Detected.[%d]`, `nBAPPLE Charger(0.5A) Detected.`.
4. Contiene strings de gestión de potencia USB: `USB type:%d`, `USB PWR`, `USB Boost(%d)`, `USB Unboost`, `USB %02X PWR %02X`, `[BGL]USB %02X PWR %02X`, `[ERR]BST USB:%d`, `USB BC DCD TimeOut`, `USB BC Retry[%d]`.
5. Contiene `power key: usb event detect!! event:0x%02x` y `power key: usb boot event edge:0x%02x` — detección de evento de arranque por USB.
6. Contiene `IHid` — interfaz HID.
7. Contiene `sio_err[mss-sync]:%x` y `sio_err[mss-async]:%x` — comunicación SIO/MSS (posible canal Darwin → BIONZ).
8. Contiene `DWN_VER0.78` seguido de una tabla de salto de ~20 punteros de función (ver §4.3).

### 4.2 Firmware propio y accesibilidad

- **¿Tiene firmware propio?** Sí: `darwin_core.bin` (157 276 bytes), firmware del microcontrolador FM3/Darwin.
- **¿Es accesible en volcados existentes?** Sí. `darwin_core.bin` está en `firmware/extracted/fw321/firmware.tar_unpacked/0640_darwin/darwin_core.bin`, extraído de la partición `0640_darwin` del FDAT oficial 3.21. SHA-256 verificado en `firmware/hashes/sha256.json`.
- **¿Tiene comunicación física o lógica con BIONZ o Darwin?** Darwin **es** el componente del USB Charger. Existe comunicación SIO/MSS de Darwin que probablemente va a BIONZ (Darwin controla las señales de alimentación `DD_ON1/2/3` hacia BIONZ, documentado en E24-01 y el esquema SY-1028 PDF 23). Sin embargo, no se rastreó una ruta específica de datos desde el USB Charger hasta BIONZ.

### 4.3 Mapa del módulo DWN (descarga)

En `darwin_core.bin`, en el offset `0x021938` aparece la cadena `DWN_VER0.78`, seguida de `131115_2` (posible fecha/build) y luego una **tabla de salto de 20 punteros de función Thumb** (offsets `0x021950` en adelante):

```
0x7151, 0x72c3, 0x730f, 0x7329, 0x73cd, 0x747b, 0x7543, 0x755d,
0x75f1, 0x76cf, 0x7715, 0x772f, 0x8045, 0x80c3, 0x817d, 0x8197,
0x8235, 0x8909, 0x8c29, 0x8c43
```

"DWN" probablemente significa "Download". Esta tabla es candidata a ser un despachador de comandos de un protocolo de descarga/actualización. **No se identificó el código de despacho que usa esta tabla** (se accede por direccionamiento relativo al PC, no por literales absolutos en el código examinado), ni se demostró que sea accesible a través de la interfaz USB Charger `054c:0994`.

### 4.4 ¿Qué ocurre al encender? (desconexión USB)

No se identificó en el binario si la desconexión al encender corresponde a una conmutación de hardware (multiplexor USB `IC5600`), una orden de firmware, o ambas. Lo que se sabe por la evidencia física:

1. Cámara apagada + USB → Darwin ejecuta y enumera como USB Charger (`054c:0994`).
2. Al encender → BIONZ Linux arranca y toma el control del USB; el dispositivo `054c:0994` desaparece.
3. Al apagar de nuevo → el USB Charger no reaparece automáticamente; es necesario reinstalar la batería.

Esto indica que Darwin gestiona el USB mientras la cámara está apagada, pero no re-enumerada al apagarse; requiere un ciclo de batería. El mecanismo exacto de transferencia de control USB de Darwin a BIONZ no está documentado en el binario examinado.

### 4.5 Modos USB de la A6000

Según `docs/research/docs/01-overview.md` del repositorio:

| Modo | VID:PID | Protocolo | Estado de cámara |
|---|---|---|---|
| Normal | `054c:07c4` | MSC/PTP | Cámara encendida (BIONZ Linux) |
| Updater | `054c:03e2` | — | Modo actualizador |
| Charging | `054c:0994` | HID (solo Input) | Cámara apagada (Darwin) |

`054c:0994` es un modo USB **separado** de normal (`07c4`) y updater (`03e2`).

---

## 5. Investigación de protocolos y solicitudes

### 5.1 Solicitudes HID de clase

La interfaz HID declara únicamente:
- Informe Input: 1 byte, Logical Min 0 / Max 1.
- **No declara informes Output ni Feature.**

Por tanto, no hay `SET_REPORT` ni `GET_REPORT` para informes Output/Feature. `GET_REPORT` para el informe Input es teóricamente posible por EP0, pero es dispositivo → host (solo 1 byte), inútil para enviar comandos al dispositivo.

### 5.2 Solicitudes estándar USB

Las solicitudes estándar (GET_DESCRIPTOR, SET_ADDRESS, GET_CONFIGURATION, SET_CONFIGURATION, GET_STATUS, CLEAR_FEATURE, SET_FEATURE, GET_INTERFACE, SET_INTERFACE, SYNCH_FRAME) se esperan para la enumeración básica. No se verificó su implementación en `darwin_core.bin`.

### 5.3 Solicitudes específicas del fabricante (vendor requests)

**No se identificaron.** Se buscó en `darwin_core.bin`:
- Manejadores de SETUP / despachador de control endpoint: **no localizado**.
- Peticiones vendor-specific con IDs de Sony: **no encontradas**.
- `CMD_SWITCH_MODE = 0x30` del protocolo Sony-PMCA-RE: **pertenece a una interfaz USB distinta** (`054c:07c4` normal / `054c:03e2` updater, cámara encendida), no a `054c:0994`. No hay relación técnicamente demostrada con el USB Charger.

### 5.4 Rutas por EP0

EP0 existe para solicitudes de control, pero sin el manejador identificado no se puede afirmar que acepte peticiones beyond las estándar de enumeración. No se descartó su existencia (ausencia de evidencia ≠ evidencia de ausencia), pero no hay implementación verificable.

### 5.5 Diferencias entre descriptores declarados y funciones internas

El descriptor declara HID con solo informe Input. Internamente, Darwin tiene:
- Pila USB Function (USBF_Init/Attach/Connect/UnAttach).
- Detección de cargador USB (BC DCD).
- Módulo DWN con tabla de salto de 20 comandos.
- SIO/MSS (comunicación inter-procesador).
- IHid (interfaz HID).

No se demostró que ninguna de estas funciones internas sea alcanzable a través de la interfaz USB Charger enumerada.

---

## 6. Comparación con Sony-PMCA-RE

`CMD_SWITCH_MODE = 0x30` (en `references/pmca/pmca/usb/sony.py:425`) es parte del protocolo PMCA que el actualizador oficial usa sobre la interfaz USB normal de la cámara (`054c:07c4` MSC/PTP o `054c:03e2` updater), cuando la cámara está **encendida** y ejecutando Linux/BIONZ. El flujo es:

```
CMD_INIT (0x1) → CMD_CHK_GUARD (0x10) → CMD_QUERY_VERSION (0x20)
→ CMD_SWITCH_MODE (0x30) → CMD_WRITE_FIRM (0x40) → CMD_COMPLETE (0x100)
```

Diferencias clave con `054c:0994`:

| Aspecto | PMCA (CMD_SWITCH_MODE) | USB Charger `054c:0994` |
|---|---|---|
| Interfaz USB | `054c:07c4` / `054c:03e2` | `054c:0994` |
| Estado cámara | Encendida (Linux/BIONZ) | Apagada (Darwin) |
| Controlador | BIONZ / libupdaterbody | Darwin (FM3) |
| Protocolo | PMCA (tramas 0x80 B + CRC-16) | HID (solo Input 1 byte) + EP0 no identificado |
| Switch de modo | Demostrado en binario del actualizador | No identificado |

**No se asumió compatibilidad por compartir fabricante.** No hay evidencia técnica que vincule `CMD_SWITCH_MODE = 0x30` con `054c:0994`.

---

## 7. Análisis de la posibilidad de alcanzar Updater Mode

### Rutas evaluadas

**Ruta 1 — HID convencional:** Descartada. No hay informe Output ni Feature declarado; no hay canal host → dispositivo.

**Ruta 2 — EP0:** No demostrada. No se identificó el manejador de solicitudes de control en `darwin_core.bin`. No se sabe si EP0 acepta peticiones vendor-specific.

**Ruta 3 — Comunicación entre procesadores:** Darwin tiene SIO/MSS (probable canal Darwin → BIONZ) y controla `DD_ON1/2/3` (alimentación de BIONZ). Pero no se demostró una ruta de datos desde el USB Charger hasta BIONz, ni que un comando USB pueda solicitar el encendido del procesador principal o un reinicio de BIONZ.

**Ruta 4 — Cambio de modo:** No demostrada. El módulo DWN existe (tabla de salto de 20 comandos) pero no se identificó su interfaz de acceso ni se demostró que pueda seleccionar una ruta de arranque o activar Updater Mode. No hay equivalente a `CMD_SWITCH_MODE` en el USB Charger.

**Ruta 5 — Transferencia a RAM:** No demostrada. A diferencia de BootROM UART (R9) que tiene paquete tipo 0 (`str(valor,[dirección])`, escritura RAM arbitraria) y tipo 0xFFFF (salto a dirección en `0xc000500C`), el USB Charger no tiene ningún mecanismo identificado de escritura a RAM ni transferencia de ejecución.

### Conclusión

**No existe una cadena demostrada para activar Updater Mode desde la interfaz USB Charger `054c:0994`.** Q6 = NO.

---

## 8. Análisis de ejecución de código desde USB

### Evaluación por ruta

**Ruta 1 — HID convencional:** No existe informe declarado que admita datos enviados desde el host (sin Output ni Feature). **No viable.**

**Ruta 2 — EP0:** No se documentó un manejador de solicitudes USB que permita enviar comandos o bloques de datos. **No viable (sin evidencia).**

**Ruta 3 — Comunicación entre procesadores:** Darwin puede comunicarse con BIONZ vía SIO/MSS, pero no se demostró que el USB Charger pueda iniciar dicha comunicación ni solicitar acciones a BIONZ. **No viable (sin evidencia).**

**Ruta 4 — Cambio de modo:** No se demostró que el USB Charger pueda provocar una nueva enumeración USB compatible con una herramienta de actualización (`054c:03e2` updater). **No viable (sin evidencia).**

**Ruta 5 — Transferencia a RAM:** No existe cadena verificable desde una solicitud USB hasta una escritura de RAM y una transferencia de ejecución. A diferencia de R9 (BootROM UART con tipo 0 y tipo 0xFFFF demostrados estáticamente y en emulación), el USB Charger no tiene equivalente identificado. **No viable.**

### Precondiciones, límites y pruebas

Para cualquiera de estas rutas sería necesario, como mínimo:
1. Identificar el manejador de SETEP/control endpoint en `darwin_core.bin` (no localizado).
2. Identificar peticiones vendor-specific con IDs de Sony (no encontradas).
3. Demostrar que el módulo DWN es accesible vía USB (no demostrado).
4. Demostrar una ruta de datos USB Charger → BIONZ o RAM (no demostrada).

No se consideró la enumeración USB ni la mera recepción de datos como evidencia de ejecución de código.

---

## 9. Rutas descartadas con sus fundamentos

| Ruta descartada | Fundamento |
|---|---|
| HID Output/Feature para enviar comandos | No declarado en el descriptor HID (solo Input de 1 byte). Verificado en `darwin_core.bin` y `lsusb -v`. |
| `CMD_SWITCH_MODE = 0x30` (PMCA) sobre `054c:0994` | Pertenece a interfaz USB distinta (`07c4`/`03e2`, cámara encendida). No hay relación demostrada con `0994`. |
| Escritura de RAM vía USB Charger | No hay equivalente al paquete tipo 0 de BootROM UART (R9). No identificado en `darwin_core.bin`. |
| Salto a ejecución vía USB Charger | No hay equivalente al paquete tipo 0xFFFF de BootROM UART. No identificado. |
| Activación de Updater Mode vía USB Charger | No hay mecanismo de cambio de modo identificado. El módulo DWN no se demostró USB-accesible. |
| Escritura selectiva de `nflasha3` vía USB Charger | Las escrituras NAND (MuMin/LLD → ARM7) requieren entorno Linux; Darwin USB Charger opera pre-Linux sin cadena de escritura NAND demostrada (E26-R7/R8). |
| BootROM como generador de `054c:0994` | `bootrom.bin` (SHA `81a17e03…`) no contiene `0x0994` ni `0x054c` (búsqueda negativa verificada). |

---

## 10. Rutas viables o candidatas con sus limitaciones

### Ruta candidata: módulo DWN de Darwin

**Evidencia:** `DWN_VER0.78` + tabla de salto de 20 punteros de función en `darwin_core.bin` (`0x021950` en adelante).

**Limitaciones:**
- No se identificó el código de despacho que usa la tabla.
- No se demostró que sea accesible vía USB Charger `054c:0994` (la interfaz es HID solo-Input, sin endpoint OUT).
- No se demostró que permita cambiar a Updater Mode ni escribir RAM.
- Es una pista futura, no una ruta viable demostrada.

### Ruta descartada para este informe: BootROM UART (R9)

**Estado:** Cerrada estáticamente con éxito parcial/completo (R9): escritura RAM arbitraria (tipo 0) y salto a RAM (tipo 0xFFFF) demostrados estáticamente y en emulación Unicorn. **Pendiente:** identificación eléctrica del contacto UART (CN4906 pin 9 vía R4003, sin continuidad verificada; requiere autorización física separada).

Esta sigue siendo la ruta de recuperación con más evidencia, pero fuera del alcance de decisión de E26-R10 (se evalúa en E26-R11).

---

## 11. Riesgos y condiciones de validación

### Riesgos

1. **Falso negativo:** No encontrar un manejador en `darwin_core.bin` no demuestra su inexistencia (binario crudo sin símbolos, dirección de carga incierta, cobertura limitada de REA). Una consulta vacía de REA no prueba ausencia.
2. **Falso positivo:** La presencia del descriptor USB en `darwin_core.bin` demuestra que Darwin *puede* enumerar como USB Charger, pero no que el código se ejecute en la cámara bloqueada ni que acepte peticiones de control.
3. **Riesgo físico:** Cualquier validación física (identificación de pines UART/USB, captura pasiva) requiere autorización separada y mediciones no destructivas. No se propuso ninguna conexión concreta en este informe.

### Condiciones de validación para una prueba futura

Si se encuentra una hipótesis específica que justifique pruebas físicas, se requeriría:
1. Autorización física separada del usuario.
2. Cámara accesible con placa SY-1028 visible.
3. Identificación de la cara visible de la placa (SIDE A: CN4906, IC6000; SIDE B: IC5700, CL5701/CL701/CL703-707).
4. Medición pasiva (sin alimentar): continuidad, resistencia a masa.
5. Medición de tensión DC (cámara apagada): esperar 0-3.3 V; si hay 5 V, abortar.
6. Observación de señal con osciloscopio/analizador lógico durante el encendido.
7. Lectura pasiva solo RX a 3.3 V si los pasos 1-5 confirman señal.

No se permite: conectar 5 V directamente, escribir NAND, flashear firmware, modificar flags de arranque, intervenir físicamente pines, o presentar emulación como éxito sobre hardware.

---

## 12. Matriz de evidencias y referencias

| ID | Evidencia | Tipo | Estado | Ruta |
|---|---|---|---|---|
| E1 | Descriptor USB `054c:0994` en `darwin_core.bin` (offset `0x0239e4`) | Binario | VERIFICADO | `firmware/extracted/fw321/firmware.tar_unpacked/0640_darwin/darwin_core.bin` |
| E2 | Validación de descriptor vs `lsusb -v` (script + 4 tests) | Script | VERIFICADO | `analysis/e26-recovery/r10-usb-descriptor-parse.py`, `tests/test_e26_r10_usb_charger.py` |
| E3 | `usb.ids`: `054c:0994 = ILCE-6000 in charging mode` | Documental | VERIFICADO | Sistema local `/usr/share/hwdata/usb.ids` |
| E4 | Pila USB Function en Darwin (`USBF_Init/Attach/Connect/UnAttach`) | Binario | VERIFICADO | `darwin_core.bin` strings |
| E5 | Detección cargador USB (`SONY Charger Detected`) | Binario | VERIFICADO | `darwin_core.bin` strings |
| E6 | Evento de arranque por USB (`usb boot event edge`) | Binario | VERIFICADO | `darwin_core.bin` strings |
| E7 | Interfaz HID (`IHid`) | Binario | VERIFICADO | `darwin_core.bin` strings |
| E8 | SIO/MSS Darwin (`sio_err[mss-sync/async]`) | Binario | VERIFICADO | `darwin_core.bin` strings |
| E9 | Módulo DWN (`DWN_VER0.78` + tabla de salto 20 punteros) | Binario | PARCIAL (no demostrado USB-accesible) | `darwin_core.bin` offset `0x021938` |
| E10 | `bootrom.bin` sin `0x0994`/`0x054c` | Binario | VERIFICADO (búsqueda negativa) | `analysis/camera-dumps/updater-20261020-175427/bootrom.bin` |
| E11 | `lsusb -v -d 054c:0994` (descriptor físico observado) | Físico | VERIFICADO (propietario) | E26-R10 §3.2 |
| E12 | Descriptor HID físico (`report_descriptor`) | Físico | VERIFICADO (propietario) | E26-R10 §3.3 |
| E13 | `CMD_SWITCH_MODE = 0x30` (PMCA) | Documental | VERIFICADO (pero interfaz distinta) | `references/pmca/pmca/usb/sony.py:425` |
| E14 | Modos USB: `07c4` normal, `03e2` updater, `0994` charging | Documental | VERIFICADO | `docs/research/docs/01-overview.md` |

### Referencias

- E26-R7: `docs/capture/e26-r7-recuperacion-estatica.md`
- E26-R8: `docs/capture/e26-r8-bootrom-uart-boss.md`
- E26-R9: `docs/capture/e26-r9-bootrom-ram-execution.md`
- E26-RECOVERY: `docs/capture/e26-recovery.md`
- E24-01: `docs/capture/e24-01-arranque-recuperacion.md` (Darwin controla `DD_ON1/2/3`)
- E24-02: `docs/capture/e24-02-protocolo-actualizacion-darwin.md`
- Sony-PMCA-RE: `references/pmca/`
- usb.ids: confirmación de `054c:0994`

---

## 13. Preguntas de cierre

| # | Pregunta | Respuesta | Fundamento / prueba que falta |
|---|---|---|---|
| Q1 | ¿Está caracterizada la interfaz HID de `054c:0994`? | **SÍ** | Descriptor completo (device, config, interface, HID, endpoint, strings) verificado contra `lsusb -v` y `darwin_core.bin`. Solo Input de 1 byte, EP1 IN interrupt. |
| Q2 | ¿Se identificó el componente físico que implementa USB Charger? | **SÍ (binario) / NO (físico)** | Componente: Darwin (FM3) vía `darwin_core.bin`. Evidencia de binario confirmada. Identificación física del pin USB D+/D- de Darwin: no hecha. |
| Q3 | ¿Se localizaron los handlers USB correspondientes? | **NO** | Funciones USBF_* y `IHid` localizadas, pero el manejador de SETEP/control endpoint y el despachador de peticiones no se identificaron en `darwin_core.bin`. |
| Q4 | ¿Se encontraron solicitudes propias de Sony documentadas o verificadas en código? | **NO** | `CMD_SWITCH_MODE = 0x30` pertenece a interfaz USB distinta (`07c4`/`03e2`). No se encontraron peticiones vendor-specific de Sony en `darwin_core.bin`. |
| Q5 | ¿Existe comunicación demostrada entre USB Charger y BIONZ/Darwin? | **PARCIAL** | Darwin es el USB Charger. Existe SIO/MSS (probable Darwin→BIONZ) y control de `DD_ON1/2/3`, pero no se demostró una ruta de datos USB Charger → BIONZ. |
| Q6 | ¿Existe una cadena demostrada para activar Updater Mode desde esta interfaz? | **NO** | No hay mecanismo de cambio de modo identificado. El módulo DWN no se demostró USB-accesible ni capaz de cambiar modo. |
| Q7 | ¿Existe una cadena demostrada para transferir y ejecutar código en RAM? | **NO** | No hay equivalente a los paquetes tipo 0 / 0xFFFF de BootROM UART (R9). No identificado en `darwin_core.bin`. |
| Q8 | ¿La interfaz continúa siendo una candidata razonable para recuperación? | **NO DEMOSTRADO / NO** | Sin canal host → dispositivo (HID solo-Input), sin manejador de control identificado, sin ruta a RAM o cambio de modo. |
| Q9 | ¿Qué componente o evidencia falta para decidir su viabilidad? | — | Manejador de SETEP/control endpoint en `darwin_core.bin`; peticiones vendor-specific de Sony; demostración de que DWN es USB-accesible; identificación física del USB D+/D- de Darwin. |
| Q10 | ¿Conviene continuar con USB Charger o priorizar BootROM UART de R9? | **Priorizar BootROM UART (R9)** | R9 tiene cadena demostrada estáticamente y en emulación. USB Charger no tiene host → dispositivo demostrado. Pista futura: módulo DWN de Darwin. |

**Nota:** Cuando la respuesta es NO por falta de evidencia, se indica expresamente que no está demostrado y se identifica la prueba que falta. No se confunde "no encontramos una implementación" con "demostramos su inexistencia".

---

## 14. Recomendación para E26-R11

**Decisión de cierre: Opción B** — Abandonar provisionalmente la ruta USB Charger y concentrar la recuperación en BootROM UART de R9.

**Justificación:**
1. R9 (BootROM → UART → escritura RAM → salto a RAM) tiene una cadena completa demostrada estáticamente y en emulación Unicorn, sin NAND, sin Linux, sin firmware modificado. Q1–Q7 de R9: 6 SÍ, 1 NO (firmas no requeridas), Q8 NO DEMOSTRADO (falta identificación física del UART), Q9 viable estática+emulada.
2. USB Charger `054c:0994` no tiene canal host → dispositivo demostrado (HID solo-Input), sin manejador de control identificado, sin ruta a RAM, sin cambio de modo, sin relación con `CMD_SWITCH_MODE`.
3. La única pista futura de USB Charger es el módulo DWN de Darwin (tabla de salto de 20 comandos), que no se demostró USB-accesible ni capaz de recuperación.

**Próximo paso para E26-R11:** Continuar con la identificación física del contacto UART de BootROM (CN4906 pin 9 vía R4003), mediante mediciones pasivas no destructivas (continuidad, tensión DC, observación de señal con osciloscopio/analizador lógico) sujeto a autorización física separada. Si se confirma señal UART, se pueden construir y validar offline los paquetes tipo 0 / 0xFFFF con el checksum CRC8 confirmado (polinomio `0xEDB88320`).

**Pista futura (no para E26-R11 inmediata):** Si surge evidencia de que el módulo DWN de Darwin es accesible vía USB Charger (EP0 vendor requests), reevaluar la ruta USB Charger como opción C.

---

**Prioridad absoluta del proyecto:** recuperar la a6000 original conservando sus calibraciones y datos, sin introducir nuevos riesgos en el hardware. No se escribió NAND, no se flasheó firmware, no se intervino físicamente la cámara en esta investigación.
