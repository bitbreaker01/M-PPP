#!/usr/bin/env python3
"""Registra UN paquete de plugins (.nupkg) en Dataverse, desde un playbook de
tipo `paquete-plugins`. Contrato: `power-platform-construir`,
`references/dataverse/alm.md`; Learn, "Build and package plug-in code".

    python3 herramientas/construir/paquete_plugins.py <playbook.md> [--solo-verificar] [--actualizar-contenido]

Existe porque `pac` y la Plug-in Registration Tool no sirven en una sesión sin
escritorio, y porque un `pluginassembly` suelto NO admite ensamblados
dependientes: el plugin necesita DocumentFormat.OpenXml, así que va en paquete.

Lo que hace la plataforma sola, y esta herramienta comprueba: al subir el
.nupkg, Dataverse registra en `pluginassembly` los ensamblados que contienen
clases `IPlugin`, y en `plugintype` cada una de esas clases. Si un tipo
esperado no aparece, el paquete se subió pero NO sirve: los steps y las
Custom API no van a tener a qué apuntar. Por eso `tipos` es obligatorio en el
playbook y se verifica uno por uno.

Nunca borra. `name` y `version` son INMUTABLES en el servidor (Learn): si el
paquete existe con otros valores, informa `difiere` y para — se resuelve
borrando a mano, que se lleva puestos ensamblados, tipos y TODOS sus steps.
Lo único que se puede actualizar es el contenido, y solo si se lo piden con
`--actualizar-contenido`.

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

TIPO = "paquete-plugins"

# Largos de columna del Web API (Learn, tabla PluginPackage, verificado 2026-09-22).
LARGO_NOMBRE = 100
LARGO_UNIQUENAME = 128
LARGO_VERSION = 100

# Tope propio, no de la plataforma: un .nupkg más grande que esto es señal de
# que se coló el SDK de Dataverse o algo que ya vive en el sandbox. El límite
# real de un ensamblado es 16 MB (Learn), pero acá queremos enterarnos ANTES.
MAXIMO_BYTES_NUPKG = 12 * 1024 * 1024

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "uniquename": str, "version": str, "nupkg": str, "tipos": list}

C_PAQUETE = "la consulta del paquete de plugins (GET pluginpackages)"
C_ENSAMBLADOS = "la consulta de los ensamblados del paquete (GET pluginassemblies)"
C_TIPOS = "la consulta de los tipos de plugin (GET plugintypes)"
C_COMPONENTES = "la consulta de pertenencia a la solución (GET solutioncomponents)"


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _caracteres_de_identificador(texto):
    """Lo que Dataverse admite en un unique name: letras y dígitos ASCII, guión
    bajo y punto. Se comprueba por rango de caracteres, no con una expresión
    regular, para que no dependa de la cultura ni de la localización."""
    return all(("a" <= c <= "z") or ("A" <= c <= "Z") or ("0" <= c <= "9") or c in "_." for c in texto)


def _version_bien_formada(texto):
    """Dos a cuatro números separados por punto, sin ceros a la izquierda de más
    de un dígito. NuGet acepta más formas; acá se exige la que produce el
    proyecto de empaquetado, porque `version` no se puede corregir después."""
    partes = texto.split(".")
    if not 2 <= len(partes) <= 4:
        return False
    for p in partes:
        if not p or not all("0" <= c <= "9" for c in p):
            return False
        if len(p) > 1 and p[0] == "0":
            return False
    return True


def _validar_estructura(datos, identidad):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"el bloque del paquete no tiene las claves esperadas: {'; '.join(partes)}")
    for clave, tipo in CLAVES.items():
        exigir_forma(datos[clave], tipo, "el bloque del paquete", clave, no_vacio=True)

    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque del paquete dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    exigir_sin_tildes(datos["nombre"], "nombre")
    if len(datos["nombre"]) > LARGO_NOMBRE:
        raise ErrorPlaybook(f"nombre tiene {len(datos['nombre'])} caracteres; el máximo de la columna es {LARGO_NOMBRE}")

    unico = datos["uniquename"]
    if len(unico) > LARGO_UNIQUENAME:
        raise ErrorPlaybook(f"uniquename tiene {len(unico)} caracteres; el máximo de la columna es {LARGO_UNIQUENAME}")
    if not _caracteres_de_identificador(unico):
        raise ErrorPlaybook(f"uniquename = {unico!r} solo puede llevar letras y dígitos ASCII, guión bajo y punto")
    # Convención NUESTRA, no de la plataforma: Learn no exige prefijo en el
    # unique name de un paquete (sí en el de una Custom API). Se exige igual
    # porque en Dev hay otro publisher con el mismo prefijo `sanic`
    # (`01-convenciones.md`) y un nombre sin prefijo invita a la colisión.
    prefijo = identidad["prefijo"] + "_"
    if not unico.startswith(prefijo):
        raise ErrorPlaybook(f"uniquename = {unico!r} no empieza con el prefijo del publisher {prefijo!r}")

    if not _version_bien_formada(datos["version"]):
        raise ErrorPlaybook(
            f"version = {datos['version']!r} no tiene la forma esperada (de dos a cuatro números separados por punto); "
            "y `version` NO se puede cambiar en el servidor una vez creado el paquete"
        )
    if len(datos["version"]) > LARGO_VERSION:
        raise ErrorPlaybook(f"version tiene {len(datos['version'])} caracteres; el máximo de la columna es {LARGO_VERSION}")

    ruta = datos["nupkg"]
    if not ruta.endswith(".nupkg"):
        raise ErrorPlaybook(f"nupkg = {ruta!r} no termina en '.nupkg'")
    if os.path.isabs(ruta) or ".." in ruta.split("/"):
        raise ErrorPlaybook(f"nupkg = {ruta!r} tiene que ser una ruta relativa a la raíz del repositorio, sin '..'")

    tipos = datos["tipos"]
    for i, t in enumerate(tipos):
        exigir_forma(t, str, "el bloque del paquete", f"tipos[{i}]", no_vacio=True)
        if "." not in t:
            raise ErrorPlaybook(f"tipos[{i}] = {t!r} no parece un nombre de tipo .NET completo (namespace + clase)")
    if len(set(tipos)) != len(tipos):
        repetidos = sorted({t for t in tipos if tipos.count(t) > 1})
        raise ErrorPlaybook(f"tipos tiene entradas repetidas: {repetidos}")


def validar_playbook(datos, identidad):
    _validar_estructura(datos, identidad)


def leer_nupkg(ruta_relativa):
    """Lee el .nupkg de la raíz del repositorio y lo devuelve en base64, que es
    como viaja en la columna `content`. Lanza `Bloqueado` si no está armado:
    no es un error del playbook, es que falta correr `dotnet pack`."""
    ruta = os.path.join(_RAIZ, ruta_relativa)
    if not os.path.isfile(ruta):
        raise Bloqueado(
            f"no existe el paquete '{ruta_relativa}'; hay que armarlo antes con "
            "`dotnet pack src/Sanic.Mppp.Plugins.Paquete/Sanic.Mppp.Plugins.Paquete.csproj -c Release`"
        )
    with open(ruta, "rb") as f:
        crudo = f.read()
    if not crudo:
        raise Bloqueado(f"el paquete '{ruta_relativa}' está vacío")
    if len(crudo) > MAXIMO_BYTES_NUPKG:
        raise Bloqueado(
            f"el paquete '{ruta_relativa}' pesa {len(crudo)} bytes, más que el tope de {MAXIMO_BYTES_NUPKG}; "
            "casi siempre significa que se coló un ensamblado que ya vive en el sandbox (el SDK de Dataverse)"
        )
    return crudo, base64.b64encode(crudo).decode("ascii")


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
def _leer_paquete(dv, uniquename):
    """El paquete por su unique name, o `None`. Nunca devuelve más de uno: el
    unique name es único, y si el entorno devolviera dos es forma inesperada."""
    ruta = (
        "pluginpackages?$select=pluginpackageid,name,uniquename,version,ismanaged"
        f"&$filter=uniquename eq '{uniquename}'"
    )
    cuerpo = leer_entorno(dv, ruta, C_PAQUETE)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_PAQUETE, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_PAQUETE} devolvió {len(filas)} filas para el unique name '{uniquename}'; se esperaba a lo sumo una")
    return filas[0] if filas else None


def _tipos_registrados(dv, paquete_id):
    """Los `plugintype` que la plataforma registró sola a partir del paquete.
    Devuelve (nombres de ensamblado, {typename: plugintypeid})."""
    ruta_asm = f"pluginassemblies?$select=pluginassemblyid,name,version&$filter=_packageid_value eq {paquete_id}"
    cuerpo = leer_entorno(dv, ruta_asm, C_ENSAMBLADOS)
    ensamblados = exigir_forma(cuerpo.get("value"), [dict], C_ENSAMBLADOS, "value")

    nombres, tipos = [], {}
    for asm in ensamblados:
        asm_id = exigir_forma(asm.get("pluginassemblyid"), str, C_ENSAMBLADOS, "pluginassemblyid", no_vacio=True)
        nombres.append(exigir_forma(asm.get("name"), str, C_ENSAMBLADOS, "name"))
        ruta_tipos = f"plugintypes?$select=plugintypeid,typename&$filter=_pluginassemblyid_value eq {asm_id}"
        cuerpo_tipos = leer_entorno(dv, ruta_tipos, C_TIPOS)
        for t in exigir_forma(cuerpo_tipos.get("value"), [dict], C_TIPOS, "value"):
            nombre_tipo = exigir_forma(t.get("typename"), str, C_TIPOS, "typename", no_vacio=True)
            tipos[nombre_tipo] = exigir_forma(t.get("plugintypeid"), str, C_TIPOS, "plugintypeid", no_vacio=True)
    return sorted(nombres), tipos


def _componente_de_la_solucion(dv, solution_id, paquete_id):
    """Fila de `solutioncomponents` del paquete en esa solución, si está.

    A propósito NO se filtra por `componenttype`: Learn avisa que los tipos de
    componente nuevos (paquete de plugins, Custom API) no están en el optionset
    público `componenttype`, y el número que circula en foros no está
    verificado. Se lee el que la plataforma haya puesto y se informa: así el
    ensayo con componentes descartables deja la evidencia en vez de la
    suposición."""
    ruta = (
        "solutioncomponents?$select=componenttype,objectid"
        f"&$filter=_solutionid_value eq {solution_id} and objectid eq {paquete_id}"
    )
    cuerpo = leer_entorno(dv, ruta, C_COMPONENTES)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_COMPONENTES, "value")
    return filas[0] if filas else None


def _verificar(dv, datos, solution_id, paquete):
    """Todo lo que tiene que ser cierto después de subir el paquete. Devuelve
    la lista de diferencias (vacía = está bien) y el detalle para el informe."""
    difs = []
    paquete_id = exigir_forma(paquete.get("pluginpackageid"), str, C_PAQUETE, "pluginpackageid", no_vacio=True)

    nombre = exigir_forma(paquete.get("name"), str, C_PAQUETE, "name")
    version = exigir_forma(paquete.get("version"), str, C_PAQUETE, "version")
    if nombre != datos["nombre"]:
        difs.append(f"name es {nombre!r} y el playbook dice {datos['nombre']!r} (INMUTABLE: hay que borrar el paquete y rehacerlo)")
    if version != datos["version"]:
        difs.append(f"version es {version!r} y el playbook dice {datos['version']!r} (INMUTABLE: hay que borrar el paquete y rehacerlo)")
    if exigir_forma(paquete.get("ismanaged"), bool, C_PAQUETE, "ismanaged"):
        difs.append("el paquete está managed en este entorno; no se toca desde acá")

    ensamblados, tipos = _tipos_registrados(dv, paquete_id)
    faltan = [t for t in datos["tipos"] if t not in tipos]
    if faltan:
        difs.append(
            f"la plataforma no registró estos tipos de plugin: {faltan}. "
            f"Ensamblados del paquete: {ensamblados or 'ninguno'}. Tipos registrados: {sorted(tipos) or 'ninguno'}"
        )

    componente = _componente_de_la_solucion(dv, solution_id, paquete_id)
    if componente is None:
        difs.append(f"el paquete no figura como componente de la solución (solutionid {solution_id})")
        tipo_componente = None
    else:
        tipo_componente = componente.get("componenttype")

    return difs, {"paquete_id": paquete_id, "tipos": tipos, "ensamblados": ensamblados, "componenttype": tipo_componente}


def _contra_entorno(dv, datos, identidad, solo_verificar, actualizar_contenido, componente, dormir):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    paquete = _leer_paquete(dv, datos["uniquename"])

    if paquete is None:
        if solo_verificar:
            return "difiere", componente, f"el paquete '{datos['uniquename']}' no existe en el entorno"
        crudo, contenido = leer_nupkg(datos["nupkg"])
        cuerpo = {
            "name": datos["nombre"],
            "uniquename": datos["uniquename"],
            "version": datos["version"],
            "content": contenido,
        }
        print(f"Subo el paquete: {len(crudo)} bytes ({len(contenido)} en base64) a la solución '{solucion}'.", flush=True)
        est, resp, _ = escribir_metadatos(dv, "POST", "pluginpackages", cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", componente, f"el alta del paquete devolvió HTTP {est} (se esperaba 204): {resp}"
        paquete = _leer_paquete(dv, datos["uniquename"])
        if paquete is None:
            return "error", componente, "el alta del paquete no devolvió error pero el paquete no aparece al releer"
        accion = "creado"
    else:
        accion = "ya_existia"
        if actualizar_contenido and not solo_verificar:
            crudo, contenido = leer_nupkg(datos["nupkg"])
            paquete_id = exigir_forma(paquete.get("pluginpackageid"), str, C_PAQUETE, "pluginpackageid", no_vacio=True)
            print(f"Actualizo el contenido del paquete: {len(crudo)} bytes ({len(contenido)} en base64).", flush=True)
            est, resp, _ = escribir_metadatos(
                dv, "PATCH", f"pluginpackages({paquete_id})", {"content": contenido}, dormir=dormir, solucion=solucion
            )
            if est not in (200, 204):
                return "error", componente, f"la actualización del contenido devolvió HTTP {est} (se esperaba 204): {resp}"
            paquete = _leer_paquete(dv, datos["uniquename"])
            accion = "creado"  # hubo escritura: el ciclo tiene que volver a verificar en Dev

    difs, detalle = _verificar(dv, datos, solution_id, paquete)
    if difs:
        estado = "difiere" if accion == "ya_existia" else "error"
        prefijo = "" if accion == "ya_existia" else "se escribió pero no quedó bien: "
        return estado, componente, prefijo + "; ".join(difs)

    return accion, componente, (
        f"pluginpackageid {detalle['paquete_id']}, version {datos['version']}, "
        f"ensamblados {detalle['ensamblados']}, {len(detalle['tipos'])} tipos de plugin registrados, "
        f"en la solución '{solucion}' con componenttype {detalle['componenttype']}"
    )


def construir(ruta_playbook, solo_verificar, fabrica_cliente, actualizar_contenido=False, dormir=None):
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
        if isinstance(datos.get("uniquename"), str):
            componente = datos["uniquename"]
        paso = "leer el bloque '## 1. Identidad'"
        identidad = obtener_identidad(secciones)
        paso = "validar el bloque del paquete"
        validar_playbook(datos, identidad)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={TIPO} uniquename={componente}")
    try:
        dv = fabrica_cliente()
    except Exception:
        return "error", componente, MENSAJE_FALLO_CLIENTE

    rastro = Rastro(dv)
    try:
        return _contra_entorno(rastro, datos, identidad, solo_verificar, actualizar_contenido, componente, dormir)
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
    desconocidas = sorted(banderas - {"--solo-verificar", "--actualizar-contenido"})
    if len(rutas) != 1 or desconocidas:
        return salida(
            "error", "desconocido",
            "uso incorrecto: paquete_plugins.py <playbook.md> [--solo-verificar] [--actualizar-contenido]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, actualizar_contenido="--actualizar-contenido" in banderas
    )
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
