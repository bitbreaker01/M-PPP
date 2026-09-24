#!/usr/bin/env python3
"""Prueba de humo de punta a punta de la validación (P-09, `PENDIENTES.md` §B).

    python3 herramientas/prueba_humo_validacion.py [--limpiar]

Qué hace, contra Dev:
 1. arma una copia de la plantilla REAL del cliente con dos filas ficticias —
    una que tiene que quedar Validada y otra que tiene que quedar rechazada;
 2. crea una Solicitud en Ingresada y le sube ese Excel a `sanic_exceloriginal`;
 3. llama `sanic_mppp_capi_validarsolicitud`;
 4. comprueba el resultado contra lo esperado y lo informa.

Qué prueba, que ninguna prueba unitaria puede probar:
 - que **DocumentFormat.OpenXml carga y corre en el sandbox real** de Dataverse
   con los ensamblados que viajan en el paquete;
 - que **`DataContractJsonSerializer` bajo el .NET Framework del sandbox** lee
   igual los parámetros JSON que bajo net10, donde corren los tests;
 - que `plantilla.estructura` y `plantilla.listas` —armados contra el Excel
   real— **funcionan de verdad contra ese Excel**;
 - que `InitializeFileBlocksDownload` se comporta como el código supone.

Los datos son ficticios y llevan `ZZ`: el catálogo lo siembran los playbooks
`playbooks/datos/humo_*.md`, que hay que correr antes.

`--limpiar` borra las Solicitudes de ensayo que haya dejado esta prueba.
"""
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
sys.path.insert(0, _AQUI)

PLANTILLA = os.path.join(_RAIZ, "datos", "plantilla", "Inclusiones_Exclusiones en PPP.xlsx")
CONJUNTO = "sanic_mppp_tbl_solicituds"
REMITENTE = "zzensayo@ejemplo.com"
MARCA = "ZZ-HUMO"

# Fila 13 (válida) y fila 14 (rechazada por banco fuera de lista). Columnas B..K.
FILAS = [
    ["INCLUSIÓN", "ACH", "ZZ01", "ZZ Beneficiario Uno", "CNA", "001-010180-1000X", "", "123456789", "USD", "BAC"],
    ["INCLUSIÓN", "ACH", "ZZ01", "ZZ Beneficiario Dos", "CNA", "001-010180-2000Y", "", "987654321", "USD", "BANCO QUE NO EXISTE"],
]
COLUMNAS = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]
PRIMERA_FILA = 13


def armar_excel(destino):
    """Copia la plantilla real y le escribe las filas ficticias. No se toca
    nada más: encabezados, hoja y ventana quedan como los manda el cliente."""
    import openpyxl

    libro = openpyxl.load_workbook(PLANTILLA)
    hoja = libro["Datos"]
    for i, fila in enumerate(FILAS):
        for columna, valor in zip(COLUMNAS, fila):
            if valor != "":
                hoja[f"{columna}{PRIMERA_FILA + i}"] = valor
    libro.save(destino)
    with open(destino, "rb") as f:
        return f.read()


def limpiar(dv):
    ruta = f"{CONJUNTO}?$select=sanic_mppp_tbl_solicitudid,sanic_nombre&$filter=startswith(sanic_messageid,'<{MARCA}')"
    est, cuerpo, _ = dv.call("GET", ruta)
    if est != 200:
        print(f"no se pudieron listar las solicitudes de ensayo: HTTP {est} {cuerpo}")
        return 1
    filas = cuerpo.get("value", [])
    for fila in filas:
        idf = fila["sanic_mppp_tbl_solicitudid"]
        est, cuerpo, _ = dv.call("DELETE", f"{CONJUNTO}({idf})")
        print(f"  borrada {fila.get('sanic_nombre')} → HTTP {est}" + (f" {cuerpo}" if est >= 400 else ""))
    print(f"{len(filas)} solicitud(es) de ensayo")
    return 0


