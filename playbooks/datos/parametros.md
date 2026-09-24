# Playbook: datos · parametros (los 13)

**`servicio.cuenta` se agrego el 2026-09-23 y hoy tiene un valor PROVISORIO.** Declara el UPN de la
cuenta con la que los cinco flujos escriben en Dataverse; `BaseDeStep.EsCodigoDeServidor` lo usa
para no tratarlos como si fueran una persona (ver `diseno/07-flujos.md` §33, que declara la
excepcion a BP-PP-122: en BAC la cuenta de servicio es un usuario, no un service principal, y un
usuario no tiene `applicationid`). Mientras el componente 13.2 (cuenta de servicio licenciada) no
exista, apunta a la cuenta personal del administrador. **Eso significa que esa persona tampoco pasa
por la lista blanca cuando trabaja a mano.** Decidido asi el 2026-09-23 para no frenar las pruebas.

Inventario 9.1. **COMPLETO desde el 2026-09-22.** `plantilla.estructura` y `plantilla.listas` se
armaron leyendo `datos/plantilla/Inclusiones_Exclusiones en PPP.xlsx`, la plantilla
real del cliente: los encabezados salen de la fila 12 de la hoja `Datos` y los
codigos de banco de la hoja `Listas`. Los valores canonicos son los nombres de los
enums del dominio (`Dominio/Choices.g.cs`), no los textos del Excel: la comparacion
de listas ya ignora mayusculas, tildes y ñ, asi que INCLUSION matchea Inclusion sin
necesidad de declarar variantes.

Valores con fuente:
- `correo.prefijos.reenvio`, `clasificacion.dias.vencimiento`, `rpa.puedeaprobar`: `02-diccionario-datos.md` §134-136.
- `lectura.limites`: `03-contratos-custom-api.md` §249 (2 MB / 20 MB); los nombres de las claves salen de `Plantilla/LimitesLectura.cs`.
- `plantilla.obligatoriedad`: DD-16 ("todo obligatorio salvo Referencia") con la forma de D-18.
- Los tres de `vigilancia.*` y los dos de `retencion.dias.*`: **decididos por el aprobador el 2026-09-22** (D-45); no estaban en ningun archivo.

Ojo: los fixtures de prueba (`ParametrosDePlantillaAceptacion`) y el mockup
NO son fuente de datos. Sus codigos de banco y sus columnas son inventados y no
coinciden con la plantilla real del cliente.

## 1. Identidad

