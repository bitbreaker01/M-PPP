#!/usr/bin/env python3
"""Construye UN web resource de Dataverse desde un playbook de tipo
`web-resource`. Contrato: `power-platform-construir`; Learn, "Web resources".

    python3 herramientas/construir/web_resource.py <playbook.md> [--solo-verificar] [--completar]

El contenido NO va escrito dentro del playbook: el playbook apunta a un archivo
del repositorio y la herramienta lo sube. Así el SVG o el JavaScript se edita,
se revisa y se versiona como lo que es —un archivo— y no como una tira de
base64 que nadie puede leer en un diff.

Learn, textual: *"It is not necessary to publish Web resources when they are
created. It is necessary to publish them when they are updated."* La
herramienta publica solo cuando hizo un `PATCH`.

Última línea de la salida: JSON de una línea con `estado`
(creado | ya_existia | difiere | bloqueado | error), `componente`, `detalle`.
"""
import base64
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, _AQUI)
sys.path.insert(0, os.path.dirname(_AQUI))

from _comun import (  # noqa: E402
    Bloqueado,
    ErrorEntorno,
    ErrorPlaybook,
    Rastro,
    comprobar_solucion_e_idioma,
    dividir_secciones,
    escribir_metadatos,
    exigir_forma,
    exigir_sin_tildes,
    leer_entorno,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
)

TIPO = "web-resource"
CONJUNTO = "webresourceset"  # OJO: NO es "webresources" (Learn, EntitySetName)

# Learn, tabla WebResource (verificado 2026-09-22).
TIPOS_DE_RECURSO = {"HTML": 1, "CSS": 2, "JS": 3, "XML": 4, "PNG": 5, "JPG": 6, "GIF": 7,
                    "XSL": 9, "ICO": 10, "SVG": 11, "RESX": 12}
# Con qué extensión tiene que estar guardado cada tipo: un SVG en un archivo
# `.png` se sube igual y se ve roto recién en la app.
EXTENSIONES = {"HTML": ".html", "CSS": ".css", "JS": ".js", "XML": ".xml", "PNG": ".png",
               "JPG": ".jpg", "GIF": ".gif", "XSL": ".xsl", "ICO": ".ico", "SVG": ".svg", "RESX": ".resx"}

LARGO_NOMBRE = 256
LARGO_DISPLAYNAME = 200
MAXIMO_BYTES = 5 * 1024 * 1024

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "displayname": str, "descripcion": str, "recurso": str, "archivo": str}

C_RECURSO = "la consulta del web resource (GET webresourceset)"
C_COMPONENTES = "la consulta de pertenencia a la solución (GET solutioncomponents)"


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _caracteres_de_nombre(texto):
    """Un nombre de web resource admite letras y dígitos ASCII, guión bajo,
    punto, guión y barra (las barras arman carpetas virtuales)."""
    return all(("a" <= c <= "z") or ("A" <= c <= "Z") or ("0" <= c <= "9") or c in "_.-/" for c in texto)


def _validar_estructura(datos, identidad):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"el bloque del web resource no tiene las claves esperadas: {'; '.join(partes)}")
    for clave, tipo in CLAVES.items():
        exigir_forma(datos[clave], tipo, "el bloque del web resource", clave, no_vacio=True)
    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    recurso = datos["recurso"]
    if recurso not in TIPOS_DE_RECURSO:
        raise ErrorPlaybook(f"recurso = {recurso!r} no es válido; los válidos son {sorted(TIPOS_DE_RECURSO)}")

    nombre = datos["nombre"]
    prefijo = f"{identidad['prefijo']}_{identidad['abrev']}_wr_{recurso.lower()}_"
    if not nombre.startswith(prefijo):
        raise ErrorPlaybook(f"nombre = {nombre!r} no sigue el patrón {prefijo}<nombre> (`01-convenciones.md` §2)")
    if not _caracteres_de_nombre(nombre):
        raise ErrorPlaybook(f"nombre = {nombre!r} solo admite letras y dígitos ASCII, guión bajo, punto, guión y barra")
    if len(nombre) > LARGO_NOMBRE:
        raise ErrorPlaybook(f"nombre tiene {len(nombre)} caracteres; el máximo es {LARGO_NOMBRE}")

    exigir_sin_tildes(datos["displayname"], "displayname")
    if len(datos["displayname"]) > LARGO_DISPLAYNAME:
        raise ErrorPlaybook(f"displayname tiene {len(datos['displayname'])} caracteres; el máximo es {LARGO_DISPLAYNAME}")

    archivo = datos["archivo"]
    if os.path.isabs(archivo) or ".." in archivo.split("/"):
        raise ErrorPlaybook(f"archivo = {archivo!r} tiene que ser una ruta relativa a la raíz del repositorio, sin '..'")
    esperada = EXTENSIONES[recurso]
    if not archivo.lower().endswith(esperada):
        raise ErrorPlaybook(
            f"archivo = {archivo!r} no termina en '{esperada}', que es la extensión de un recurso {recurso}")


