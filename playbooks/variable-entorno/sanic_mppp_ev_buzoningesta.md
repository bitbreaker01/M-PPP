# Playbook: variable-entorno · sanic_mppp_ev_buzoningesta

Inventario 10.1. `07-flujos.md` DF-05.

Valor del Dev del aprobador (DF-05). Es un **buzon compartido**.

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
  "inventario": "10.1"
}
```

## 2. Qué se crea

```json
{
  "tipo": "variable-entorno",
  "nombre": "sanic_mppp_ev_buzoningesta",
  "displayname": "EV - MPPP - Buzon de ingesta",
  "descripcion": "Buzon compartido del que MPPP-REC lee los correos entrantes y al que MPPP-ENV responde.",
  "tipovalor": "Texto",
  "obligatoria": true,
  "valor": "mppp@55xljh.onmicrosoft.com"
}
```

## 3. Precondiciones

- La definicion viaja en la solucion; el VALOR no, porque es de este entorno (`07` DF-05: "la solucion pasa despues al Dev de BAC, donde estos valores se cargan de nuevo").
