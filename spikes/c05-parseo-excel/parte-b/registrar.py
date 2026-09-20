#!/usr/bin/env python3
"""Registro de los componentes del spike C-05 parte B contra Dev, paso a paso y
re-ejecutable (cada paso comprueba si su componente ya existe antes de crearlo).

Uso:
    python3 spikes/c05-parseo-excel/parte-b/registrar.py tabla
    python3 spikes/c05-parseo-excel/parte-b/registrar.py clave
    python3 spikes/c05-parseo-excel/parte-b/registrar.py customapi
    python3 spikes/c05-parseo-excel/parte-b/registrar.py paquete <ruta-al-nupkg>
    python3 spikes/c05-parseo-excel/parte-b/registrar.py step
    python3 spikes/c05-parseo-excel/parte-b/registrar.py todo <ruta-al-nupkg>
"""
import base64
import os
import sys
import time

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))
from dataverse_api import Dataverse  # noqa: E402

SOLUCION = "sanic_mppp_sol_zzspikec05"
PUBLISHER_PREFIX = "sanic"
TABLA_SCHEMA = "sanic_mppp_tbl_zzspike"
TABLA_LOGICAL = "sanic_mppp_tbl_zzspike"
CLAVE_SCHEMA = "sanic_mppp_key_zzspike_clave"
CUSTOMAPI_UNIQUENAME = "sanic_mppp_capi_zzspikec05"
PAQUETE_UNIQUENAME = "sanic_mppp_pkg_zzspikec05"
NAMESPACE_RAIZ = "Sanic.Mppp.Plugins.Zzspikec05"


def label(texto):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": texto, "LanguageCode": 1033}
        ],
    }


def paso_tabla(dv):
    print(f"== Tabla {TABLA_LOGICAL} ==")
    estado, cuerpo, _ = dv.call("GET", f"EntityDefinitions(LogicalName='{TABLA_LOGICAL}')?$select=LogicalName")
    if estado == 200:
        print("  ya existe, no se recrea")
        return True

    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": TABLA_SCHEMA,
        "DisplayName": label("ZZ Spike C05"),
        "DisplayCollectionName": label("ZZ Spike C05"),
        "Description": label("Tabla descartable del spike C-05 parte B. No pertenece al producto."),
        "OwnershipType": "UserOwned",
        "HasActivities": False,
        "HasNotes": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": "sanic_nombre",
                "DisplayName": label("Nombre"),
                "RequiredLevel": {"Value": "None", "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"},
                "MaxLength": 200,
                "FormatName": {"Value": "Text"},
                "IsPrimaryName": True,
            }
        ],
    }
    estado, cuerpo, cabeceras = dv.call("POST", "EntityDefinitions", body, solucion=SOLUCION)
    if estado not in (201, 204):
        print(f"  [FALLO] crear tabla: {estado} {cuerpo}")
        return False
    print("  OK tabla creada")

    # Espera a que el metadata este disponible antes de agregar columnas (creacion async).
    for intento in range(20):
        estado, _, _ = dv.call("GET", f"EntityDefinitions(LogicalName='{TABLA_LOGICAL}')?$select=LogicalName")
        if estado == 200:
            break
        time.sleep(3)
    else:
        print("  [FALLO] la tabla no aparecio en metadata tras esperar")
        return False

    return paso_columnas(dv)


def paso_columnas(dv):
    print(f"== Columnas de {TABLA_LOGICAL} ==")
    columnas = [
        {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "sanic_clave",
            "DisplayName": label("Clave"),
            "Description": label("Columna de prueba para la pregunta 6 (clave alternativa, sensibilidad a mayusculas)."),
            "RequiredLevel": {"Value": "None", "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"},
            "MaxLength": 100,
            "FormatName": {"Value": "Text"},
        },
        {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "sanic_actorcapturado",
            "DisplayName": label("Actor capturado"),
            "Description": label("UserId/InitiatingUserId capturados por el step de Update, para la pregunta 5."),
            "RequiredLevel": {"Value": "None", "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"},
            "MaxLength": 500,
            "FormatName": {"Value": "Text"},
        },
        {
            "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
            "SchemaName": "sanic_actordetalle",
            "DisplayName": label("Actor detalle"),
            "Description": label("Cadena completa de ParentContext y busqueda de SharedVariables, para la pregunta 5 bis."),
            "RequiredLevel": {"Value": "None", "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"},
            "MaxLength": 4000,
        },
    ]
    ok = True
    for col in columnas:
        schema = col["SchemaName"]
        logical = schema.lower()
        estado, _, _ = dv.call(
            "GET",
            f"EntityDefinitions(LogicalName='{TABLA_LOGICAL}')/Attributes(LogicalName='{logical}')?$select=LogicalName",
        )
        if estado == 200:
            print(f"  {schema}: ya existe")
            continue
        estado, cuerpo, _ = dv.call(
            "POST",
            f"EntityDefinitions(LogicalName='{TABLA_LOGICAL}')/Attributes",
            col,
            solucion=SOLUCION,
        )
        if estado in (201, 204):
            print(f"  OK columna creada: {schema}")
        else:
            print(f"  [FALLO] columna {schema}: {estado} {cuerpo}")
            ok = False
    return ok


