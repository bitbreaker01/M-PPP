#!/usr/bin/env python3
"""Carga filas de DATOS en una tabla de Dataverse, desde un playbook de tipo
`datos`. Contrato: `power-platform-construir`.

    python3 herramientas/construir/datos.py <playbook.md> [--solo-verificar] [--completar]

Datos, no metadatos: estas filas **no** son componentes de solución, así que no
se manda la cabecera `MSCRM.SolutionUniqueName` ni se comprueba pertenencia.
Igual se validan la solución y el idioma de la Identidad: es el chequeo barato
de "estoy apuntando al entorno que creo".

Idempotencia: cada fila se busca por su CLAVE DE NEGOCIO (las columnas que
declara `clave`), no por GUID. Correr la herramienta dos veces no duplica nada.

Nunca borra. Una fila que está en el entorno y no en el playbook se denuncia;
una que difiere se informa, y solo con `--completar` se corrige con un PATCH de
las columnas declaradas.

Ojo con los steps: al crear una fila se disparan los plugins registrados sobre
esa tabla (normalizar y validar, nombre calculado). Si un valor del playbook no
pasa la validación del plugin, el alta se rechaza y acá se ve el motivo. Eso es
bueno: es el mismo control que va a ver una persona.

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
    leer_entorno,
    leer_texto,
    obtener_componente,
    obtener_identidad,
    salida,
)

TIPO = "datos"

MENSAJE_FALLO_CLIENTE = (
    "no se pudo inicializar el cliente de Dataverse (fallo de red o de credenciales); "
    "no se expone el detalle porque podría incluir datos de la solicitud de token"
)

CLAVES = {"tipo": str, "tabla": str, "clave": list, "filas": list}

C_TABLA = "la consulta de la definición de la tabla (GET EntityDefinitions)"
C_CHOICE = "la consulta del choice global (GET GlobalOptionSetDefinitions)"
C_FILAS = "la consulta de las filas de la tabla"


# ---------------------------------------------------------------------------
# Validación sin red
# ---------------------------------------------------------------------------
def _es_escalar(valor):
    # Un booleano ES un int en Python, pero acá los dos son escalares válidos.
    return valor is None or isinstance(valor, (str, int, float, bool))


def _validar_estructura(datos):
    faltan, sobran = sorted(set(CLAVES) - set(datos)), sorted(set(datos) - set(CLAVES))
    if faltan or sobran:
        partes = []
        if faltan:
            partes.append(f"faltan {faltan}")
        if sobran:
            partes.append(f"sobran {sobran}")
        raise ErrorPlaybook(f"el bloque de datos no tiene las claves esperadas: {'; '.join(partes)}")
    for clave, tipo in CLAVES.items():
        exigir_forma(datos[clave], tipo, "el bloque de datos", clave, no_vacio=True)
    if datos["tipo"] != TIPO:
        raise ErrorPlaybook(f"el bloque de datos dice tipo = {datos['tipo']!r}, se esperaba {TIPO!r}")

    clave = exigir_forma(datos["clave"], [str], "el bloque de datos", "clave", no_vacio=True)
    if len(set(clave)) != len(clave):
        raise ErrorPlaybook(f"clave tiene columnas repetidas: {clave}")

    vistas = set()
    for i, fila in enumerate(datos["filas"]):
        donde = f"la fila [{i}]"
        exigir_forma(fila, dict, "el bloque de datos", f"filas[{i}]")
        faltan_clave = [c for c in clave if c not in fila]
        if faltan_clave:
            raise ErrorPlaybook(f"{donde}: no trae las columnas de la clave de negocio {faltan_clave}")
        for columna, valor in fila.items():
            if isinstance(valor, dict) and "lookup" in valor:
                _validar_lookup(valor["lookup"], donde, columna)
                if len(valor) != 1:
                    raise ErrorPlaybook(f"{donde}: la columna '{columna}' declara 'lookup' y además {sorted(set(valor) - {'lookup'})}")
            elif isinstance(valor, dict):
                _validar_choice(valor, donde, columna)
            elif not _es_escalar(valor):
                raise ErrorPlaybook(
                    f"{donde}: la columna '{columna}' tiene un valor de tipo {type(valor).__name__}; "
                    "solo se admiten escalares, {choice, etiqueta} o {lookup: {tabla, clave}}"
                )
        huella = tuple(_texto_de_clave(fila[c]) for c in clave)
        if huella in vistas:
            raise ErrorPlaybook(f"{donde}: hay otra fila con la misma clave de negocio {huella}")
        vistas.add(huella)


def _validar_lookup(valor, donde, columna):
    """Un lookup se declara por la CLAVE DE NEGOCIO de la fila apuntada, nunca
    por GUID: un playbook con GUID adentro solo sirve en el entorno donde se
    escribió, y nadie puede revisarlo de un vistazo."""
    faltan = sorted({"tabla", "clave"} - set(valor))
    sobran = sorted(set(valor) - {"tabla", "clave"})
    if faltan or sobran:
        raise ErrorPlaybook(
            f"{donde}: la columna '{columna}' es un lookup y solo se admite {{tabla, clave}}; "
            f"faltan {faltan}, sobran {sobran}"
        )
    exigir_forma(valor["tabla"], str, donde, f"{columna}.tabla", no_vacio=True)
    clave = exigir_forma(valor["clave"], dict, donde, f"{columna}.clave")
    if not clave:
        raise ErrorPlaybook(f"{donde}: el lookup de '{columna}' no trae ninguna columna en su clave de negocio")
    for c, v in clave.items():
        if not _es_escalar(v) or v is None:
            raise ErrorPlaybook(f"{donde}: la clave del lookup de '{columna}' solo admite escalares no nulos ('{c}')")


def _validar_choice(valor, donde, columna):
    """Un choice se declara por su ETIQUETA, no por su número. Escribir
    `159460001` en un playbook es imposible de revisar; escribir `"COR"` se
    revisa de un vistazo, y además la herramienta comprueba que exista."""
    faltan, sobran = sorted({"choice", "etiqueta"} - set(valor)), sorted(set(valor) - {"choice", "etiqueta"})
    if faltan or sobran:
        raise ErrorPlaybook(
            f"{donde}: la columna '{columna}' es un objeto y solo se admite {{choice, etiqueta}}; "
            f"faltan {faltan}, sobran {sobran}"
        )
    exigir_forma(valor["choice"], str, donde, f"{columna}.choice", no_vacio=True)
    exigir_forma(valor["etiqueta"], str, donde, f"{columna}.etiqueta", no_vacio=True)


def _texto_de_clave(valor):
    """La huella de un valor para comparar claves de negocio, sin depender de
    la cultura: los booleanos y números se pasan a texto de forma fija."""
    if isinstance(valor, dict) and "lookup" in valor:
        ref = valor["lookup"]
        return ref["tabla"] + ":" + ",".join(f"{c}={ref['clave'][c]}" for c in sorted(ref["clave"]))
    if isinstance(valor, dict):
        return f"{valor['choice']}:{valor['etiqueta']}"
    if valor is True:
        return "true"
    if valor is False:
        return "false"
    return str(valor)


def validar_playbook(datos):
    _validar_estructura(datos)


def literal_odata(valor):
    """El valor como literal de un `$filter`. Un apóstrofo se duplica: es la
    única forma de escaparlo en OData, y sin eso un nombre con apóstrofo
    rompería la consulta (o algo peor)."""
    if valor is True:
        return "true"
    if valor is False:
        return "false"
    if valor is None:
        return "null"
    if isinstance(valor, (int, float)):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Contra el entorno
# ---------------------------------------------------------------------------
class Entorno:
    """Resuelve y cachea lo que hace falta del entorno: el conjunto de
    entidades de la tabla y el número de cada etiqueta de choice."""

    def __init__(self, dv):
        self._dv = dv
        self._choices = {}
        self._tablas = {}
        self._filas = {}

    def id_de_fila(self, logical_name, clave):
        """El id de la fila apuntada por un lookup, buscada por su CLAVE DE
        NEGOCIO. Se cachea: varias filas del playbook suelen apuntar a la
        misma. Si no existe, `Bloqueado`: falta sembrar el padre primero."""
        huella = (logical_name, tuple(sorted((c, str(v)) for c, v in clave.items())))
        if huella not in self._filas:
            conjunto, primaria = self.tabla(logical_name)
            filtro = " and ".join(f"{c} eq {literal_odata(clave[c])}" for c in sorted(clave))
            cuerpo = leer_entorno(self._dv, f"{conjunto}?$select={primaria}&$filter={filtro}", C_FILAS)
            filas = exigir_forma(cuerpo.get("value"), [dict], C_FILAS, "value")
            if not filas:
                raise Bloqueado(
                    f"el lookup apunta a una fila de '{logical_name}' que no existe ({filtro}); "
                    "hay que sembrar primero la tabla apuntada"
                )
            if len(filas) > 1:
                raise ErrorEntorno(
                    f"el lookup a '{logical_name}' encontró {len(filas)} filas con la misma clave de negocio ({filtro})"
                )
            self._filas[huella] = exigir_forma(filas[0].get(primaria), str, C_FILAS, primaria, no_vacio=True)
        return self._filas[huella]

    def tabla(self, logical_name):
        if logical_name in self._tablas:
            return self._tablas[logical_name]
        ruta = f"EntityDefinitions(LogicalName='{logical_name}')?$select=EntitySetName,PrimaryIdAttribute"
        cuerpo = leer_entorno(self._dv, ruta, C_TABLA, admite_404=True)
        if cuerpo is None:
            raise Bloqueado(f"la tabla '{logical_name}' no existe en el entorno")
        conjunto = exigir_forma(cuerpo.get("EntitySetName"), str, C_TABLA, "EntitySetName", no_vacio=True)
        primaria = exigir_forma(cuerpo.get("PrimaryIdAttribute"), str, C_TABLA, "PrimaryIdAttribute", no_vacio=True)
        self._tablas[logical_name] = (conjunto, primaria)
        return self._tablas[logical_name]

    def valor_de_choice(self, nombre, etiqueta):
        if nombre not in self._choices:
            ruta = f"GlobalOptionSetDefinitions(Name='{nombre}')"
            cuerpo = leer_entorno(self._dv, ruta, C_CHOICE, admite_404=True)
            if cuerpo is None:
                raise Bloqueado(f"el choice global '{nombre}' no existe en el entorno")
            por_etiqueta = {}
            for opcion in exigir_forma(cuerpo.get("Options"), [dict], C_CHOICE, "Options", no_vacio=True):
                etiquetas = exigir_forma(opcion.get("Label"), dict, C_CHOICE, "Options.Label")
                for loc in exigir_forma(etiquetas.get("LocalizedLabels"), [dict], C_CHOICE, "LocalizedLabels"):
                    texto = exigir_forma(loc.get("Label"), str, C_CHOICE, "LocalizedLabels.Label")
                    por_etiqueta[texto] = exigir_forma(opcion.get("Value"), int, C_CHOICE, "Options.Value")
            self._choices[nombre] = por_etiqueta
        por_etiqueta = self._choices[nombre]
        if etiqueta not in por_etiqueta:
            raise Bloqueado(
                f"el choice '{nombre}' no tiene la opción {etiqueta!r}; las que tiene son {sorted(por_etiqueta)}"
            )
        return por_etiqueta[etiqueta]


def cuerpo_de_fila(entorno, fila):
    """La fila del playbook traducida a lo que entiende el Web API.

    Devuelve `(cuerpo, esperado)`. No son lo mismo y por eso van separados: un
    lookup se ESCRIBE como `columna@odata.bind` con una ruta, y se LEE como
    `_columna_value` con un GUID. Comparar lo escrito contra lo leído sin esta
    traducción daría siempre "difiere"."""
    cuerpo, esperado = {}, {}
    for columna, valor in fila.items():
        if isinstance(valor, dict) and "lookup" in valor:
            ref = valor["lookup"]
            conjunto, _ = entorno.tabla(ref["tabla"])
            id_apuntado = entorno.id_de_fila(ref["tabla"], ref["clave"])
            cuerpo[f"{columna}@odata.bind"] = f"/{conjunto}({id_apuntado})"
            esperado[f"_{columna}_value"] = id_apuntado
        elif isinstance(valor, dict):
            numero = entorno.valor_de_choice(valor["choice"], valor["etiqueta"])
            cuerpo[columna] = numero
            esperado[columna] = numero
        else:
            cuerpo[columna] = valor
            esperado[columna] = valor
    return cuerpo, esperado


def nombre_leido(fila, columna):
    """Cómo se llama esa columna al LEERLA: un lookup se lee como `_col_value`."""
    valor = fila[columna]
    return f"_{columna}_value" if isinstance(valor, dict) and "lookup" in valor else columna


def _buscar_fila(dv, conjunto, primaria, clave_leida, esperado, columnas):
    filtro = " and ".join(f"{c} eq {literal_odata(esperado[c])}" for c in clave_leida)
    seleccion = ",".join(sorted({primaria} | set(columnas)))
    ruta = f"{conjunto}?$select={seleccion}&$filter={filtro}"
    respuesta = leer_entorno(dv, ruta, C_FILAS)
    filas = exigir_forma(respuesta.get("value"), [dict], C_FILAS, "value")
    if len(filas) > 1:
        raise ErrorEntorno(
            f"{C_FILAS} devolvió {len(filas)} filas para la clave de negocio {filtro}; "
            "la clave alternativa de esa tabla no está haciendo su trabajo"
        )
    return filas[0] if filas else None


def _diferencias(cuerpo, fila):
    difs = {}
    for columna, esperado in cuerpo.items():
        actual = fila.get(columna)
        if actual != esperado:
            difs[columna] = (actual, esperado)
    return difs


def _contra_entorno(dv, datos, identidad, solo_verificar, completar, componente, dormir):
    comprobar_solucion_e_idioma(dv, identidad)
    entorno = Entorno(dv)
    conjunto, primaria = entorno.tabla(datos["tabla"])
    clave = datos["clave"]

    # TODOS los choice y TODOS los lookups se resuelven ANTES de escribir la
    # primera fila. Si una etiqueta o una fila apuntada no existe, esto lanza
    # `Bloqueado` con el entorno intacto; si se resolviera fila por fila, un
    # playbook con un error en la fila 12 dejaría once filas escritas y la
    # carga a medias.
    preparadas = []
    for fila in datos["filas"]:
        cuerpo, esperado = cuerpo_de_fila(entorno, fila)
        clave_leida = [nombre_leido(fila, c) for c in clave]
        etiqueta = " / ".join(str(esperado[c]) for c in clave_leida)
        preparadas.append((cuerpo, esperado, clave_leida, etiqueta))

    creadas, iguales, difs = [], [], []
    for cuerpo, esperado, clave_leida, etiqueta in preparadas:
        existente = _buscar_fila(dv, conjunto, primaria, clave_leida, esperado, esperado.keys())

        if existente is None:
            if solo_verificar:
                difs.append(f"{etiqueta}: no existe en el entorno")
                continue
            est, resp, _ = escribir_metadatos(dv, "POST", conjunto, cuerpo, dormir=dormir)
            if est not in (200, 201, 204):
                # Un 400 acá suele ser un plugin nuestro rechazando el valor:
                # el mensaje del plugin es lo que hay que leer.
                return "error", componente, f"{etiqueta}: el alta devolvió HTTP {est} (se esperaba 204): {resp}"
            existente = _buscar_fila(dv, conjunto, primaria, clave_leida, esperado, esperado.keys())
            if existente is None:
                return "error", componente, f"{etiqueta}: el alta no dio error pero la fila no aparece al releer"
            d = _diferencias(esperado, existente)
            if d:
                detalle = "; ".join(f"{c}: quedó {a!r} y el playbook dice {e!r}" for c, (a, e) in sorted(d.items()))
                return "error", componente, f"{etiqueta}: se creó pero no quedó como el playbook — {detalle}"
            creadas.append(etiqueta)
            continue

        d = _diferencias(esperado, existente)
        if not d:
            iguales.append(etiqueta)
            continue

        if completar and not solo_verificar:
            id_fila = exigir_forma(existente.get(primaria), str, C_FILAS, primaria, no_vacio=True)
            # Se PATCHea con los nombres de ESCRITURA: un lookup se corrige con
            # su `@odata.bind`, nunca con `_col_value`, que es de solo lectura.
            leido_a_escritura = {k: k for k in cuerpo}
            leido_a_escritura.update({f"_{k.split('@')[0]}_value": k for k in cuerpo if "@odata.bind" in k})
            cambios = {leido_a_escritura[c]: cuerpo[leido_a_escritura[c]] for c in d}
            est, resp, _ = escribir_metadatos(dv, "PATCH", f"{conjunto}({id_fila})", cambios, dormir=dormir)
            if est not in (200, 204):
                return "error", componente, f"{etiqueta}: la corrección devolvió HTTP {est} (se esperaba 204): {resp}"
            revisada = _buscar_fila(dv, conjunto, primaria, clave_leida, esperado, esperado.keys())
            pendientes = _diferencias(esperado, revisada or {})
            if pendientes:
                detalle = "; ".join(f"{c}: quedó {a!r} y el playbook dice {e!r}" for c, (a, e) in sorted(pendientes.items()))
                return "error", componente, f"{etiqueta}: se corrigió pero sigue distinta — {detalle}"
            creadas.append(etiqueta)
            continue

        detalle = "; ".join(f"{c} es {a!r} y el playbook dice {e!r}" for c, (a, e) in sorted(d.items()))
        difs.append(f"{etiqueta}: {detalle}")

    if difs:
        estado = "error" if creadas else "difiere"
        prefijo = "se escribió pero quedaron diferencias: " if creadas else ""
        return estado, componente, prefijo + "; ".join(difs)

    resumen = f"{len(creadas)} escritas y {len(iguales)} que ya estaban, de {len(datos['filas'])}, en {datos['tabla']}"
    return ("creado" if creadas else "ya_existia"), componente, resumen


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
        if isinstance(datos.get("tabla"), str):
            componente = datos["tabla"]
        paso = "leer el bloque '## 1. Identidad'"
        identidad = obtener_identidad(secciones)
        paso = "validar el bloque de datos"
        validar_playbook(datos)
    except ErrorPlaybook as e:
        return "error", componente, str(e)
    except Bloqueado as e:
        return "bloqueado", componente, str(e)
    except OSError as e:
        return "error", componente, f"no se pudo leer el playbook '{ruta_playbook}': {e}"
    except Exception as e:
        return "error", componente, f"fallo inesperado validando el playbook (offline), al {paso}: {type(e).__name__}: {e}"

    print(f"Playbook leído y validado (offline). tipo={TIPO} tabla={componente} filas={len(datos['filas'])}")
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
            "uso incorrecto: datos.py <playbook.md> [--solo-verificar] [--completar]"
            + (f"; banderas desconocidas: {desconocidas}" if desconocidas else ""),
        )
    from dataverse_api import Dataverse

    estado, componente, detalle = construir(
        rutas[0], "--solo-verificar" in banderas, Dataverse, completar="--completar" in banderas
    )
    return salida(estado, componente, detalle)


if __name__ == "__main__":
    sys.exit(main())
