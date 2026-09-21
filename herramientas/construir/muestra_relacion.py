#!/usr/bin/env python3
"""Comprobación independiente de las relaciones: exporta la solución unmanaged
por el Web API (`ExportSolution`) y compara cada playbook de
`playbooks/relacion/` contra `customizations.xml` (la relación, en
`<EntityRelationships>`; su lookup, dentro de la tabla hija). Es otro camino
que el de `relacion.py`. Solo lee.

    python3 herramientas/construir/muestra_relacion.py [<playbook.md> …] [--guardar]
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
from relacion import CASCADAS  # noqa: E402

TIPO = "relacion"
# En el XML no existe CascadeMerge; las demás acciones se llaman Cascade<Acción>.
ACCIONES_XML = ["Assign", "Delete", "Reparent", "Share", "Unshare", "RollupView"]


def _etiqueta(nodo, contenedor, hijo, lcid, que, esperado, difs):
    c = nodo.find(contenedor) if nodo is not None else None
    etiquetas = {} if c is None else {int(e.get("languagecode")): e.get("description") or "" for e in c.findall(hijo)}
    otros = sorted(k for k in etiquetas if k != lcid)
    if otros:
        difs.append(f"{que}: tiene etiquetas en otro idioma {otros}")
    if etiquetas.get(lcid, "") != esperado:
        difs.append(f"{que}: xml={etiquetas.get(lcid)!r} playbook={esperado!r}")


def comparar_con_xml(customizations_xml, datos, lcid):
    raiz = ET.fromstring(customizations_xml)
    rel = next((r for r in raiz.iter("EntityRelationship") if r.get("Name") == datos["nombre"]), None)
    if rel is None:
        return [f"{datos['nombre']} no está en la solución exportada"]
    difs, k = [], datos["lookup"]

    def igual(nodo, etiqueta, esperado, que):
        real = (nodo.findtext(etiqueta) or "").strip()
        if real != str(esperado):
            difs.append(f"{que}: xml={real!r} playbook={str(esperado)!r}")

    igual(rel, "EntityRelationshipType", "OneToMany", "tipo de relación")
    igual(rel, "ReferencedEntityName", datos["tabla_padre"], "tabla_padre")
    igual(rel, "ReferencingEntityName", datos["tabla_hija"], "tabla_hija")
    igual(rel, "ReferencingAttributeName", k["nombre"], "lookup.nombre")
    for accion in ACCIONES_XML:
        igual(rel, f"Cascade{accion}", CASCADAS[datos["comportamiento"]][accion], f"comportamiento ({accion})")

    hija = next((e for e in raiz.iter("entity") if e.get("Name") == datos["tabla_hija"]), None)
    attrs = hija.find("attributes") if hija is not None else None
    col = None if attrs is None else next((a for a in attrs if a.findtext("LogicalName") == k["nombre"]), None)
    if col is None:
        difs.append(f"falta la columna lookup {k['nombre']} en {datos['tabla_hija']}")
        return difs
    igual(col, "Type", "lookup", "lookup.tipo")
    igual(col, "RequiredLevel", "required" if k["requerida"] else "none", "lookup.requerida")
    igual(col, "IsAuditEnabled", int(k["auditoria"]), "lookup.auditoria")
    igual(col, "IsSecured", 0, "lookup.protegida")
    _etiqueta(col, "displaynames", "displayname", lcid, "lookup.displayname", k["displayname"], difs)
    _etiqueta(col, "Descriptions", "Description", lcid, "lookup.descripcion", k["descripcion"], difs)
    return difs


def main():
    from dataverse_api import Dataverse

    argv = sys.argv[1:]
    guardar = "--guardar" in argv
    rutas = [a for a in argv if not a.startswith("--")] or sorted(glob.glob(os.path.join(_RAIZ, "playbooks", "relacion", "*.md")))
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
    custom = zipfile.ZipFile(io.BytesIO(base64.b64decode(cuerpo["ExportSolutionFile"]))).read("customizations.xml").decode("utf-8")
    raiz = ET.fromstring(custom)
    malos = 0
    for datos, identidad in playbooks:
        difs = comparar_con_xml(custom, datos, identidad["lcid"])
        print(f"{'OK      ' if not difs else 'DIFIERE '} {datos['nombre']}" + ("" if not difs else ": " + "; ".join(difs)))
        malos += bool(difs)
        if guardar:
            rel = next((r for r in raiz.iter("EntityRelationship") if r.get("Name") == datos["nombre"]), None)
            if rel is not None:
                os.makedirs(os.path.join(_RAIZ, "playbooks", "relacion", "muestras"), exist_ok=True)
                open(os.path.join(_RAIZ, "playbooks", "relacion", "muestras", f"{datos['nombre']}.solucion.xml"), "w", encoding="utf-8").write(ET.tostring(rel, encoding="unicode") + "\n")
    print(json.dumps({"playbooks": len(playbooks), "coinciden": len(playbooks) - malos, "difieren": malos}))
    return 0 if not malos else 1


if __name__ == "__main__":
    sys.exit(main())
