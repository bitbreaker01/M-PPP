#!/usr/bin/env python3
"""Registra los `sdkmessageprocessingstep` de un paquete de plugins, con sus
imágenes, desde un playbook de tipo `steps`. Contrato:
`power-platform-construir`, `references/dataverse/patrones.md`; Learn,
"Register a plug-in".

    python3 herramientas/construir/step.py <playbook.md> [--solo-verificar] [--completar]

A diferencia de las otras herramientas, un playbook trae TODOS los steps de un
paquete, no uno solo. Es a propósito: los steps de un mismo mensaje y tabla
compiten por el `rank`, así que solo se entienden mirándolos juntos
(`diseno/03-contratos-custom-api.md` §5.1 es esa misma tabla).

Lo que más se valida, porque es lo que revienta en producción y no en el
registro: las **imágenes**. Un step que lee la pre-image y se registró sin
ella no falla al registrarse — falla con una referencia nula la primera vez
que alguien guarda un registro. Learn fija las combinaciones posibles y acá se
comprueban una por una antes de tocar el entorno.

Nunca borra un step ni una imagen. Un step de más se denuncia; sacarlo lo
decide una persona.

Última línea de la salida: JSON de una línea con `estado`
(creado | ya_existia | difiere | bloqueado | error), `componente`, `detalle`.
"""
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
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

TIPO = "steps"

# Learn, tabla SdkMessageProcessingStep (verificado 2026-09-22). Del enum de
# `stage` solo estos tres son estables para uso externo; el resto es interno
# o está deprecado aunque el picklist técnicamente los acepte.
ETAPAS = {"PreValidation": 10, "PreOperation": 20, "PostOperation": 40}
MODOS = {"Sincrono": 0, "Asincrono": 1}
DESPLIEGUE_SOLO_SERVIDOR = 0
INVOCACION_PADRE = 0

# Learn, tabla SdkMessageProcessingStepImage.
IMAGEN_PRE, IMAGEN_POST = 0, 1

# Los ÚNICOS mensajes que admiten imágenes, con el `messagepropertyname` que
# les corresponde (Learn, "Messages that support entity images"). Los mensajes
# con más de una propiedad posible no se soportan acá: ninguno hace falta.
PROPIEDAD_DE_IMAGEN = {
    "Assign": "Target", "Create": "Target", "Delete": "Target",
    "DeliverIncoming": "EmailId", "DeliverPromote": "EmailId",
    "Route": "Target", "SetState": "EntityMoniker", "Update": "Target",
}

# Mensajes en los que el `filteringattributes` tiene sentido. En un Create no
# hay atributos "que cambiaron", así que un filtro ahí es un error de concepto.
MENSAJES_CON_FILTRO = {"Update"}

LARGO_NOMBRE = 256
LARGO_ALIAS = 256

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "paquete": str, "steps": list}
CLAVES_STEP = {
    "nombre": str, "descripcion": str, "plugintype": str, "mensaje": str, "tabla": str,
    "etapa": str, "modo": str, "orden": int, "filtro": list, "preimagen": (dict, type(None)),
}
CLAVES_IMAGEN = {"alias": str, "columnas": list}

C_TIPO_PLUGIN = "la consulta del tipo de plugin (GET plugintypes)"
C_MENSAJE = "la consulta del mensaje (GET sdkmessages)"
C_FILTRO = "la consulta del filtro de mensaje (GET sdkmessagefilters)"
C_STEPS = "la consulta de los steps (GET sdkmessageprocessingsteps)"
C_IMAGENES = "la consulta de las imágenes (GET sdkmessageprocessingstepimages)"
C_COMPONENTES = "la consulta de pertenencia a la solución (GET solutioncomponents)"


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _validar_bloque(datos, claves, de_donde):
    faltan, sobran = sorted(set(claves) - set(datos)), sorted(set(datos) - set(claves))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"{de_donde} no tiene las claves esperadas: {'; '.join(partes)}")


