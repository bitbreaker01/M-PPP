#!/usr/bin/env python3
"""Lee los intentos de ENTREGA de eventos de Dataverse hacia endpoints externos.

**Por qué existe.** Cuando un trigger de flujo ("cuando se agrega o modifica una
fila") no dispara, todo lo que se puede mirar desde afuera se ve sano: la
suscripción está registrada en `callbackregistration`, la fila cambia, el
entorno está Activo. El intento de ENTREGA, en cambio, deja rastro en la cola de
trabajos del sistema como una operación de tipo 25 (`ServiceEndpointNotification`),
y si falló, el motivo está escrito en texto en su columna `message`.

Solo lee. No escribe, no borra, no sale nada a internet: habla únicamente con el
Dataverse del proyecto a través de `herramientas/dataverse_api.py`.

Uso:  python3 herramientas/diagnostico/entregas_webhook.py
"""

import os
import sys
import collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataverse_api import Dataverse  # noqa: E402

# asyncoperation.operationtype — solo los que importan para este diagnóstico.
TIPOS = {
    1: "System Event",
    9: "SendEmail",
    10: "Workflow",
    14: "BulkDelete",
    25: "ServiceEndpointNotification",   # ← los webhooks
    27: "CalculateOrgStorageSize",
    50: "ImportSolution",
    54: "ExportSolution",
}

# asyncoperation.statuscode
RAZON = {0: "Waiting for resources", 10: "Waiting", 20: "In progress",
         21: "Pausing", 22: "Canceling", 30: "Succeeded", 31: "Failed", 32: "Canceled"}


def filas(dv, ruta):
    """Devuelve `value` o lista vacía, sin romper si la consulta no trae nada.

    OJO: en este entorno `asyncoperations?$orderby=createdon desc` llegó a
    devolver 0 filas mientras que el mismo pedido con `asc` devolvía 200. Por eso
    acá nunca se concluye "está vacío" a partir de un solo orden.
    """
    codigo, cuerpo, _ = dv.call("GET", ruta)
    if codigo != 200 or not isinstance(cuerpo, dict):
        print(f"   (HTTP {codigo} en {ruta.split('?')[0]})")
        return []
    return cuerpo.get("value", [])


def resumen_de_la_cola(dv):
    print("=== cola de trabajos del sistema: qué hay y en qué estado ===")
    for orden in ("desc", "asc"):
        f = filas(dv, "asyncoperations?$select=operationtype,statuscode,createdon"
                      f"&$orderby=createdon {orden}&$top=500")
        print(f"\n  orden {orden}: {len(f)} filas")
        if not f:
            continue
        fechas = [x["createdon"] for x in f if x.get("createdon")]
        if fechas:
            print(f"    rango: {min(fechas)[:19]}  →  {max(fechas)[:19]}")
        cuenta = collections.Counter(
            (TIPOS.get(x.get("operationtype"), f"tipo {x.get('operationtype')}"),
             RAZON.get(x.get("statuscode"), "?")) for x in f)
        for (tipo, razon), n in cuenta.most_common(15):
            print(f"    {tipo:30} {razon:22} → {n}")


def entregas(dv):
    print("\n\n=== intentos de entrega a endpoints externos (operationtype 25) ===")
    print("Si un trigger de Dataverse falló al entregar, el motivo está acá.\n")
    encontrado = False
    for orden in ("desc", "asc"):
        f = filas(dv, "asyncoperations?$select=name,statuscode,createdon,startedon,"
                      "completedon,message,friendlymessage,errorcode"
                      f"&$filter=operationtype eq 25&$orderby=createdon {orden}&$top=40")
        if not f:
            continue
        encontrado = True
        print(f"--- orden {orden}: {len(f)} filas ---")
        for x in f:
            texto = (x.get("friendlymessage") or x.get("message") or "").strip()
            print(f"  {x['createdon'][:19]}  {RAZON.get(x.get('statuscode'), '?'):22} "
                  f"errorcode={x.get('errorcode')}  {str(x.get('name'))[:40]}")
            if texto:
                for linea in texto.splitlines()[:8]:
                    print(f"        {linea[:160]}")
        break
    if not encontrado:
        print("  NINGUNA. Dataverse no registró ni un solo intento de entrega.")
        print("  Eso significa que el evento no llega siquiera a encolarse para salir:")
        print("  el problema está antes de la entrega, no en la entrega.")


def fallidos_recientes(dv):
    print("\n\n=== últimos trabajos FALLIDOS o en espera, del tipo que sea ===")
    for etiqueta, filtro in (("fallidos", "statuscode eq 31"), ("en espera", "statuscode eq 10")):
        f = filas(dv, "asyncoperations?$select=name,operationtype,statuscode,createdon,message"
                      f"&$filter={filtro}&$orderby=createdon asc&$top=20")
        print(f"\n  {etiqueta}: {len(f)}")
        for x in f[-10:]:
            texto = (x.get("message") or "").strip().splitlines()
            print(f"    {x['createdon'][:19]} {TIPOS.get(x.get('operationtype'), x.get('operationtype'))} "
                  f"· {str(x.get('name'))[:38]}")
            if texto:
                print(f"        {texto[0][:160]}")


def main():
    dv = Dataverse()
    resumen_de_la_cola(dv)
    entregas(dv)
    fallidos_recientes(dv)
    print("\nListo. Nada de esto modificó el entorno.")


if __name__ == "__main__":
    main()
