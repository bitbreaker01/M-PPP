# Playbook: datos · las 15 reglas del catalogo

Inventario 9.2 (2 de nivel Correo + 5 de nivel Solicitud) y 9.3 (8 de nivel
Registro). Contenido transcripto de `diseno/02-diccionario-datos.md` §156, §158
y §162. Generado por script para que no se despegue del diseno.

`sanic_nombre` NO se carga: es autonumerica `REG-{SEQNUM:4}` y se llena sola.
`sanic_mensajecliente` queda VACIA a proposito (D-19): cuando esta vacia, el
evaluador usa su propio mensaje por defecto, que es el texto aprobado y vive en
el codigo. Cargar una plantilla aca duplicaria la fuente de verdad.

`sanic_orden` lo deriva este script (D-47): orden topologico en multiplos de 10
dentro de cada nivel. El diseno solo fija el orden RELATIVO; el motor exige que
quien depende tenga orden estrictamente mayor (`02` §152), y el script lo
comprueba con un assert antes de escribir el playbook.

## 1. Identidad

```json
{
  "tipo_playbook": "datos",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "9.2+9.3",
  "fase": 1,
  "entorno_url": "https://org36e60d9d.crm.dynamics.com/",
  "solucion": "sanic_mppp_sol_mantenimientoppp",
  "publisher": "Sistemas_Abiertos_Nicaragua",
  "prefijo": "sanic",
  "abrev": "mppp",
  "prefijo_opciones": 15946,
  "lcid": 1033
}
```

## 2. Qué se crea

```json
{
  "tipo": "datos",
  "tabla": "sanic_mppp_tbl_regla",
  "clave": [
    "sanic_codigo"
  ],
  "filas": [
    {
      "sanic_codigo": "ES_CORREO_NUEVO",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Correo"
      },
      "sanic_orden": 10,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Envia a revision"
      }
    },
    {
      "sanic_codigo": "REMITENTE_RECONOCIDO",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Correo"
      },
      "sanic_orden": 20,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Envia a revision"
      },
      "sanic_dependede": "ES_CORREO_NUEVO"
    },
    {
      "sanic_codigo": "TRAE_ADJUNTO",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Solicitud"
      },
      "sanic_orden": 10,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      }
    },
    {
      "sanic_codigo": "ADJUNTO_ES_EXCEL",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Solicitud"
      },
      "sanic_orden": 20,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "TRAE_ADJUNTO"
    },
    {
      "sanic_codigo": "UN_SOLO_EXCEL",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Solicitud"
      },
      "sanic_orden": 30,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "ADJUNTO_ES_EXCEL"
    },
    {
      "sanic_codigo": "ESTRUCTURA_PLANTILLA",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Solicitud"
      },
      "sanic_orden": 40,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "UN_SOLO_EXCEL"
    },
    {
      "sanic_codigo": "TIENE_FILAS",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Solicitud"
      },
      "sanic_orden": 50,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "ESTRUCTURA_PLANTILLA"
    },
    {
      "sanic_codigo": "LISTAS_VALIDAS",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Registro"
      },
      "sanic_orden": 10,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      }
    },
    {
      "sanic_codigo": "LARGOS_Y_FORMATO",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Registro"
      },
      "sanic_orden": 20,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      }
    },
    {
      "sanic_codigo": "PLAN_EXISTE",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Registro"
      },
      "sanic_orden": 30,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_mensajecliente": "El plan {plan} no existe o usted no está autorizado sobre él."
    },
    {
      "sanic_codigo": "AUTORIZACION_CORREO_PLAN",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Registro"
      },
      "sanic_orden": 40,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "PLAN_EXISTE",
      "sanic_mensajecliente": "El plan {plan} no existe o usted no está autorizado sobre él."
    },
    {
      "sanic_codigo": "FORMATO_11_SOLO_ACH",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Registro"
      },
      "sanic_orden": 50,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "AUTORIZACION_CORREO_PLAN,LISTAS_VALIDAS"
    },
    {
      "sanic_codigo": "OBLIGATORIEDAD",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Registro"
      },
      "sanic_orden": 60,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "AUTORIZACION_CORREO_PLAN,LISTAS_VALIDAS"
    },
    {
      "sanic_codigo": "MONEDA_DEL_PLAN",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Registro"
      },
      "sanic_orden": 70,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "AUTORIZACION_CORREO_PLAN,LISTAS_VALIDAS"
    },
    {
      "sanic_codigo": "REFERENCIA_FORMATO_11",
      "sanic_nivel": {
        "choice": "sanic_mppp_ch_nivelregla",
        "etiqueta": "Registro"
      },
      "sanic_orden": 80,
      "sanic_efecto": {
        "choice": "sanic_mppp_ch_efectoregla",
        "etiqueta": "Rechaza"
      },
      "sanic_dependede": "FORMATO_11_SOLO_ACH,OBLIGATORIEDAD"
    }
  ]
}
```

## 3. Precondiciones

- La tabla `sanic_mppp_tbl_regla` y su clave `sanic_mppp_key_regla_codigo` existen.
- Los choice `sanic_mppp_ch_nivelregla` y `sanic_mppp_ch_efectoregla` existen con sus etiquetas.

## 4. Invariantes que fija el diseño y respeta este playbook

- **Efecto `Envia a revision` solo en niveles Correo y Solicitud, nunca en Registro** (D-20).
- **`AUTORIZACION_CORREO_PLAN` no admite otro efecto que `Rechaza`** (D-14).
- Toda dependencia es del **mismo nivel** y tiene **orden menor** (`02` §152).
- El codigo C# tiene un evaluador por cada uno de estos 15 codigos; una regla activa sin evaluador hace fallar cerrado al motor (D-13).