def main():
    from dataverse_api import Dataverse

    dv = Dataverse()
    if "--limpiar" in sys.argv:
        return limpiar(dv)

    import datetime
    import tempfile

    sello = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with tempfile.TemporaryDirectory() as tmp:
        destino = os.path.join(tmp, "ZZ-humo.xlsx")
        contenido = armar_excel(destino)
    print(f"1. Excel armado sobre la plantilla real: {len(contenido)} bytes, {len(FILAS)} filas")

    cuerpo = {
        "sanic_estadoprocesamiento": 159460001,  # Ingresada
        "sanic_fechaingresada": ahora,
        "sanic_fecharecibido": ahora,
        "sanic_messageid": f"<{MARCA}-{sello}@ensayo>",
        "sanic_remitente": REMITENTE,
        "sanic_asunto": "ZZ prueba de humo",
        "sanic_cantidadadjuntos": 1,
        "sanic_cantidadexcel": 1,
    }
    est, resp, cab = dv.call("POST", CONJUNTO, cuerpo)
    if est not in (200, 201, 204):
        print(f"FALLO al crear la Solicitud: HTTP {est} {resp}")
        return 1
    solicitud_id = Dataverse.id_creado(cab)
    print(f"2. Solicitud creada: {solicitud_id}")

    est, resp, _ = dv.subir_archivo(
        f"{CONJUNTO}({solicitud_id})/sanic_exceloriginal", "ZZ-humo.xlsx", contenido)
    if est not in (200, 204):
        print(f"FALLO al subir el Excel: HTTP {est} {resp}")
        return 1
    print("3. Excel subido a sanic_exceloriginal")

    est, resp, _ = dv.call("POST", "sanic_mppp_capi_validarsolicitud", {"solicitudid": solicitud_id})
    print(f"4. Custom API: HTTP {est}")
    if est not in (200, 204):
        print(f"   FALLO: {resp}")
        print("   (si dice que no encuentra el mensaje, revisar que la Custom API no sea privada para quien llama)")
        return 1
    for clave in ("estado", "yaprocesada", "filastotales", "filasvalidas", "filasrechazadas", "resumen"):
        print(f"   {clave} = {resp.get(clave)!r}")

    est, cuerpo, _ = dv.call(
        "GET",
        f"{CONJUNTO}({solicitud_id})?$select=sanic_nombre,sanic_estadoprocesamiento,sanic_filastotales,"
        "sanic_filasvalidas,sanic_filasrechazadas,sanic_versionparametros,sanic_acusecontenido")
    print(f"5. Solicitud releida: HTTP {est}")
    if est == 200:
        acuse = cuerpo.get("sanic_acusecontenido") or ""
        for clave in ("sanic_nombre", "sanic_estadoprocesamiento", "sanic_filastotales",
                      "sanic_filasvalidas", "sanic_filasrechazadas", "sanic_versionparametros"):
            print(f"   {clave} = {cuerpo.get(clave)!r}")
        print(f"   acuse: {len(acuse)} caracteres")

    ruta_filas = ("sanic_mppp_tbl_filas?$select=sanic_numerofila,sanic_estado,sanic_referencia,"
                  "sanic_numerocuenta,sanic_mensaje,sanic_nombre"
                  f"&$filter=_sanic_solicitudid_value eq {solicitud_id}&$orderby=sanic_numerofila")
    est, cuerpo, _ = dv.call("GET", ruta_filas)
    print(f"6. Filas guardadas: HTTP {est}")
    if est == 200:
        for fila in cuerpo.get("value", []):
            print(f"   #{fila.get('sanic_numerofila')} [{fila.get('sanic_nombre')}] {fila.get('sanic_estado')!r} "
                  f"cuenta={fila.get('sanic_numerocuenta')!r} referencia={fila.get('sanic_referencia')!r}")
            if fila.get("sanic_mensaje"):
                print(f"       mensaje: {fila['sanic_mensaje']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