def validar_playbook(datos, identidad):
    _validar_estructura(datos, identidad)


def leer_archivo(ruta_relativa):
    """El contenido desde el repositorio, en base64. Que falte el archivo es
    `Bloqueado`, no un error del playbook: el playbook está bien, falta el
    archivo al lado."""
    ruta = os.path.join(_RAIZ, ruta_relativa)
    if not os.path.isfile(ruta):
        raise Bloqueado(f"no existe el archivo '{ruta_relativa}' que el playbook quiere subir")
    with open(ruta, "rb") as f:
        crudo = f.read()
    if not crudo:
        raise Bloqueado(f"el archivo '{ruta_relativa}' está vacío")
    if len(crudo) > MAXIMO_BYTES:
        raise Bloqueado(f"el archivo '{ruta_relativa}' pesa {len(crudo)} bytes, más que el tope de {MAXIMO_BYTES}")
    return crudo, base64.b64encode(crudo).decode("ascii")


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
def _leer_recurso(dv, nombre):
    ruta = (f"{CONJUNTO}?$select=webresourceid,name,displayname,description,webresourcetype,content,ismanaged"
            f"&$filter=name eq '{nombre}'")
    cuerpo = leer_entorno(dv, ruta, C_RECURSO)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_RECURSO, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_RECURSO} devolvió {len(filas)} filas para '{nombre}'; el nombre es único")
    return filas[0] if filas else None


def _en_la_solucion(dv, solution_id, objeto_id):
    """Sin filtrar por `componenttype`: se lee el que la plataforma ponga y se
    informa, como con el paquete y las Custom API."""
    ruta = ("solutioncomponents?$select=componenttype,objectid"
            f"&$filter=_solutionid_value eq {solution_id} and objectid eq {objeto_id}")
    cuerpo = leer_entorno(dv, ruta, C_COMPONENTES)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_COMPONENTES, "value")
    return filas[0] if filas else None


def _publicar(dv, id_recurso, dormir):
    cuerpo = {"ParameterXml":
              f"<importexportxml><webresources><webresource>{id_recurso}</webresource></webresources></importexportxml>"}
    return escribir_metadatos(dv, "POST", "PublishXml", cuerpo, dormir=dormir)


def _diferencias(datos, recurso, contenido):
    difs, corregibles = [], {}
    if recurso.get("webresourcetype") != TIPOS_DE_RECURSO[datos["recurso"]]:
        difs.append(f"webresourcetype es {recurso.get('webresourcetype')!r} y el playbook dice {datos['recurso']} "
                    "(INMUTABLE: hay que borrar el web resource y rehacerlo)")
    for campo, valor in (("displayname", datos["displayname"]), ("description", datos["descripcion"])):
        if recurso.get(campo) != valor:
            difs.append(f"{campo} es {recurso.get(campo)!r} y el playbook dice {valor!r}")
            corregibles[campo] = valor
    if (recurso.get("content") or "") != contenido:
        difs.append("el contenido no es el del archivo del repositorio")
        corregibles["content"] = contenido
    if recurso.get("ismanaged"):
        difs.append("el web resource está managed en este entorno; no se toca desde acá")
        corregibles.clear()
    return difs, corregibles