def _validar_imagen(imagen, s, donde):
    _validar_bloque(imagen, CLAVES_IMAGEN, f"{donde}.preimagen")
    exigir_forma(imagen["alias"], str, donde, "preimagen.alias", no_vacio=True)
    if len(imagen["alias"]) > LARGO_ALIAS:
        raise ErrorPlaybook(f"{donde}: el alias de la pre-imagen tiene más de {LARGO_ALIAS} caracteres")
    columnas = exigir_forma(imagen["columnas"], [str], donde, "preimagen.columnas", no_vacio=True)
    # Learn: dejar `attributes` vacío trae TODAS las columnas, y eso pega en el
    # rendimiento de cada guardado. Acá directamente no se admite.
    if len(set(columnas)) != len(columnas):
        raise ErrorPlaybook(f"{donde}: la pre-imagen tiene columnas repetidas")

    mensaje = s["mensaje"]
    if mensaje not in PROPIEDAD_DE_IMAGEN:
        raise ErrorPlaybook(
            f"{donde}: el mensaje '{mensaje}' no admite imágenes. Los que sí son {sorted(PROPIEDAD_DE_IMAGEN)}"
        )
    if mensaje == "Create":
        # No hay "antes" de un Create: el registro todavía no existe.
        raise ErrorPlaybook(f"{donde}: un step sobre 'Create' no puede tener pre-imagen")


def _validar_step(s, indice, nombres, naturales):
    donde = f"el step [{indice}] ({s.get('nombre', 'sin nombre')!r})"
    _validar_bloque(s, CLAVES_STEP, donde)
    for clave, tipo in CLAVES_STEP.items():
        if clave == "preimagen":
            continue
        exigir_forma(s[clave], tipo, donde, clave, no_vacio=(tipo is str))

    exigir_sin_tildes(s["nombre"], f"{donde}.nombre")
    if len(s["nombre"]) > LARGO_NOMBRE:
        raise ErrorPlaybook(f"{donde}: nombre tiene más de {LARGO_NOMBRE} caracteres")
    if s["nombre"] in nombres:
        raise ErrorPlaybook(f"{donde}: el nombre está repetido")
    nombres.add(s["nombre"])

    if s["etapa"] not in ETAPAS:
        raise ErrorPlaybook(f"{donde}: etapa = {s['etapa']!r} no es válida; las válidas son {sorted(ETAPAS)}")
    if s["modo"] not in MODOS:
        raise ErrorPlaybook(f"{donde}: modo = {s['modo']!r} no es válido; los válidos son {sorted(MODOS)}")
    if s["modo"] == "Asincrono" and s["etapa"] != "PostOperation":
        # Learn: un step asíncrono solo se puede registrar en PostOperation.
        raise ErrorPlaybook(f"{donde}: un step asíncrono solo se puede registrar en PostOperation, no en {s['etapa']}")
    if "." not in s["plugintype"]:
        raise ErrorPlaybook(f"{donde}: plugintype = {s['plugintype']!r} no parece un nombre de tipo .NET completo")

    filtro = exigir_forma(s["filtro"], [str], donde, "filtro")
    if filtro and s["mensaje"] not in MENSAJES_CON_FILTRO:
        raise ErrorPlaybook(
            f"{donde}: hay filtro de atributos sobre '{s['mensaje']}', y solo tiene sentido en {sorted(MENSAJES_CON_FILTRO)}"
        )
    if len(set(filtro)) != len(filtro):
        raise ErrorPlaybook(f"{donde}: el filtro de atributos tiene columnas repetidas")
    for columna in filtro:
        # Learn: la primary key viene SIEMPRE en el Target, así que meterla en
        # el filtro lo anula para todo lo demás. Es el error clásico.
        if columna.endswith("id") and columna == s["tabla"] + "id":
            raise ErrorPlaybook(
                f"{donde}: el filtro no puede incluir la clave primaria '{columna}': viene siempre en el Target "
                "y deja el filtro sin efecto para el resto de las columnas"
            )

    natural = (s["plugintype"], s["mensaje"], s["tabla"])
    if natural in naturales:
        raise ErrorPlaybook(f"{donde}: ya hay otro step del mismo plugin sobre {s['mensaje']} de {s['tabla']}")
    naturales.add(natural)

    if s["preimagen"] is not None:
        exigir_forma(s["preimagen"], dict, donde, "preimagen")
        _validar_imagen(s["preimagen"], s, donde)


