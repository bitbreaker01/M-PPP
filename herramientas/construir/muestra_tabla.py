#!/usr/bin/env python3
"""Comprobación independiente de las tablas: exporta la solución unmanaged por
el Web API (`ExportSolution`) y compara cada playbook de `playbooks/tabla/`
contra el XML de `customizations.xml`. Es otro camino que el de `tabla.py`
(que verifica por `EntityDefinitions`): si los dos coinciden, la tabla está
bien. Solo lee.

    python3 herramientas/construir/muestra_tabla.py [<playbook.md> …] [--guardar]

Sin playbooks, compara todos los de `playbooks/tabla/` (no los de `ensayos/`).
Con `--guardar`, deja el XML real de cada tabla en `playbooks/tabla/muestras/`.
"""
import base64
import glob
import io
import json
import os
import sys
import xml.etree.ElementTree as ET
import zipfile

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)
sys.path.insert(0, os.path.dirname(_AQUI))

from _comun import dividir_secciones, escribir_metadatos, leer_texto, obtener_componente, obtener_identidad  # noqa: E402

TIPO = "tabla"
COMPONENTE_TABLA = "1"
# Cómo se ve cada tipo del playbook en el XML de la solución (observado, 2026-09-20).
TIPO_XML = {"texto": "nvarchar", "autonumerico": "nvarchar", "memo": "ntext", "entero": "int", "choice": "picklist",
            "sino": "bit", "fecha": "datetime", "fechahora": "datetime", "archivo": "file"}
PROPIEDAD_XML = {"usuario": "UserOwned", "organizacion": "OrgOwned"}
NO_DECLARABLES = {"lookup", "owner", "primarykey", "uniqueidentifier", "virtual"}


def _etiquetas(nodo, contenedor, hijo):
    c = nodo.find(contenedor) if nodo is not None else None
    return {} if c is None else {int(e.get("languagecode")): e.get("description") or "" for e in c.findall(hijo)}


def comparar_con_xml(customizations_xml, datos, lcid):
    raiz = ET.fromstring(customizations_xml)
    ent = next((e for e in raiz.iter("entity") if e.get("Name") == datos["nombre"]), None)
    if ent is None:
        return [f"{datos['nombre']} no está en la solución exportada"]
    difs = []

    def texto(etiquetas, esperado, que):
        otros = sorted(k for k in etiquetas if k != lcid)
        if otros:
            difs.append(f"{que}: tiene etiquetas en otro idioma {otros}")
        if etiquetas.get(lcid, "") != esperado:
            difs.append(f"{que}: xml={etiquetas.get(lcid)!r} playbook={esperado!r}")

    def igual(nodo, etiqueta, esperado, que):
        real = (nodo.findtext(etiqueta) or "").strip()
        if real != str(esperado):
            difs.append(f"{que}: xml={real!r} playbook={str(esperado)!r}")

    texto(_etiquetas(ent, "LocalizedNames", "LocalizedName"), datos["displayname"], "displayname")
    texto(_etiquetas(ent, "LocalizedCollectionNames", "LocalizedCollectionName"), datos["displayname_plural"], "displayname_plural")
    texto(_etiquetas(ent, "Descriptions", "Description"), datos["descripcion"], "descripcion")
    igual(ent, "OwnershipTypeMask", PROPIEDAD_XML[datos["propiedad"]], "propiedad")
    igual(ent, "IsAuditEnabled", int(datos["auditoria"]), "auditoria de la tabla")

    cont = ent.find("attributes")
    attrs = {a.findtext("LogicalName"): a for a in ([] if cont is None else list(cont))}
    p = datos["primaria"]
    declaradas = [{**p, "tipo": "autonumerico" if p["autonumerico"] else "texto", "formato": p["autonumerico"],
                   "protegida": False, "auditoria": datos["auditoria"], "_clave_formato": "autonumerico"}] + list(datos["columnas"])
    for c in declaradas:
        n, a = c["nombre"], attrs.get(c["nombre"])
        if a is None:
            difs.append(f"falta la columna {n}")
            continue
        tipo = c["tipo"]
        igual(a, "Type", TIPO_XML[tipo], f"{n}.tipo")
        if (a.findtext("Type") or "") != TIPO_XML[tipo]:
            continue
        igual(a, "RequiredLevel", "required" if c["requerida"] else "none", f"{n}.requerida")
        igual(a, "IsSecured", int(c["protegida"]), f"{n}.protegida")
        igual(a, "IsAuditEnabled", int(c["auditoria"]), f"{n}.auditoria")
        texto(_etiquetas(a, "displaynames", "displayname"), c["displayname"], f"{n}.displayname")
        texto(_etiquetas(a, "Descriptions", "Description"), c["descripcion"], f"{n}.descripcion")
        if tipo in ("texto", "autonumerico", "memo"):
            igual(a, "MaxLength", c["largo"], f"{n}.largo")
        if tipo in ("texto", "autonumerico"):
            igual(a, "AutoNumberFormat", c.get("formato") or "", f"{n}.{c.get('_clave_formato', 'formato')}")
        elif tipo == "entero":
            igual(a, "MinValue", c["minimo"], f"{n}.minimo")
            igual(a, "MaxValue", c["maximo"], f"{n}.maximo")
        elif tipo == "choice":
            igual(a, "OptionSetName", c["choice"], f"{n}.choice")
        elif tipo == "sino":
            igual(a, "AppDefaultValue", int(c["defecto"]), f"{n}.defecto")
        elif tipo == "archivo":
            igual(a, "MaxValue", c["tamano_kb"], f"{n}.tamano_kb")  # en el XML el tamaño de un archivo es <MaxValue>
        elif tipo in ("fecha", "fechahora"):
            igual(a, "Format", "date" if tipo == "fecha" else "datetime", f"{n}.tipo (formato de la fecha)")
            igual(a, "Behavior", 2 if tipo == "fecha" else 1, f"{n}.tipo (comportamiento: 1 usuario local, 2 fecha sola)")

    nombres = {c["nombre"] for c in declaradas}
    for n, a in sorted(attrs.items()):
        if a.findtext("IsCustomField") == "1" and n not in nombres and (a.findtext("Type") or "") not in NO_DECLARABLES:
            difs.append(f"columna propia que el playbook no declara: {n} ({a.findtext('Type')})")
    return difs


