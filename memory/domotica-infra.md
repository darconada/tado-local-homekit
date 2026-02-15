# Infraestructura Domótica

## Hosts Proxmox (No Cluster)

### 1. Host AMD (Administración)
- **IP:** `192.168.201.254:8006`
- **Acceso alternativo:** SSH root al host Proxmox para gestionar VM/CT directamente.
- **Hardware:** Ryzen 5 6600H (12 vCPU), 32GB RAM
- **OS:** Proxmox 8.4.1
- **VMs/LXC:**
  - **Prometheus (LXC):** `192.168.200.225` (métricas para Grafana en HA)
  - **Home Assistant OS (VM 101):** `192.168.200.146:8123` (Core)
    - **Caminos de acceso:**
      - API/MCP (token LEO) para control funcional diario.
      - API REST directa vía `curl` sobre `/api/states` y `/api/services/*` para diagnóstico fino y acciones por `entity_id`.
      - Gestión de VM vía Proxmox host AMD (SSH/root + `qm`).
      - SSH a HAOS (limitado para operación interna del sistema).
  - **Domo Server (Linux):** `192.168.200.2`
    - **OS:** Ubuntu 22.04.4 LTS.
    - **Rol:** BBDD externas de Home Assistant.
    - **Servicios:**
      - **MySQL/MariaDB:** Nativo (Systemd), puerto 3306.
      - **InfluxDB:** Docker (`influxdb:1.8`, container `influxdb1`), puerto 8086.
    - **Acceso:** SSH verificado (`dani` + `DOMOTICA_GENERAL_PASS`).
    - **Estado:** 55% disco usado, Load avg bajo.

### 2. Host Intel (Frigate/Video)
- **IP:** `192.168.201.253:8006` (SSH: 22)
- **Hardware:** Intel iGPU (iHD driver) + Coral USB
- **OS:** Proxmox 9.0.x (kernel 6.14.x)
- **LXC CTID 202 (Frigate):**
  - **IP:** `192.168.200.238` (Estática, GW .1)
  - **Stack:** Docker Compose en `/opt/frigate`
  - **Hardware Passthrough:** 
    - iGPU: `/dev/dri/renderD128` (VA-API)
    - Coral USB: Bind mount `/dev/bus/usb` (privileged mode act.)
  - **Almacenamiento:**
    - RootFS: 20GB
    - Grabaciones: `mp0` (local-lvm 100GB) montado en `/opt/frigate/media`
  - **Config:** `hwaccel_args: preset-vaapi`, `detectors: coral`
  - **Estado:** Producción estable (pendientes: harden privileged mode, udev rules)

### 3. OpenClaw (Leo)
- **Ubicación:** VM en Host Intel (Proxmox 2)
- **Rol:** Agente Main (Leo)