def _validar_estructura(datos):
    _validar_bloque(datos, CLAVES, "el bloque de los steps")
    for clave, tipo in CLAVES.items():
        exigir_forma(datos[clave], tipo, "el bloque de los steps", clave, no_vacio=True)
    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque de los steps dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    nombres, naturales = set(), set()
    for i, s in enumerate(datos["steps"]):
        exigir_forma(s, dict, "el bloque de los steps", f"steps[{i}]")
        _validar_step(s, i, nombres, naturales)


def validar_playbook(datos):
    _validar_estructura(datos)


def texto_de_filtro(filtro):
    """`filteringattributes` va como una lista separada por comas. Se ordena
    para que dos playbooks con las mismas columnas en distinto orden produzcan
    el mismo valor, y la comparación contra el entorno no dé falsos positivos."""
    return ",".join(sorted(filtro)) if filtro else None


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
class Catalogo:
    """Resuelve y cachea los identificadores del entorno. Cada mensaje y cada
    tabla se consultan UNA vez, por más steps que los usen."""

    def __init__(self, dv):
        self._dv = dv
        self._tipos, self._mensajes, self._filtros = {}, {}, {}

    def tipo_de_plugin(self, typename):
        if typename not in self._tipos:
            ruta = f"plugintypes?$select=plugintypeid,typename&$filter=typename eq '{typename}'"
            cuerpo = leer_entorno(self._dv, ruta, C_TIPO_PLUGIN)
            filas = exigir_forma(cuerpo.get("value"), [dict], C_TIPO_PLUGIN, "value")
            if not filas:
                raise Bloqueado(
                    f"el tipo de plugin '{typename}' no está registrado; "
                    "primero hay que registrar el paquete con `herramientas/construir/paquete_plugins.py`"
                )
            if len(filas) > 1:
                raise ErrorEntorno(f"{C_TIPO_PLUGIN} devolvió {len(filas)} filas para '{typename}'")
            self._tipos[typename] = exigir_forma(filas[0].get("plugintypeid"), str, C_TIPO_PLUGIN, "plugintypeid", no_vacio=True)
        return self._tipos[typename]

    def mensaje(self, nombre):
        if nombre not in self._mensajes:
            ruta = f"sdkmessages?$select=sdkmessageid,name&$filter=name eq '{nombre}'"
            cuerpo = leer_entorno(self._dv, ruta, C_MENSAJE)
            filas = exigir_forma(cuerpo.get("value"), [dict], C_MENSAJE, "value")
            if len(filas) != 1:
                raise Bloqueado(f"el mensaje '{nombre}' no existe en el entorno, o hay más de uno ({len(filas)})")
            self._mensajes[nombre] = exigir_forma(filas[0].get("sdkmessageid"), str, C_MENSAJE, "sdkmessageid", no_vacio=True)
        return self._mensajes[nombre]

    def filtro_de_mensaje(self, mensaje, tabla):
        """El `sdkmessagefilter` del par (mensaje, tabla). Se consulta por tabla
        y se elige el mensaje del lado del cliente: es la forma que Learn
        documenta literal para esta tabla."""
        if tabla not in self._filtros:
            ruta = (
                "sdkmessagefilters?$select=sdkmessagefilterid,primaryobjecttypecode"
                "&$expand=sdkmessageid($select=name)"
                f"&$filter=primaryobjecttypecode eq '{tabla}'"
            )
            cuerpo = leer_entorno(self._dv, ruta, C_FILTRO)
            por_mensaje = {}
            for fila in exigir_forma(cuerpo.get("value"), [dict], C_FILTRO, "value"):
                sdk = exigir_forma(fila.get("sdkmessageid"), dict, C_FILTRO, "sdkmessageid")
                nombre = exigir_forma(sdk.get("name"), str, C_FILTRO, "sdkmessageid.name", no_vacio=True)
                por_mensaje[nombre] = exigir_forma(
                    fila.get("sdkmessagefilterid"), str, C_FILTRO, "sdkmessagefilterid", no_vacio=True
                )
            self._filtros[tabla] = por_mensaje
        por_mensaje = self._filtros[tabla]
        if mensaje not in por_mensaje:
            raise Bloqueado(
                f"la tabla '{tabla}' no admite el mensaje '{mensaje}' (no hay sdkmessagefilter para ese par); "
                f"los que admite son {sorted(por_mensaje)}"
            )
        return por_mensaje[mensaje]


