#!/usr/bin/env python3
"""Comprobación independiente de los choices globales: exporta la solución
unmanaged por el Web API (acción `ExportSolution`) y compara cada playbook de
`playbooks/choice-global/` contra el XML de `customizations.xml`. Es otro
camino que el de la herramienta de construcción (que verifica por
`GlobalOptionSetDefinitions`): si los dos coinciden, el componente está bien.

Solo lee. Uso:
    python3 herramientas/construir/muestra_choice.py            # compara todos
    python3 herramientas/construir/muestra_choice.py --guardar  # además guarda el XML de cada uno en muestras/
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

from _comun import dividir_secciones, leer_texto, obtener_componente, obtener_identidad  # noqa: E402

TIPO = "choice-global"
COMPONENTE_CHOICE = "9"  # tipo de componente de un choice global en solution.xml


def _etiquetas(nodo, contenedor, hijo):
    """{languagecode: texto} de `<contenedor><hijo description languagecode/>`."""
    c = nodo.find(contenedor)
    if c is None:
        return {}
    return {int(e.get("languagecode")): e.get("description") or "" for e in c.findall(hijo)}


def comparar_con_xml(customizations_xml, datos, lcid):
    """Lista de diferencias (vacía si coincide) entre el playbook y el
    `<optionset>` de ese nombre en `customizations.xml`."""
    raiz = ET.fromstring(customizations_xml)
    nodo = next((o for o in raiz.iter("optionset") if o.get("Name") == datos["nombre"]), None)
    if nodo is None:
        return [f"{datos['nombre']} no está en la solución exportada"]
    difs = []

    def texto_unico(etiquetas, esperado, que):
        otros = sorted(k for k in etiquetas if k != lcid)
        if otros:
            difs.append(f"{que}: tiene etiquetas en otro idioma {otros}")
        if etiquetas.get(lcid, "") != esperado:
            difs.append(f"{que}: xml={etiquetas.get(lcid)!r} playbook={esperado!r}")

    if (nodo.findtext("IsGlobal") or "").strip() != "1":
        difs.append(f"IsGlobal: xml={nodo.findtext('IsGlobal')!r} esperado='1'")
    if (nodo.findtext("OptionSetType") or "").strip().lower() != "picklist":
        difs.append(f"OptionSetType: xml={nodo.findtext('OptionSetType')!r} esperado='picklist'")
    texto_unico(_etiquetas(nodo, "displaynames", "displayname"), datos["displayname"], "displayname")
    texto_unico(_etiquetas(nodo, "Descriptions", "Description"), datos["descripcion"], "descripcion")
    # Los dos atributos del elemento raíz duplican el idioma base.
    if nodo.get("localizedName") != datos["displayname"]:
        difs.append(f"atributo localizedName: xml={nodo.get('localizedName')!r} playbook={datos['displayname']!r}")

    cont = nodo.find("options")
    opciones = [] if cont is None else list(cont)
    if len(opciones) != len(datos["opciones"]):
        difs.append(f"cantidad de opciones: xml={len(opciones)} playbook={len(datos['opciones'])}")
    for i, (op_x, op_p) in enumerate(zip(opciones, datos["opciones"])):
        if op_x.get("value") != str(op_p["valor"]):
            difs.append(f"opciones[{i}].valor: xml={op_x.get('value')!r} playbook={op_p['valor']!r}")
        texto_unico(_etiquetas(op_x, "labels", "label"), op_p["etiqueta"], f"opciones[{i}].etiqueta")
        texto_unico(_etiquetas(op_x, "Descriptions", "Description"), op_p.get("descripcion") or "", f"opciones[{i}].descripcion")
    return difs


def fragmento(customizations_xml, nombre):
    raiz = ET.fromstring(customizations_xml)
    nodo = next((o for o in raiz.iter("optionset") if o.get("Name") == nombre), None)
    return None if nodo is None else ET.tostring(nodo, encoding="unicode")


def main():
    from dataverse_api import Dataverse

    guardar = "--guardar" in sys.argv[1:]
    rutas = sorted(glob.glob(os.path.join(_RAIZ, "playbooks", "choice-global", "*.md")))
    playbooks = []
    for ruta in rutas:
        sec = dividir_secciones(leer_texto(ruta))
        playbooks.append((obtener_componente(sec, TIPO), obtener_identidad(sec)))
    soluciones = {i["solucion"] for _, i in playbooks}
    if len(soluciones) != 1:
        print(f"los playbooks nombran más de una solución: {sorted(soluciones)}")
        return 1
    solucion = soluciones.pop()

    est, cuerpo, _ = Dataverse().call("POST", "ExportSolution", {"SolutionName": solucion, "Managed": False}, timeout=600)
    if est != 200 or not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("ExportSolutionFile"), str):
        print(f"ExportSolution devolvió HTTP {est} o una forma inesperada")
        return 1
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(cuerpo["ExportSolutionFile"])))
    custom = z.read("customizations.xml").decode("utf-8")
    raices = [r for r in ET.fromstring(z.read("solution.xml")).iter("RootComponent") if r.get("type") == COMPONENTE_CHOICE]
    en_solucion = {r.get("schemaName") for r in raices}

    malos = 0
    for datos, identidad in playbooks:
        difs = comparar_con_xml(custom, datos, identidad["lcid"])
        if datos["nombre"] not in en_solucion:
            difs.append("no figura como RootComponent type=9 en solution.xml")
        print(f"{'OK      ' if not difs else 'DIFIERE '} {datos['nombre']}" + ("" if not difs else ": " + "; ".join(difs)))
        malos += bool(difs)
        if guardar:
            frag = fragmento(custom, datos["nombre"])
            if frag:
                destino = os.path.join(_RAIZ, "playbooks", "choice-global", "muestras", f"{datos['nombre']}.solucion.xml")
                open(destino, "w", encoding="utf-8").write(frag + "\n")
    sobran = sorted(en_solucion - {d["nombre"] for d, _ in playbooks})
    if sobran:
        print(f"AVISO: choices en la solución sin playbook: {sobran}")
    print(json.dumps({"playbooks": len(playbooks), "coinciden": len(playbooks) - malos, "difieren": malos, "sin_playbook": len(sobran)}))
    return 0 if not malos and not sobran else 1


if __name__ == "__main__":
    sys.exit(main())
