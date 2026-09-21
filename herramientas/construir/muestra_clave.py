#!/usr/bin/env python3
"""Comprobación independiente de las claves alternativas: exporta la solución
unmanaged por el Web API (`ExportSolution`) y compara cada playbook de
`playbooks/clave/` contra `customizations.xml` (la clave, en `<EntityKeys>`
dentro de su tabla). Es otro camino que el de `clave.py`. Solo lee.

    python3 herramientas/construir/muestra_clave.py [<playbook.md> …] [--guardar]

El XML no dice si el índice está activo: eso solo lo sabe el Web API
(`EntityKeyIndexStatus`), y lo comprueba `clave.py --solo-verificar`.
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

TIPO = "clave"


def _buscar(raiz, datos):
    tabla = next((e for e in raiz.iter("entity") if (e.get("Name") or "").lower() == datos["tabla"]), None)
    claves = None if tabla is None else tabla.find("EntityKeys")
    return None if claves is None else next((k for k in claves.findall("EntityKey") if k.findtext("LogicalName") == datos["nombre"]), None)


def comparar_con_xml(customizations_xml, datos, lcid):
    clave = _buscar(ET.fromstring(customizations_xml), datos)
    if clave is None:
        return [f"{datos['nombre']} no está en la solución exportada, dentro de {datos['tabla']}"]
    difs = []
    contenedor = clave.find("EntityKeyAttributes")
    columnas = [] if contenedor is None else [(a.text or "").strip() for a in contenedor.findall("AttributeName")]
    # La plataforma escribe las columnas en su propio orden: la unicidad no depende del orden.
    if sorted(columnas) != sorted(datos["columnas"]):
        difs.append(f"columnas: xml={sorted(columnas)!r} playbook={sorted(datos['columnas'])!r}")
    nombres = clave.find("displaynames")
    etiquetas = {} if nombres is None else {int(e.get("languagecode")): e.get("description") or "" for e in nombres.findall("displayname")}
    if etiquetas.get(lcid, "") != datos["displayname"]:
        difs.append(f"displayname: xml={etiquetas.get(lcid)!r} playbook={datos['displayname']!r}")
    otros = sorted(k for k in etiquetas if k != lcid)
    if otros:
        difs.append(f"displayname: tiene etiquetas en otro idioma {otros}")
    return difs


def main():
    from dataverse_api import Dataverse

    argv = sys.argv[1:]
    guardar = "--guardar" in argv
    rutas = [a for a in argv if not a.startswith("--")] or sorted(glob.glob(os.path.join(_RAIZ, "playbooks", "clave", "*.md")))
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
            clave = _buscar(raiz, datos)
            if clave is not None:
                os.makedirs(os.path.join(_RAIZ, "playbooks", "clave", "muestras"), exist_ok=True)
                open(os.path.join(_RAIZ, "playbooks", "clave", "muestras", f"{datos['nombre']}.solucion.xml"), "w", encoding="utf-8").write(ET.tostring(clave, encoding="unicode") + "\n")
    print(json.dumps({"playbooks": len(playbooks), "coinciden": len(playbooks) - malos, "difieren": malos}))
    return 0 if not malos else 1


if __name__ == "__main__":
    sys.exit(main())
