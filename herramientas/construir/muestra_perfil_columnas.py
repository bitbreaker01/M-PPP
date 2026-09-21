#!/usr/bin/env python3
"""Comprobación independiente de los perfiles de seguridad de columna: exporta
la solución unmanaged por el Web API (`ExportSolution`) y compara cada playbook
de `playbooks/perfil-columnas/` contra `customizations.xml`
(`<FieldSecurityProfiles><FieldSecurityProfile name="…"><FieldPermissions>`).
Es otro camino que el de `perfil_columnas.py`. Solo lee.

    python3 herramientas/construir/muestra_perfil_columnas.py [<playbook.md> …] [--guardar]

Los miembros del perfil (usuarios y equipos) no viajan en la solución: no se
comparan acá ni en ningún lado; son una tarea de administración.
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

from _comun import dividir_secciones, escribir_metadatos, leer_texto, nombre_de_archivo, obtener_componente, obtener_identidad  # noqa: E402

TIPO = "perfil-columnas"
ETIQUETAS = {"leer": "CanRead", "crear": "CanCreate", "actualizar": "CanUpdate"}


def _buscar(raiz, datos):
    return next((p for p in raiz.iter("FieldSecurityProfile") if p.get("name") == datos["nombre"]), None)


def comparar_con_xml(customizations_xml, datos):
    perfil = _buscar(ET.fromstring(customizations_xml), datos)
    if perfil is None:
        return [f"{datos['nombre']} no está en la solución exportada"]
    difs = []
    if (perfil.get("description") or "") != datos["descripcion"]:
        difs.append(f"descripcion: xml={perfil.get('description')!r} playbook={datos['descripcion']!r}")
    contenedor = perfil.find("FieldPermissions")
    reales = {} if contenedor is None else {((f.findtext("EntityName") or "").strip(), (f.findtext("AttributeName") or "").strip()): f for f in contenedor.findall("FieldPermission")}
    for p in datos["permisos"]:
        clave = (p["tabla"], p["columna"])
        if clave not in reales:
            difs.append(f"falta el permiso sobre {p['tabla']}.{p['columna']}")
            continue
        esperado = {etiqueta: "4" if p[campo] else "0" for campo, etiqueta in ETIQUETAS.items()}
        esperado["CanReadUnmasked"] = "0"
        for etiqueta, valor in esperado.items():
            real = (reales[clave].findtext(etiqueta) or "").strip()
            if real != valor:
                difs.append(f"{p['tabla']}.{p['columna']}.{etiqueta}: xml={real!r} playbook={valor!r}")
    declarados = {(p["tabla"], p["columna"]) for p in datos["permisos"]}
    difs += [f"sobra el permiso sobre {t}.{c}: el playbook no lo declara" for t, c in sorted(reales) if (t, c) not in declarados]
    return difs


def main():
    from dataverse_api import Dataverse

    argv = sys.argv[1:]
    guardar = "--guardar" in argv
    rutas = [a for a in argv if not a.startswith("--")] or sorted(glob.glob(os.path.join(_RAIZ, "playbooks", "perfil-columnas", "*.md")))
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
    for datos, _ in playbooks:
        difs = comparar_con_xml(custom, datos)
        print(f"{'OK      ' if not difs else 'DIFIERE '} {datos['nombre']}" + ("" if not difs else ": " + "; ".join(difs)))
        malos += bool(difs)
        if guardar:
            perfil = _buscar(raiz, datos)
            if perfil is not None:
                os.makedirs(os.path.join(_RAIZ, "playbooks", "perfil-columnas", "muestras"), exist_ok=True)
                archivo = nombre_de_archivo(datos["nombre"]) + ".solucion.xml"
                open(os.path.join(_RAIZ, "playbooks", "perfil-columnas", "muestras", archivo), "w", encoding="utf-8").write(ET.tostring(perfil, encoding="unicode") + "\n")
    print(json.dumps({"playbooks": len(playbooks), "coinciden": len(playbooks) - malos, "difieren": malos}))
    return 0 if not malos else 1


if __name__ == "__main__":
    sys.exit(main())
