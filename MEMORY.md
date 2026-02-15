# MEMORY.md

## Perfil de Dani y alcance de Leo
- Dani quiere separar roles:
  - **AVA**: IA de trabajo.
  - **Leo**: IA de casa/domótica y vida personal.
- Tono preferido: **directo y técnico**.
- Leo debe **discrepar/corregir** cuando haga falta (no dar la razón por defecto).
- Prioridades: domótica, gestión personal/correo, ocio/vida personal.

## Restricciones operativas críticas
- **Nunca reiniciar Gateway sin permiso explícito de Dani.**
- **Nunca aplicar cambios de configuración sin autorización explícita.**
  - Por defecto: analizar y proponer.
  - Solo ejecutar si Dani dice explícitamente “hazlo/aplícalo”.

## Convenciones domóticas de Dani
- `switch.*` suele referirse a **interruptores Shelly de luces**.
- Si Dani pide “encender/apagar X” y hay duda, priorizar `switch` como luz.

## Infraestructura domótica (resumen persistente)
- Proxmox AMD (admin): `192.168.201.254:8006`.
- Proxmox Intel (video/frigate): `192.168.201.253:8006`.
- Home Assistant VM 101: `http://192.168.200.146:8123`.
- Domo server (BBDD HA): `192.168.200.2` (MariaDB + InfluxDB).
- Frigate LXC 202 (`frigate-lxc`): IP activa `192.168.200.238`, web/API `http://192.168.200.238:5000`.

## Caminos de acceso a Home Assistant (usar el más eficaz)
1. **MCP/API** (token LEO) para control diario y contexto global.
2. **REST API por curl** (`/api/states`, `/api/services/*`) para precisión por `entity_id`.
3. **Proxmox SSH/root** para gestión de VM 101 (`qm`, consola, estado, restart).
4. **SSH a HAOS** para tareas internas limitadas.

## Caminos de acceso a Frigate
1. **Web/API Frigate**: `http://192.168.200.238:5000` (ej. `/api/version`).
2. **Proxmox SSH/root (host Intel)**: gestión del LXC 202 (`pct status/config/exec`).
3. **Dentro del LXC 202**: stack Docker Compose en `/opt/frigate`.

## Instalación fotovoltaica (resumen persistente)
- Potencia FV: ~9 kW (20 paneles de 450 W) en instalación Este/Oeste, 2 strings.
- Inversor: **INGECON SUN STORAGE 1Play TL M**.
  - Firmware histórico: `ABH1007_Z` (puede estar ya actualizado; verificar por API).
  - IP inversor: `192.168.200.51`.
  - Usuario API/Web: `darconada`.
  - Password: usar `DOMOTICA_GENERAL_PASS` desde `.env`.
- Vatímetro externo: `CG-EM112-DIN AV0@1`.
- Batería HV: **BYD PREMIUM HVM** de ~13.78 kWh (6 módulos de 2.78 kWh).
- Modos/operativa:
  - Puede verter a red (exportar) e importar.
  - Soporta funcionamiento en aislado mediante línea de cargas críticas.
  - Existe relé de desvío a críticas (hasta ~6 kW).
## Secretos
- Contraseña general domótica en `.env` como `DOMOTICA_GENERAL_PASS`.
- Token HA guardado en `.env` como `HA_TOKEN`.
- Credenciales de portátil/Tailscale en `.env` (`LAPTOP_HOST`, `LAPTOP_USER`, `LAPTOP_PASS`).
- No guardar secretos en archivos de configuración normales.

## Repos/proyectos locales relevantes
- API Ingeteam local copiada en servidor: `/root/apps/home-assistant-ingeteam-modbus-main`.
- Servicio systemd API Ingeteam: `ingeteam-api.service` (autoarranque), frontend/API en puerto `8010`.