def _leer_step(dv, plugintype_id, mensaje_id, filtro_id):
    """El step por su clave natural: plugin + mensaje + tabla. No por `name`,
    que es mutable y podría haberlo cambiado alguien desde el portal."""
    ruta = (
        "sdkmessageprocessingsteps?$select=sdkmessageprocessingstepid,name,description,stage,mode,rank,"
        "filteringattributes,statecode,supporteddeployment"
        f"&$filter=_plugintypeid_value eq {plugintype_id} and _sdkmessageid_value eq {mensaje_id} "
        f"and _sdkmessagefilterid_value eq {filtro_id}"
    )
    cuerpo = leer_entorno(dv, ruta, C_STEPS)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_STEPS, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_STEPS} devolvió {len(filas)} steps para la misma clave natural; se esperaba a lo sumo uno")
    return filas[0] if filas else None


def _leer_imagenes(dv, step_id):
    ruta = (
        "sdkmessageprocessingstepimages?$select=sdkmessageprocessingstepimageid,imagetype,entityalias,"
        "attributes,messagepropertyname,name"
        f"&$filter=_sdkmessageprocessingstepid_value eq {step_id}"
    )
    cuerpo = leer_entorno(dv, ruta, C_IMAGENES)
    return exigir_forma(cuerpo.get("value"), [dict], C_IMAGENES, "value")


def _cuerpo_step(s, plugintype_id, mensaje_id, filtro_id):
    return {
        "name": s["nombre"],
        "description": s["descripcion"],
        "stage": ETAPAS[s["etapa"]],
        "mode": MODOS[s["modo"]],
        "rank": s["orden"],
        "supporteddeployment": DESPLIEGUE_SOLO_SERVIDOR,
        "invocationsource": INVOCACION_PADRE,
        "filteringattributes": texto_de_filtro(s["filtro"]),
        "sdkmessageid@odata.bind": f"/sdkmessages({mensaje_id})",
        "sdkmessagefilterid@odata.bind": f"/sdkmessagefilters({filtro_id})",
        "plugintypeid@odata.bind": f"/plugintypes({plugintype_id})",
        # `eventhandler` es POLIMÓRFICO (plugintype o serviceendpoint): no
        # existe un `eventhandler@odata.bind` genérico, hay que usar la
        # propiedad de navegación del destino. En un step de plugin apunta al
        # mismo tipo que `plugintypeid`.
        "eventhandler_plugintype@odata.bind": f"/plugintypes({plugintype_id})",
    }


def _cuerpo_imagen(s, step_id):
    imagen = s["preimagen"]
    return {
        "name": imagen["alias"],
        "entityalias": imagen["alias"],
        "imagetype": IMAGEN_PRE,
        "messagepropertyname": PROPIEDAD_DE_IMAGEN[s["mensaje"]],
        "attributes": ",".join(sorted(imagen["columnas"])),
        "sdkmessageprocessingstepid@odata.bind": f"/sdkmessageprocessingsteps({step_id})",
    }