def _contra_entorno(dv, datos, identidad, solo_verificar, completar, componente, dormir):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    crudo, contenido = leer_archivo(datos["archivo"])
    recurso = _leer_recurso(dv, datos["nombre"])
    hubo_escritura = False

    if recurso is None:
        if solo_verificar:
            return "difiere", componente, f"el web resource '{datos['nombre']}' no existe en el entorno"
        cuerpo = {
            "name": datos["nombre"],
            "displayname": datos["displayname"],
            "description": datos["descripcion"],
            "webresourcetype": TIPOS_DE_RECURSO[datos["recurso"]],
            "content": contenido,
        }
        est, resp, _ = escribir_metadatos(dv, "POST", CONJUNTO, cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", componente, f"el alta devolvió HTTP {est} (se esperaba 204): {resp}"
        recurso = _leer_recurso(dv, datos["nombre"])
        if recurso is None:
            return "error", componente, "el alta no dio error pero el web resource no aparece al releer"
        hubo_escritura = True
    elif completar and not solo_verificar:
        difs, corregibles = _diferencias(datos, recurso, contenido)
        if not [d for d in difs if "INMUTABLE" in d] and corregibles:
            id_recurso = exigir_forma(recurso.get("webresourceid"), str, C_RECURSO, "webresourceid", no_vacio=True)
            est, resp, _ = escribir_metadatos(
                dv, "PATCH", f"{CONJUNTO}({id_recurso})", corregibles, dormir=dormir, solucion=solucion)
            if est not in (200, 204):
                return "error", componente, f"la corrección devolvió HTTP {est} (se esperaba 204): {resp}"
            # Learn: un web resource NO hace falta publicarlo al crearlo, pero SÍ al actualizarlo.
            est, resp, _ = _publicar(dv, id_recurso, dormir)
            if est not in (200, 204):
                return "error", componente, f"se corrigió pero la publicación devolvió HTTP {est}: {resp}"
            recurso = _leer_recurso(dv, datos["nombre"])
            hubo_escritura = True

    id_recurso = exigir_forma(recurso.get("webresourceid"), str, C_RECURSO, "webresourceid", no_vacio=True)
    difs, _ = _diferencias(datos, recurso, contenido)
    fila = _en_la_solucion(dv, solution_id, id_recurso)
    if fila is None:
        difs.append(f"el web resource no figura como componente de la solución (solutionid {solution_id})")

    if difs:
        estado = "error" if hubo_escritura else "difiere"
        prefijo = "se escribió pero no quedó bien: " if hubo_escritura else ""
        return estado, componente, prefijo + "; ".join(difs)

    return ("creado" if hubo_escritura else "ya_existia"), componente, (
        f"webresourceid {id_recurso}, {datos['recurso']} de {len(crudo)} bytes desde '{datos['archivo']}', "
        f"en la solución '{solucion}' con componenttype {fila.get('componenttype')}")


def construir(ruta_playbook, solo_verificar, fabrica_cliente, completar=False, dormir=None):
    """Nunca lanza: siempre devuelve `(estado, componente, detalle)`."""
    if dormir is None:
        import time

        dormir = time.sleep
    componente = os.path.basename(ruta_playbook)
    paso = "leer el playbook"
    try:
        secciones = dividir_secciones(leer_texto(ruta_playbook))
        paso = "leer el bloque '## 2. Qué se crea'"
        datos = obtener_componente(secciones, TIPO)
        if isinstance(datos.get("nombre"), str):
            componente = datos["nombre"]
        paso = "leer el bloque '## 1. Identidad'"
        identidad = obtener_identidad(secciones)
        paso = "validar el bloque del web resource"
        validar_playbook(datos, identidad)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={TIPO} nombre={componente}")
    try:
        dv = fabrica_cliente()
    except Exception:
        return "error", componente, MENSAJE_FALLO_CLIENTE

    rastro = Rastro(dv)
    try:
        return _contra_entorno(rastro, datos, identidad, solo_verificar, completar, componente, dormir)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except ErrorEntorno as e:
        return "error", componente, str(e)
    except Exception as e:
        return "error", componente, f"fallo inesperado hablando con Dataverse, durante {rastro.en_curso}: {type(e).__name__}: {e}"


def main():
    argv = sys.argv[1:]
    rutas = [a for a in argv if not a.startswith("--")]
    banderas = {a for a in argv if a.startswith("--")}
    desconocidas = sorted(banderas - {"--solo-verificar", "--completar"})
    if len(rutas) != 1 or desconocidas:
        return salida(
            "error", "desconocido",
            "uso incorrecto: web_resource.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas)
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
