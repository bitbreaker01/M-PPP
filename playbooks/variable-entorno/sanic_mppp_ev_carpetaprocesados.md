# Playbook: variable-entorno · sanic_mppp_ev_carpetaprocesados

Inventario 10.2. `07-flujos.md` DF-05.

**Se crea SIN VALOR a proposito.** La carpeta la crea el administrador de Exchange
(inventario 13.1) y su nombre no esta fijado en el diseno. Inventarlo haria que
*Move email* de MPPP-ING fallara en tiempo de ejecucion sin que nadie supiera por que;
una variable vacia, en cambio, se ve y se pregunta. Queda `obligatoria: false` para que
no frene una importacion de solucion. **Hay que cargarle el valor antes de construir
MPPP-ING (P-12).**

## 1. Identidad

```json
{
  "tipo_playbook": "variable-entorno",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "fase": 1,
  "entorno_url": "https://org36e60d9d.crm.dynamics.com/",
  "solucion": "sanic_mppp_sol_mantenimientoppp",
  "publisher": "Sistemas_Abiertos_Nicaragua",
  "prefijo": "sanic",
  "abrev": "mppp",
  "prefijo_opciones": 15946,
  "lcid": 1033,
  "inventario": "10.2"
}
```

## 2. Qué se crea

```json
{
  "tipo": "variable-entorno",
  "nombre": "sanic_mppp_ev_carpetaprocesados",
  "displayname": "EV - MPPP - Carpeta de procesados",
  "descripcion": "Carpeta del buzon compartido a la que MPPP-ING mueve el correo ya ingresado (paso 7).",
  "tipovalor": "Texto",
  "obligatoria": false,
  "valor": "Procesados"
}
```

## 3. Precondiciones

- La definicion viaja en la solucion; el VALOR no, porque es de este entorno (`07` DF-05: "la solucion pasa despues al Dev de BAC, donde estos valores se cargan de nuevo").
- **La carpeta tiene que EXISTIR en el buzon con ese nombre exacto**: `MoveV2` la busca por
  `folderPath`, o sea por nombre, no por identificador.
- **Sin valor, el flujo que la usa NO SE PUEDE ACTIVAR** (`XrmEnvironmentVariableAttributeNotFound`,
  visto en Dev el 2026-09-22 al intentar encender MPPP-ING). No es que falle al ejecutarse: no
  arranca.