def paso_clave(dv):
    print(f"== Clave alternativa {CLAVE_SCHEMA} ==")
    estado, cuerpo, _ = dv.call(
        "GET",
        f"EntityDefinitions(LogicalName='{TABLA_LOGICAL}')/Keys?$select=SchemaName,EntityKeyIndexStatus",
    )
    if estado == 200:
        for k in cuerpo.get("value", []):
            if k["SchemaName"] == CLAVE_SCHEMA:
                print(f"  ya existe, estado de indice: {k.get('EntityKeyIndexStatus')}")
                return True

    body = {
        "SchemaName": CLAVE_SCHEMA,
        "DisplayName": label("KEY - MPPP - ZZ Spike C05 - Clave"),
        "KeyAttributes": ["sanic_clave"],
    }
    estado, cuerpo, _ = dv.call(
        "POST",
        f"EntityDefinitions(LogicalName='{TABLA_LOGICAL}')/Keys",
        body,
        solucion=SOLUCION,
    )
    if estado not in (201, 204):
        print(f"  [FALLO] crear clave: {estado} {cuerpo}")
        return False
    print("  OK solicitada (la activacion del indice es asincrona)")
    return True


def esperar_clave_activa(dv, minutos=10):
    print(f"== Esperando activacion de {CLAVE_SCHEMA} (hasta {minutos} min) ==")
    limite = time.time() + minutos * 60
    while time.time() < limite:
        estado, cuerpo, _ = dv.call(
            "GET",
            f"EntityDefinitions(LogicalName='{TABLA_LOGICAL}')/Keys?$select=SchemaName,EntityKeyIndexStatus",
        )
        if estado == 200:
            for k in cuerpo.get("value", []):
                if k["SchemaName"] == CLAVE_SCHEMA:
                    print(f"  estado actual: {k.get('EntityKeyIndexStatus')}")
                    if k.get("EntityKeyIndexStatus") == "Active":
                        return True
        time.sleep(20)
    print("  NO CONCLUYENTE: el indice no quedo activo dentro del tiempo de espera")
    return False


def paso_customapi(dv):
    print(f"== Custom API {CUSTOMAPI_UNIQUENAME} ==")
    estado, cuerpo, _ = dv.call(
        "GET", f"customapis?$select=customapiid&$filter=uniquename eq '{CUSTOMAPI_UNIQUENAME}'"
    )
    if estado == 200 and cuerpo.get("value"):
        capiid = cuerpo["value"][0]["customapiid"]
        print(f"  ya existe: {capiid}")
        return capiid

    body = {
        "uniquename": CUSTOMAPI_UNIQUENAME,
        "name": "CAPI - MPPP - ZZ Spike C05",
        "displayname": "CAPI - MPPP - ZZ Spike C05",
        "description": "Custom API descartable del spike C-05 parte B. Dispatch por 'modo': lector | atomicidad | actor.",
        "bindingtype": 0,  # Global (unbound)
        "isfunction": False,
        "isprivate": True,
        "allowedcustomprocessingsteptype": 0,  # None
        "executeprivilegename": None,
    }
    estado, cuerpo, cabeceras = dv.call("POST", "customapis", body, solucion=SOLUCION)
    if estado not in (201, 204):
        print(f"  [FALLO] crear custom api: {estado} {cuerpo}")
        return None
    capiid = Dataverse.id_creado(cabeceras)
    print(f"  OK creada: {capiid}")
    return capiid


TIPO_STRING = 10
TIPO_GUID = 12
TIPO_INTEGER = 7