def _diferencias_del_step(s, fila):
    difs = []
    esperado = {
        "name": s["nombre"],
        "description": s["descripcion"],
        "stage": ETAPAS[s["etapa"]],
        "mode": MODOS[s["modo"]],
        "rank": s["orden"],
        "filteringattributes": texto_de_filtro(s["filtro"]),
    }
    for campo, valor in esperado.items():
        actual = fila.get(campo)
        if campo == "filteringattributes" and isinstance(actual, str):
            actual = ",".join(sorted(actual.split(",")))
        if actual != valor:
            difs.append(f"{campo} es {actual!r} y el playbook dice {valor!r}")
    if fila.get("statecode") not in (0, None):
        difs.append(f"el step está deshabilitado (statecode {fila.get('statecode')})")
    return difs


def _diferencias_de_imagen(s, imagenes):
    """Lo que más importa: un step que lee la pre-image y no la tiene
    registrada revienta en producción, no acá."""
    difs = []
    pre = [i for i in imagenes if i.get("imagetype") == IMAGEN_PRE]
    if s["preimagen"] is None:
        if pre:
            difs.append(f"tiene {len(pre)} pre-imagen(es) que el playbook no declara (esta herramienta nunca borra)")
        return difs, False
    if not pre:
        return ["le falta la pre-imagen, y el plugin la lee: sin ella revienta al primer guardado"], True
    if len(pre) > 1:
        difs.append(f"tiene {len(pre)} pre-imágenes; el playbook declara una")
    imagen, declarada = pre[0], s["preimagen"]
    if imagen.get("entityalias") != declarada["alias"]:
        difs.append(f"el alias de la pre-imagen es {imagen.get('entityalias')!r} y el playbook dice {declarada['alias']!r}")
    actuales = imagen.get("attributes")
    esperadas = ",".join(sorted(declarada["columnas"]))
    if actuales is None or ",".join(sorted(str(actuales).split(","))) != esperadas:
        difs.append(f"las columnas de la pre-imagen son {actuales!r} y el playbook dice {esperadas!r}")
    if imagen.get("messagepropertyname") != PROPIEDAD_DE_IMAGEN[s["mensaje"]]:
        difs.append(
            f"messagepropertyname de la pre-imagen es {imagen.get('messagepropertyname')!r} y para "
            f"'{s['mensaje']}' tiene que ser {PROPIEDAD_DE_IMAGEN[s['mensaje']]!r}"
        )
    return difs, False


def _en_la_solucion(dv, solution_id, step_id):
    ruta = (
        "solutioncomponents?$select=componenttype,objectid"
        f"&$filter=_solutionid_value eq {solution_id} and objectid eq {step_id}"
    )
    cuerpo = leer_entorno(dv, ruta, C_COMPONENTES)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_COMPONENTES, "value")
    return filas[0] if filas else None


def _cuerpo_corregible(s):
    """Lo que SÍ se puede cambiar en un step ya registrado. La clave natural
    (plugin, mensaje, tabla) no está acá: cambiar eso es otro step, no una
    corrección. `filteringattributes` va explícito en `None` para poder
    BORRAR un filtro que sobra, no solo cambiarlo."""
    return {
        "name": s["nombre"],
        "description": s["descripcion"],
        "stage": ETAPAS[s["etapa"]],
        "mode": MODOS[s["modo"]],
        "rank": s["orden"],
        "filteringattributes": texto_de_filtro(s["filtro"]),
    }


