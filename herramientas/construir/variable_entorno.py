#!/usr/bin/env python3
"""Construye UNA environment variable de Dataverse (su definición y, si se
declara, su valor en ESTE entorno), desde un playbook de tipo
`variable-entorno`. Contrato: `power-platform-construir`,
`references/dataverse/alm.md`.

    python3 herramientas/construir/variable_entorno.py <playbook.md> [--solo-verificar] [--completar]

Dos filas, no una: la **definición** (`environmentvariabledefinition`) viaja en
la solución y es la misma en todos los entornos; el **valor**
(`environmentvariablevalue`) es de ESTE entorno y NO se agrega a la solución, a
propósito: si el valor viajara, al importar en otro entorno pisaría el de allá
(`07` DF-05: "la solución pasa después al Dev de BAC, donde estos valores se
cargan de nuevo").

Un playbook puede declarar `valor: null`: entonces se crea la definición y no
se toca el valor. Es lo correcto cuando el dato todavía no existe (una carpeta
de buzón que aún no creó el administrador de Exchange): una variable vacía se
ve y se pregunta; una variable con un valor inventado falla en tiempo de
ejecución y nadie sabe por qué.

`schemaname` y `type` NO se pueden cambiar una vez creada la definición: si
difieren, se informa y se para.

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

TIPO = "variable-entorno"

# Verificado contra las definiciones que ya viven en el entorno (2026-09-22).
TIPOS_DE_VALOR = {"Texto": 100000000, "Numero": 100000001, "Booleano": 100000002, "JSON": 100000003}

LARGO_SCHEMANAME = 100
LARGO_DISPLAYNAME = 100

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "nombre": str, "displayname": str, "descripcion": str,
          "tipovalor": str, "obligatoria": bool}
# `valor` va aparte porque es la única clave que admite nulo a propósito.
CLAVE_VALOR = "valor"

C_DEFINICION = "la consulta de la definición (GET environmentvariabledefinitions)"
C_VALOR = "la consulta del valor (GET environmentvariablevalues)"
C_COMPONENTES = "la consulta de pertenencia a la solución (GET solutioncomponents)"


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _caracteres_de_identificador(texto):
    return all(("a" <= c <= "z") or ("A" <= c <= "Z") or ("0" <= c <= "9") or c == "_" for c in texto)


def _validar_estructura(datos, identidad):
    esperadas = set(CLAVES) | {CLAVE_VALOR}
    faltan, sobran = sorted(esperadas - set(datos)), sorted(set(datos) - esperadas)
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"el bloque de la variable no tiene las claves esperadas: {'; '.join(partes)}")

    for clave, tipo in CLAVES.items():
        # `obligatoria` en False es legítimo, así que no se le exige "no vacío".
        exigir_forma(datos[clave], tipo, "el bloque de la variable", clave, no_vacio=(tipo is str))

    if datos[CLAVE_VALOR] is not None:
        exigir_forma(datos[CLAVE_VALOR], str, "el bloque de la variable", CLAVE_VALOR, no_vacio=True)

    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque de la variable dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    nombre = datos["nombre"]
    prefijo = f"{identidad['prefijo']}_{identidad['abrev']}_ev_"
    if not nombre.startswith(prefijo):
        raise ErrorPlaybook(f"nombre = {nombre!r} no sigue el patrón {prefijo}<nombre> (`01-convenciones.md` §2)")
    if not _caracteres_de_identificador(nombre):
        raise ErrorPlaybook(f"nombre = {nombre!r} solo puede llevar letras y dígitos ASCII y guión bajo")
    if len(nombre) > LARGO_SCHEMANAME:
        raise ErrorPlaybook(f"nombre tiene {len(nombre)} caracteres; el máximo es {LARGO_SCHEMANAME}")

    exigir_sin_tildes(datos["displayname"], "displayname")
    if len(datos["displayname"]) > LARGO_DISPLAYNAME:
        raise ErrorPlaybook(f"displayname tiene {len(datos['displayname'])} caracteres; el máximo es {LARGO_DISPLAYNAME}")

    if datos["tipovalor"] not in TIPOS_DE_VALOR:
        raise ErrorPlaybook(
            f"tipovalor = {datos['tipovalor']!r} no es válido; los válidos son {sorted(TIPOS_DE_VALOR)}. "
            "Ademas `type` NO se puede cambiar una vez creada la definicion"
        )
    if datos["obligatoria"] and datos["valor"] is None:
        raise ErrorPlaybook(
            "la variable se declara obligatoria pero no trae valor: o le ponés el valor, o no es obligatoria. "
            "Una variable obligatoria y vacía rompe los flujos que la leen"
        )


def validar_playbook(datos, identidad):
    _validar_estructura(datos, identidad)


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
def _leer_definicion(dv, nombre):
    ruta = (
        "environmentvariabledefinitions?$select=environmentvariabledefinitionid,schemaname,displayname,"
        "description,type,isrequired,ismanaged"
        f"&$filter=schemaname eq '{nombre}'"
    )
    cuerpo = leer_entorno(dv, ruta, C_DEFINICION)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_DEFINICION, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_DEFINICION} devolvió {len(filas)} filas para '{nombre}'; se esperaba a lo sumo una")
    return filas[0] if filas else None


def _leer_valor(dv, definicion_id):
    ruta = (
        "environmentvariablevalues?$select=environmentvariablevalueid,value"
        f"&$filter=_environmentvariabledefinitionid_value eq {definicion_id}"
    )
    cuerpo = leer_entorno(dv, ruta, C_VALOR)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_VALOR, "value")
    if len(filas) > 1:
        raise ErrorEntorno(f"{C_VALOR} devolvió {len(filas)} valores para la misma definición; se esperaba a lo sumo uno")
    return filas[0] if filas else None


def _en_la_solucion(dv, solution_id, objeto_id):
    """Sin filtrar por `componenttype`: Learn no publica el de una environment
    variable. Se lee el que la plataforma haya puesto y se informa."""
    ruta = (
        "solutioncomponents?$select=componenttype,objectid"
        f"&$filter=_solutionid_value eq {solution_id} and objectid eq {objeto_id}"
    )
    cuerpo = leer_entorno(dv, ruta, C_COMPONENTES)
    filas = exigir_forma(cuerpo.get("value"), [dict], C_COMPONENTES, "value")
    return filas[0] if filas else None


def _diferencias(datos, definicion):
    difs, corregibles = [], {}
    tipo_actual = exigir_forma(definicion.get("type"), int, C_DEFINICION, "type")
    if tipo_actual != TIPOS_DE_VALOR[datos["tipovalor"]]:
        inverso = {v: k for k, v in TIPOS_DE_VALOR.items()}
        difs.append(
            f"type es {inverso.get(tipo_actual, tipo_actual)} y el playbook dice {datos['tipovalor']} "
            "(INMUTABLE: hay que borrar la definición y rehacerla)"
        )
    for campo, valor in (("displayname", datos["displayname"]), ("description", datos["descripcion"]),
                         ("isrequired", datos["obligatoria"])):
        if definicion.get(campo) != valor:
            difs.append(f"{campo} es {definicion.get(campo)!r} y el playbook dice {valor!r}")
            corregibles[campo] = valor
    if definicion.get("ismanaged"):
        difs.append("la definición está managed en este entorno; no se toca desde acá")
        corregibles.clear()
    return difs, corregibles


def _contra_entorno(dv, datos, identidad, solo_verificar, completar, componente, dormir):
    solucion = identidad["solucion"]
    solution_id = comprobar_solucion_e_idioma(dv, identidad)
    definicion = _leer_definicion(dv, datos["nombre"])
    hubo_escritura = False

    if definicion is None:
        if solo_verificar:
            return "difiere", componente, f"la variable '{datos['nombre']}' no existe en el entorno"
        cuerpo = {
            "schemaname": datos["nombre"],
            "displayname": datos["displayname"],
            "description": datos["descripcion"],
            "type": TIPOS_DE_VALOR[datos["tipovalor"]],
            "isrequired": datos["obligatoria"],
        }
        est, resp, _ = escribir_metadatos(
            dv, "POST", "environmentvariabledefinitions", cuerpo, dormir=dormir, solucion=solucion)
        if est not in (200, 201, 204):
            return "error", componente, f"el alta de la definición devolvió HTTP {est} (se esperaba 204): {resp}"
        definicion = _leer_definicion(dv, datos["nombre"])
        if definicion is None:
            return "error", componente, "el alta no dio error pero la definición no aparece al releer"
        hubo_escritura = True
    elif completar and not solo_verificar:
        difs, corregibles = _diferencias(datos, definicion)
        if not [d for d in difs if "INMUTABLE" in d] and corregibles:
            id_def = exigir_forma(definicion.get("environmentvariabledefinitionid"), str,
                                  C_DEFINICION, "environmentvariabledefinitionid", no_vacio=True)
            est, resp, _ = escribir_metadatos(
                dv, "PATCH", f"environmentvariabledefinitions({id_def})", corregibles, dormir=dormir, solucion=solucion)
            if est not in (200, 204):
                return "error", componente, f"la corrección devolvió HTTP {est} (se esperaba 204): {resp}"
            definicion = _leer_definicion(dv, datos["nombre"])
            hubo_escritura = True

    id_def = exigir_forma(definicion.get("environmentvariabledefinitionid"), str,
                          C_DEFINICION, "environmentvariabledefinitionid", no_vacio=True)

    # El VALOR: de este entorno, nunca con la cabecera de solución.
    valor_actual = _leer_valor(dv, id_def)
    if datos["valor"] is not None and not solo_verificar:
        if valor_actual is None:
            cuerpo = {"value": datos["valor"],
                      "EnvironmentVariableDefinitionId@odata.bind": f"/environmentvariabledefinitions({id_def})"}
            est, resp, _ = escribir_metadatos(dv, "POST", "environmentvariablevalues", cuerpo, dormir=dormir)
            if est not in (200, 201, 204):
                return "error", componente, f"el alta del valor devolvió HTTP {est} (se esperaba 204): {resp}"
            hubo_escritura = True
        elif valor_actual.get("value") != datos["valor"] and completar:
            id_val = exigir_forma(valor_actual.get("environmentvariablevalueid"), str,
                                  C_VALOR, "environmentvariablevalueid", no_vacio=True)
            est, resp, _ = escribir_metadatos(
                dv, "PATCH", f"environmentvariablevalues({id_val})", {"value": datos["valor"]}, dormir=dormir)
            if est not in (200, 204):
                return "error", componente, f"la corrección del valor devolvió HTTP {est} (se esperaba 204): {resp}"
            hubo_escritura = True
        if hubo_escritura:
            valor_actual = _leer_valor(dv, id_def)

    difs, _ = _diferencias(datos, definicion)
    if datos["valor"] is not None:
        actual = valor_actual.get("value") if valor_actual else None
        if actual != datos["valor"]:
            difs.append(f"el valor en este entorno es {actual!r} y el playbook dice {datos['valor']!r}")

    fila = _en_la_solucion(dv, solution_id, id_def)
    if fila is None:
        difs.append(f"la definición no figura como componente de la solución (solutionid {solution_id})")

    if difs:
        estado = "error" if hubo_escritura else "difiere"
        prefijo = "se escribió pero no quedó bien: " if hubo_escritura else ""
        return estado, componente, prefijo + "; ".join(difs)

    sin_valor = " (SIN VALOR en este entorno, a propósito)" if datos["valor"] is None else ""
    return ("creado" if hubo_escritura else "ya_existia"), componente, (
        f"environmentvariabledefinitionid {id_def}, tipo {datos['tipovalor']}{sin_valor}, "
        f"en la solución '{solucion}' con componenttype {fila.get('componenttype')}"
    )


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
        paso = "validar el bloque de la variable"
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
            "uso incorrecto: variable_entorno.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas
    )
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