```json
{
  "tipo_playbook": "datos",
  "version_skill": "0.1.0",
  "proyecto": "2026-001-referencias-planes-pago",
  "inventario": "9.1",
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
  "tabla": "sanic_mppp_tbl_parametro",
  "clave": [
    "sanic_nombre",
    "sanic_version"
  ],
  "filas": [
    {
      "sanic_nombre": "correo.prefijos.reenvio",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "JSON"
      },
      "sanic_valor": "[\"FW:\",\"FWD:\",\"RV:\",\"REENV:\"]",
      "sanic_descripcion": "Prefijos de asunto que identifican un reenvio. 02 §134."
    },
    {
      "sanic_nombre": "clasificacion.dias.vencimiento",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "Numero"
      },
      "sanic_valor": "30",
      "sanic_descripcion": "Dias que un correo puede quedar en Por clasificar antes de pasar a Vencida. 02 §135."
    },
    {
      "sanic_nombre": "lectura.limites",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "JSON"
      },
      "sanic_valor": "{\"maximoBytesComprimido\":2097152,\"maximoBytesDescomprimido\":20971520}",
      "sanic_descripcion": "Peso maximo del archivo comprimido (2 MB) y del contenido descomprimido (20 MB). 03 §249."
    },
    {
      "sanic_nombre": "plantilla.obligatoriedad",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "JSON"
      },
      "sanic_valor": "{\"porDefecto\":\"obligatorio\",\"opcionales\":[{\"campo\":\"referencia\"}]}",
      "sanic_descripcion": "Campos obligatorios. Arranca con todo obligatorio salvo Referencia (DD-16); crece con reglas cuando el negocio escriba la matriz."
    },
    {
      "sanic_nombre": "rpa.puedeaprobar",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "Texto"
      },
      "sanic_valor": "no",
      "sanic_descripcion": "En 'si', el bot puede aprobar lo que el mismo digito. Queda en 'no' hasta contar con el aval de C-03."
    },
    {
      "sanic_nombre": "servicio.cuenta",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "Texto"
      },
      "sanic_valor": "admin@55xljh.onmicrosoft.com",
      "sanic_descripcion": "PROVISORIO. UPN de la cuenta con la que los cinco flujos escriben; sin el, la lista blanca los trata como personas y no pueden escribir sus marcas de envio. Hoy apunta a la cuenta personal del administrador porque el componente 13.2 no existe todavia: cambiar al UPN de la cuenta de servicio de BAC antes de produccion."
    },
    {
      "sanic_nombre": "vigilancia.minutos.sinvalidar",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "Numero"
      },
      "sanic_valor": "15",
      "sanic_descripcion": "Umbral de MPPP-VIG para una Solicitud que sigue en Ingresada. Aprobado 2026-09-22: VIG corre cada 10 min."
    },
    {
      "sanic_nombre": "vigilancia.minutos.sinresponder",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "Numero"
      },
      "sanic_valor": "30",
      "sanic_descripcion": "Umbral de MPPP-VIG para una comunicacion sin enviar o sin confirmar. Aprobado 2026-09-22."
    },
    {
      "sanic_nombre": "vigilancia.reintentos.maximo",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "Numero"
      },
      "sanic_valor": "3",
      "sanic_descripcion": "Reintentos de validacion antes de marcar sanic_requiererevision. Aprobado 2026-09-22."
    },
    {
      "sanic_nombre": "retencion.dias.general",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "Numero"
      },
      "sanic_valor": "30",
      "sanic_descripcion": "Plazo del historico desde que la Solicitud queda Cerrada. Lo consume el job de purga de fase 3 (D-35). Aprobado 2026-09-22."
    },
    {
      "sanic_nombre": "retencion.dias.noreconocidas",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "Numero"
      },
      "sanic_valor": "30",
      "sanic_descripcion": "Plazo corto para las No reconocidas y Descartadas (DD-06). Lo consume el job de purga de fase 3. Aprobado 2026-09-22."
    },
    {
      "sanic_nombre": "plantilla.estructura",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "JSON"
      },
      "sanic_valor": "{\"hoja\": \"Datos\", \"filaEncabezado\": 12, \"primeraFila\": 13, \"cantidadFilas\": 100, \"campos\": [{\"nombre\": \"gestion\", \"columna\": \"B\", \"encabezado\": \"Gestión\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 20}, {\"nombre\": \"clasificacion\", \"columna\": \"C\", \"encabezado\": \"Clasificación\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 10}, {\"nombre\": \"numeroPlan\", \"columna\": \"D\", \"encabezado\": \"No. Plan\", \"formato\": \"alfanumerico\", \"largoMinimo\": 1, \"largoMaximo\": 4}, {\"nombre\": \"nombreBeneficiario\", \"columna\": \"E\", \"encabezado\": \"Nombre Colaborador / Proveedor\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 44}, {\"nombre\": \"tipoIdentificacion\", \"columna\": \"F\", \"encabezado\": \"Tipo ID\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 10}, {\"nombre\": \"numeroIdentificacion\", \"columna\": \"G\", \"encabezado\": \"No. Identificación\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 16}, {\"nombre\": \"referencia\", \"columna\": \"H\", \"encabezado\": \"Referencia\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 20}, {\"nombre\": \"numeroCuenta\", \"columna\": \"I\", \"encabezado\": \"No. Cuenta\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 16}, {\"nombre\": \"moneda\", \"columna\": \"J\", \"encabezado\": \"Moneda\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 10}, {\"nombre\": \"banco\", \"columna\": \"K\", \"encabezado\": \"Banco\", \"formato\": \"texto\", \"largoMinimo\": 1, \"largoMaximo\": 20}]}",
      "sanic_descripcion": "Hoja, ventana de filas y las 10 columnas B-K con su encabezado, formato y largos. Encabezados leidos de la plantilla real del cliente."
    },
    {
      "sanic_nombre": "plantilla.listas",
      "sanic_version": 1,
      "sanic_tipo": {
        "choice": "sanic_mppp_ch_tipoparametro",
        "etiqueta": "JSON"
      },
      "sanic_valor": "{\"gestion\": [{\"valor\": \"Inclusion\", \"variantes\": []}, {\"valor\": \"Exclusion\", \"variantes\": []}, {\"valor\": \"Modificacion\", \"variantes\": []}], \"clasificacion\": [{\"valor\": \"BAC\", \"variantes\": []}, {\"valor\": \"ACH\", \"variantes\": []}, {\"valor\": \"CK\", \"variantes\": []}], \"tipoIdentificacion\": [{\"valor\": \"CNA\", \"variantes\": []}, {\"valor\": \"CRE\", \"variantes\": []}, {\"valor\": \"PAS\", \"variantes\": []}, {\"valor\": \"PEX\", \"variantes\": []}, {\"valor\": \"RUC\", \"variantes\": []}], \"moneda\": [{\"valor\": \"COR\", \"variantes\": []}, {\"valor\": \"USD\", \"variantes\": []}], \"banco\": [{\"valor\": \"LAFISE\", \"variantes\": [], \"codigo\": \"006\"}, {\"valor\": \"BAC\", \"variantes\": [], \"codigo\": \"007\"}, {\"valor\": \"BANPRO\", \"variantes\": [], \"codigo\": \"008\"}, {\"valor\": \"FICOHSA\", \"variantes\": [], \"codigo\": \"009\"}, {\"valor\": \"BDF\", \"variantes\": [], \"codigo\": \"012\"}, {\"valor\": \"AVANZ\", \"variantes\": [], \"codigo\": \"019\"}, {\"valor\": \"PRODUZCAMOS\", \"variantes\": [], \"codigo\": \"023\"}, {\"valor\": \"ATLANTIDA\", \"variantes\": [], \"codigo\": \"037\"}]}",
      "sanic_descripcion": "Valores aceptados de cada lista, con el codigo de 3 digitos del banco (DD-10). Codigos leidos de la plantilla real del cliente."
    }
  ]
}
```

## 3. Precondiciones

- La tabla `sanic_mppp_tbl_parametro` y su clave `sanic_mppp_key_parametro_nombre_version` existen.
- El step `MPPP - Normalizar y validar - Create de Parametro` esta registrado: normaliza `sanic_nombre` a minusculas y exige el formato separado por puntos. Si un nombre no pasa, el alta se rechaza y se ve el motivo.