def _procesar_step(dv, catalogo, s, solution_id, solucion, escribir, completar, dormir):
    """Devuelve (accion, difs). `accion` es 'creado', 'ya_existia' o 'difiere'."""
    plugintype_id = catalogo.tipo_de_plugin(s["plugintype"])
    mensaje_id = catalogo.mensaje(s["mensaje"])
    filtro_id = catalogo.filtro_de_mensaje(s["mensaje"], s["tabla"])

    fila = _leer_step(dv, plugintype_id, mensaje_id, filtro_id)
    hubo_escritura = False

    if fila is None:
        if not escribir:
            return "difiere", [f"{s['nombre']}: no existe en el entorno"]
        cuerpo = _cuerpo_step(s, plugintype_id, mensaje_id, filtro_id)
        est, resp, _ = escribir_metadatos(dv, "POST", "sdkmessageprocessingsteps", cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", [f"{s['nombre']}: el alta devolvió HTTP {est} (se esperaba 204): {resp}"]
        fila = _leer_step(dv, plugintype_id, mensaje_id, filtro_id)
        if fila is None:
            return "error", [f"{s['nombre']}: el alta no dio error pero el step no aparece al releer"]
        hubo_escritura = True

    step_id = exigir_forma(
        fila.get("sdkmessageprocessingstepid"), str, C_STEPS, "sdkmessageprocessingstepid", no_vacio=True
    )
    if escribir and completar and not hubo_escritura and _diferencias_del_step(s, fila):
        est, resp, _ = escribir_metadatos(
            dv, "PATCH", f"sdkmessageprocessingsteps({step_id})", _cuerpo_corregible(s), dormir=dormir, solucion=solucion
        )
        if est not in (200, 204):
            return "error", [f"{s['nombre']}: la corrección devolvió HTTP {est} (se esperaba 204): {resp}"]
        hubo_escritura = True
        fila = _leer_step(dv, plugintype_id, mensaje_id, filtro_id)
        if fila is None:
            return "error", [f"{s['nombre']}: el step desapareció al releer después de corregirlo"]

    imagenes = _leer_imagenes(dv, step_id)
    _, falta_imagen = _diferencias_de_imagen(s, imagenes)
    # Una pre-imagen que falta se agrega SIEMPRE que se esté escribiendo,
    # incluso sin `--completar`: no es un ajuste de gusto, es la diferencia
    # entre que el plugin ande y que reviente al primer guardado.
    if falta_imagen and escribir:
        est, resp, _ = escribir_metadatos(
            dv, "POST", "sdkmessageprocessingstepimages", _cuerpo_imagen(s, step_id), dormir=dormir, solucion=solucion
        )
        if est not in (200, 201, 204):
            return "error", [f"{s['nombre']}: el alta de la pre-imagen devolvió HTTP {est}: {resp}"]
        hubo_escritura = True
        imagenes = _leer_imagenes(dv, step_id)

    difs = [f"{s['nombre']}: {d}" for d in _diferencias_del_step(s, fila)]
    d_imagen, _ = _diferencias_de_imagen(s, imagenes)
    difs.extend(f"{s['nombre']}: {d}" for d in d_imagen)
    if _en_la_solucion(dv, solution_id, step_id) is None:
        difs.append(f"{s['nombre']}: no figura como componente de la solución")

    if difs:
        return ("error" if hubo_escritura else "difiere"), difs
    return ("creado" if hubo_escritura else "ya_existia"), []


def _contra_entorno(dv, datos, identidad, solo_verificar, completar, componente, dormir):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    catalogo = Catalogo(dv)
    escribir = not solo_verificar

    creados, existian, difs = [], [], []
    for s in datos["steps"]:
        accion, d = _procesar_step(dv, catalogo, s, solution_id, solucion, escribir, completar, dormir)
        if accion == "error":
            return "error", componente, "; ".join(d)
        if d:
            difs.extend(d)
        elif accion == "creado":
            creados.append(s["nombre"])
        else:
            existian.append(s["nombre"])

    if difs:
        estado = "error" if creados else "difiere"
        prefijo = "se escribió pero no quedó bien: " if creados else ""
        return estado, componente, prefijo + "; ".join(difs)

    resumen = f"{len(creados)} registrados y {len(existian)} que ya estaban, de {len(datos['steps'])}, en la solución '{solucion}'"
    return ("creado" if creados else "ya_existia"), componente, resumen


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
        if isinstance(datos.get("paquete"), str):
            componente = datos["paquete"]
        paso = "leer el bloque '## 1. Identidad'"
        identidad = obtener_identidad(secciones)
        paso = "validar el bloque de los steps"
        validar_playbook(datos)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={TIPO} paquete={componente} steps={len(datos['steps'])}")
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
            "uso incorrecto: step.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas
    )
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
