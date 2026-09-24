#!/usr/bin/env python3
"""Saca el texto COMPLETO de las fallas del plugin que une Dataverse con Power Automate.

**Por qué existe.** En la cola de trabajos del sistema apareció un fallo de
`Microsoft.Dynamics.MicrosoftFlow.Plugin` el 2026-08-31, que es el día exacto en
que los trece flujos con trigger de Dataverse del entorno dejaron de dispararse.
El motivo está escrito en la columna `message`, pero completo ocupa varias
líneas y el resumen anterior solo mostraba la primera.

También le pregunta a la plataforma cómo se llama cada `operationtype` en vez de
deducirlo: un mapa inventado a mano ya hizo leer "ServiceEndpointNotification"
donde en realidad decía "Full Text Catalog job".

Solo lee. No escribe, no borra, no sale nada a internet.

Uso:  python3 herramientas/diagnostico/falla_flow.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataverse_api import Dataverse  # noqa: E402

RAZON = {0: "Waiting for resources", 10: "Waiting", 20: "In progress",
         30: "Succeeded", 31: "Failed", 32: "Canceled"}

SEPARADOR = "-" * 78


def filas(dv, ruta):
    codigo, cuerpo, _ = dv.call("GET", ruta)
    if codigo != 200 or not isinstance(cuerpo, dict):
        print(f"   (HTTP {codigo})")
        return []
    return cuerpo.get("value", [])


def tipos_reales(dv):
    """Los nombres de `operationtype` tal como los declara la plataforma."""
    ruta = ("EntityDefinitions(LogicalName='asyncoperation')/Attributes"
            "(LogicalName='operationtype')/Microsoft.Dynamics.CRM.PicklistAttributeMetadata"
            "?$select=LogicalName&$expand=OptionSet($select=Options)")
    codigo, cuerpo, _ = dv.call("GET", ruta)
    mapa = {}
    if codigo == 200 and isinstance(cuerpo, dict):
        for o in (cuerpo.get("OptionSet") or {}).get("Options", []):
            etiquetas = (o.get("Label") or {}).get("LocalizedLabels") or []
            if etiquetas:
                mapa[o["Value"]] = etiquetas[0].get("Label")
    return mapa


def imprimir(x, mapa):
    tipo = mapa.get(x.get("operationtype"), f"tipo {x.get('operationtype')}")
    print(SEPARADOR)
    print(f"{x['createdon'][:19]}  {RAZON.get(x.get('statuscode'), '?')}  ·  {tipo}")
    print(f"nombre: {x.get('name')}")
    print(f"errorcode: {x.get('errorcode')}   completedon: {x.get('completedon')}")
    for campo in ("friendlymessage", "message"):
        texto = (x.get(campo) or "").strip()
        if texto:
            print(f"\n[{campo}]")
            print(texto[:4000])


def main():
    dv = Dataverse()
    mapa = tipos_reales(dv)

    print("=== cómo se llama de verdad cada operationtype (según la plataforma) ===")
    for valor in sorted(mapa):
        if valor in (1, 13, 25, 57, 58, 63, 65, 69, 79, 101, 104, 239, 304, 306, 330):
            print(f"   {valor:4} = {mapa[valor]}")
    endpoint = [v for v, n in mapa.items() if "endpoint" in (n or "").lower()]
    print(f"\n   tipos con 'endpoint' en el nombre: {[(v, mapa[v]) for v in endpoint]}")

    print("\n\n=== TODAS las fallas del plugin de Power Automate, texto completo ===")
    hallados = filas(dv, "asyncoperations?$select=name,operationtype,statuscode,createdon,"
                         "completedon,message,friendlymessage,errorcode"
                         "&$filter=contains(name,'MicrosoftFlow')"
                         "&$orderby=createdon asc&$top=50")
    print(f"{len(hallados)} registro(s)\n")
    for x in hallados:
        imprimir(x, mapa)

    print("\n\n=== todo lo que pasó entre el 2026-08-30 y el 2026-09-02 ===")
    ventana = filas(dv, "asyncoperations?$select=name,operationtype,statuscode,createdon,"
                        "completedon,message,friendlymessage,errorcode"
                        "&$filter=createdon ge 2026-08-30T00:00:00Z and "
                        "createdon le 2026-09-02T23:59:59Z"
                        "&$orderby=createdon asc&$top=100")
    print(f"{len(ventana)} registro(s)\n")
    for x in ventana:
        estado = RAZON.get(x.get("statuscode"), "?")
        tipo = mapa.get(x.get("operationtype"), f"tipo {x.get('operationtype')}")
        print(f"  {x['createdon'][:19]}  {estado:22} {tipo[:34]:36} {str(x.get('name'))[:44]}")
    print("\n--- de esos, los que fallaron, con texto completo ---")
    for x in ventana:
        if x.get("statuscode") == 31:
            imprimir(x, mapa)

    print("\n\n=== ¿existen trabajos de entrega a endpoints externos, alguna vez? ===")
    for valor in endpoint:
        f = filas(dv, "asyncoperations?$select=name,statuscode,createdon"
                      f"&$filter=operationtype eq {valor}&$orderby=createdon desc&$top=10")
        print(f"   {mapa[valor]} (tipo {valor}): {len(f)} registro(s)")
        for x in f:
            print(f"      {x['createdon'][:19]} {RAZON.get(x.get('statuscode'), '?')} {str(x.get('name'))[:50]}")

    print("\nListo. Nada de esto modificó el entorno.")


if __name__ == "__main__":
    main()