def paso_parametros_customapi(dv, capiid):
    print("== Parametros de la Custom API ==")
    entrada = [
        ("modo", "CAPI_IP - MPPP - ZZ Spike C05 - Modo", TIPO_STRING, 100, True),
        ("excelbase64", "CAPI_IP - MPPP - ZZ Spike C05 - Excel base64", TIPO_STRING, 100, False),
        ("zzspikeid", "CAPI_IP - MPPP - ZZ Spike C05 - Id de fila", TIPO_GUID, 100, False),
        ("cantidadfilas", "CAPI_IP - MPPP - ZZ Spike C05 - Cantidad de filas", TIPO_INTEGER, 100, False),
    ]
    salida = [
        ("resultado", "CAPI_OP - MPPP - ZZ Spike C05 - Resultado", TIPO_STRING, 100),
        ("milisegundos", "CAPI_OP - MPPP - ZZ Spike C05 - Milisegundos", TIPO_INTEGER, 100),
    ]
    ok = True
    estado, cuerpo, _ = dv.call(
        "GET", f"customapirequestparameters?$select=uniquename&$filter=_customapiid_value eq {capiid}"
    )
    existentes_in = {r["uniquename"] for r in cuerpo.get("value", [])} if estado == 200 else set()
    for uniquename, displayname, tipo, orden, requerido in entrada:
        if uniquename in existentes_in:
            print(f"  parametro entrada '{uniquename}': ya existe")
            continue
        body = {
            "uniquename": uniquename,
            "name": f"{NAMESPACE_RAIZ}.capiip.{uniquename}",
            "displayname": displayname,
            "type": tipo,
            "isoptional": not requerido,
            "CustomAPIId@odata.bind": f"/customapis({capiid})",
        }
        estado, cuerpo, _ = dv.call("POST", "customapirequestparameters", body, solucion=SOLUCION)
        if estado in (201, 204):
            print(f"  OK parametro entrada: {uniquename}")
        else:
            print(f"  [FALLO] parametro entrada {uniquename}: {estado} {cuerpo}")
            ok = False

    estado, cuerpo, _ = dv.call(
        "GET", f"customapiresponseproperties?$select=uniquename&$filter=_customapiid_value eq {capiid}"
    )
    existentes_out = {r["uniquename"] for r in cuerpo.get("value", [])} if estado == 200 else set()
    for uniquename, displayname, tipo, orden in salida:
        if uniquename in existentes_out:
            print(f"  parametro salida '{uniquename}': ya existe")
            continue
        body = {
            "uniquename": uniquename,
            "name": f"{NAMESPACE_RAIZ}.capiop.{uniquename}",
            "displayname": displayname,
            "type": tipo,
            "CustomAPIId@odata.bind": f"/customapis({capiid})",
        }
        estado, cuerpo, _ = dv.call("POST", "customapiresponseproperties", body, solucion=SOLUCION)
        if estado in (201, 204):
            print(f"  OK parametro salida: {uniquename}")
        else:
            print(f"  [FALLO] parametro salida {uniquename}: {estado} {cuerpo}")
            ok = False
    return ok


def paso_paquete(dv, ruta_nupkg):
    print(f"== Paquete de plugins {PAQUETE_UNIQUENAME} ==")
    estado, cuerpo, _ = dv.call(
        "GET", f"pluginpackages?$select=pluginpackageid&$filter=uniquename eq '{PAQUETE_UNIQUENAME}'"
    )
    if estado == 200 and cuerpo.get("value"):
        print(f"  ya existe: {cuerpo['value'][0]['pluginpackageid']}")
        return cuerpo["value"][0]["pluginpackageid"]

    with open(ruta_nupkg, "rb") as f:
        contenido = base64.b64encode(f.read()).decode("ascii")
    print(f"  .nupkg: {os.path.getsize(ruta_nupkg) / 1024:.1f} KB, base64: {len(contenido) / 1024:.1f} KB")

    body = {
        "name": PAQUETE_UNIQUENAME,
        "uniquename": PAQUETE_UNIQUENAME,
        "version": "1.0.0.0",
        "content": contenido,
    }
    estado, cuerpo, cabeceras = dv.call("POST", "pluginpackages", body, solucion=SOLUCION, timeout=180)
    if estado not in (201, 204):
        print(f"  [FALLO] registrar paquete: {estado} {cuerpo}")
        return None
    pkgid = Dataverse.id_creado(cabeceras)
    print(f"  OK registrado: {pkgid}")
    return pkgid


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dv = Dataverse()
    accion = sys.argv[1]

    if accion == "tabla":
        ok = paso_tabla(dv)
    elif accion == "clave":
        ok = paso_clave(dv)
    elif accion == "esperar-clave":
        ok = esperar_clave_activa(dv)
    elif accion == "customapi":
        capiid = paso_customapi(dv)
        ok = bool(capiid) and paso_parametros_customapi(dv, capiid)
    elif accion == "paquete":
        ok = bool(paso_paquete(dv, sys.argv[2]))
    else:
        sys.exit(f"accion desconocida: {accion}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
