#!/usr/bin/env python3
"""Mira el trabajo que convierte una suscripción de Dataverse en una entrega real.

**Por qué existe.** Un trigger de flujo ("cuando se agrega o modifica una fila")
deja una fila en `callbackregistration`. Esa fila, por sí sola, no entrega nada:
hay un trabajo del sistema llamado **CallbackRegistration Expander Operation**
(`asyncoperation.operationtype = 79`) que la expande en la notificación que sale
hacia Power Automate.

En este entorno la suscripción está impecable, la fila cambia, el entorno está
Activo y el servicio asíncrono procesa trabajos — y aun así ningún flujo con
trigger de Dataverse dispara desde el 2026-08-31. Si el expansor dejó de correr,
ahí está el eslabón roto.

Solo lee. No escribe, no borra, no sale nada a internet.

Uso:  python3 herramientas/diagnostico/expansor_callbacks.py
"""

import os
import sys
import collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataverse_api import Dataverse  # noqa: E402

RAZON = {0: "Waiting for resources", 10: "Waiting", 20: "In progress",
         30: "Succeeded", 31: "Failed", 32: "Canceled"}

# Plugins de sistema que inundan la cola y no aportan nada a este diagnóstico.
RUIDO = ("AppCopilotFeatures", "SourceControlIntegration", "PurgeArchivedContent",
         "knowledgearticle", "Knowledge Article", "ComponentVersioning")

SEP = "-" * 78


def filas(dv, ruta):
    codigo, cuerpo, _ = dv.call("GET", ruta)
    if codigo != 200 or not isinstance(cuerpo, dict):
        print(f"   (HTTP {codigo})")
        return []
    return cuerpo.get("value", [])


def por_tipo(dv, tipo, etiqueta):
    """Todo lo ocurrido con un operationtype, en los dos extremos de la historia."""
    print(f"\n{SEP}\n=== {etiqueta}  (operationtype {tipo}) ===")
    campos = ("asyncoperations?$select=name,statuscode,createdon,startedon,completedon,"
              "message,friendlymessage,errorcode"
              f"&$filter=operationtype eq {tipo}&$orderby=createdon ")
    viejos = filas(dv, campos + "asc&$top=100")
    nuevos = filas(dv, campos + "desc&$top=100")

    todos = {x["asyncoperationid"]: x for x in viejos + nuevos} if viejos or nuevos else {}
    if not todos:
        # `asyncoperationid` no se pidió; reconstruimos por createdon+name.
        todos = {(x["createdon"], x.get("name")): x for x in viejos + nuevos}
    registros = sorted(todos.values(), key=lambda x: x["createdon"])
    if not registros:
        print("   NINGÚN registro. Este trabajo nunca corrió en el entorno.")
        return

    print(f"   {len(registros)} registro(s) visibles")
    print(f"   primero: {registros[0]['createdon'][:19]}")
    print(f"   ÚLTIMO : {registros[-1]['createdon'][:19]}   ← si es viejo, dejó de correr")
    cuenta = collections.Counter(RAZON.get(x.get("statuscode"), "?") for x in registros)
    for estado, n in cuenta.most_common():
        print(f"      {estado:22} → {n}")

    print("\n   los 12 más recientes:")
    for x in registros[-12:]:
        texto = (x.get("friendlymessage") or x.get("message") or "").strip().splitlines()
        print(f"      {x['createdon'][:19]}  {RAZON.get(x.get('statuscode'), '?'):22} "
              f"started={str(x.get('startedon'))[:19]:19} {str(x.get('name'))[:40]}")
        if texto:
            print(f"           {texto[0][:150]}")


def franja_del_31(dv):
    """El 31 de agosto, sin el ruido de los plugins de mantenimiento."""
    print(f"\n{SEP}\n=== el 2026-08-31, filtrando el ruido de mantenimiento ===")
    f = filas(dv, "asyncoperations?$select=name,operationtype,statuscode,createdon,"
                  "message,friendlymessage"
                  "&$filter=createdon ge 2026-08-31T00:00:00Z and "
                  "createdon le 2026-09-01T12:00:00Z"
                  "&$orderby=createdon asc&$top=500")
    utiles = [x for x in f if not any(r in (x.get("name") or "") for r in RUIDO)]
    print(f"   {len(f)} en total, {len(utiles)} después de sacar el ruido\n")
    for x in utiles:
        texto = (x.get("friendlymessage") or x.get("message") or "").strip().splitlines()
        print(f"   {x['createdon'][:19]} tipo={x.get('operationtype'):4} "
              f"{RAZON.get(x.get('statuscode'), '?'):22} {str(x.get('name'))[:50]}")
        if texto and x.get("statuscode") in (31, 32):
            print(f"        {texto[0][:150]}")


def main():
    dv = Dataverse()
    por_tipo(dv, 79, "CallbackRegistration Expander Operation")
    por_tipo(dv, 101, "Update Modern Flow Async Operation")
    franja_del_31(dv)
    print("\nListo. Nada de esto modificó el entorno.")


if __name__ == "__main__":
    main()