def fragmento(customizations_xml, nombre):
    raiz = ET.fromstring(customizations_xml)
    for e in raiz.iter("Entity"):
        if e.findtext("Name") == nombre:
            return ET.tostring(e, encoding="unicode")
    return None


def main():
    from dataverse_api import Dataverse

    argv = sys.argv[1:]
    guardar = "--guardar" in argv
    rutas = [a for a in argv if not a.startswith("--")] or sorted(glob.glob(os.path.join(_RAIZ, "playbooks", "tabla", "*.md")))
    playbooks = []
    for ruta in rutas:
        sec = dividir_secciones(leer_texto(ruta))
        playbooks.append((obtener_componente(sec, TIPO), obtener_identidad(sec)))
    soluciones = {i["solucion"] for _, i in playbooks}
    if len(soluciones) != 1:
        print(f"los playbooks nombran {len(soluciones)} soluciones: {sorted(soluciones)}; se compara de a una")
        return 1
    solucion = soluciones.pop()
    est, cuerpo, _ = escribir_metadatos(Dataverse(), "POST", "ExportSolution", {"SolutionName": solucion, "Managed": False}, timeout=900)
    if est != 200 or not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("ExportSolutionFile"), str):
        print(f"ExportSolution devolvió HTTP {est} o una forma inesperada")
        return 1
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(cuerpo["ExportSolutionFile"])))
    custom = z.read("customizations.xml").decode("utf-8")
    en_solucion = {r.get("schemaName") for r in ET.fromstring(z.read("solution.xml")).iter("RootComponent") if r.get("type") == COMPONENTE_TABLA}
    malos = 0
    for datos, identidad in playbooks:
        difs = comparar_con_xml(custom, datos, identidad["lcid"])
        if datos["nombre"] not in en_solucion:
            difs.append("no figura como RootComponent type=1 en solution.xml")
        print(f"{'OK      ' if not difs else 'DIFIERE '} {datos['nombre']}" + ("" if not difs else ": " + "; ".join(difs)))
        malos += bool(difs)
        if guardar:
            frag = fragmento(custom, datos["nombre"])
            if frag:
                os.makedirs(os.path.join(_RAIZ, "playbooks", "tabla", "muestras"), exist_ok=True)
                open(os.path.join(_RAIZ, "playbooks", "tabla", "muestras", f"{datos['nombre']}.solucion.xml"), "w", encoding="utf-8").write(frag + "\n")
    print(json.dumps({"playbooks": len(playbooks), "coinciden": len(playbooks) - malos, "difieren": malos}))
    return 0 if not malos else 1


if __name__ == "__main__":
    sys.exit(main())
