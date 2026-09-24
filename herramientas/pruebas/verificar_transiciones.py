#!/usr/bin/env python3
"""Compara la tabla de transiciones del DOMINIO con la copia que tiene el cliente.

**Por qué existe.** `Dominio/TransicionesDeFila.cs` es la autoridad: dice desde qué
estado se puede pasar a cuál. El ribbon necesita saber lo mismo para ocultar los
botones que no corresponden, y como una EnableRule se evalúa en cada cambio de
selección, no puede preguntárselo al servidor: tiene su propia copia en
`recursos/js/comandos.js` (`TRANSICIONES_VALIDAS`).

Dos copias de la misma regla, en dos lenguajes. **Ninguna prueba unitaria puede
cruzarlas**: las de C# no ven el JavaScript y no hay pruebas de JavaScript. Si
alguien agrega una transición al dominio y no toca el JS, el botón no aparece y
nadie entiende por qué. Esto es lo único que lo detecta.

No se ejecuta nada ni se toca el entorno: son dos archivos leídos de disco.

Uso:
    python3 herramientas/pruebas/verificar_transiciones.py
    → sale con 0 si coinciden, 1 si no.
"""

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOMINIO = os.path.join(RAIZ, "src", "Sanic.Mppp.Plugins", "Dominio", "TransicionesDeFila.cs")
CLIENTE = os.path.join(RAIZ, "recursos", "js", "comandos.js")

# El mismo estado se escribe distinto en cada lado. Es el único punto donde los dos
# vocabularios se tocan, así que va acá, explícito, y no repartido en el código.
CSHARP_A_JS = {
    "Validada": "VALIDADA",
    "Digitada": "DIGITADA",
    "Aprobada": "APROBADA",
    "RechazadaEnAS400": "RECHAZADA_AS400",
    "Anulada": "ANULADA",
}


def transiciones_del_dominio():
    """Los pares (desde, hacia) de la tabla de `TransicionesDeFila`."""
    texto = open(DOMINIO, encoding="utf-8").read()
    pares = re.findall(
        r"\[\(EstadoDeLaFila\.(\w+),\s*EstadoDeLaFila\.(\w+)\)\]", texto)
    if not pares:
        raise SystemExit(f"no se encontró ninguna transición en {DOMINIO}; ¿cambió la forma de la tabla?")
    return {(d, h) for d, h in pares}


def transiciones_del_cliente():
    """Los pares (desde, hacia) que el ribbon usa para mostrar u ocultar.

    Salen de dos lugares del mismo archivo: `TRANSICIONES_VALIDAS` (los estados
    DESDE los que cada acción se ofrece) y la función pública de cada acción (el
    estado HACIA el que escribe, en su `cambioDe(FILA, FILA.X)`).
    """
    texto = open(CLIENTE, encoding="utf-8").read()

    bloque = re.search(r"var TRANSICIONES_VALIDAS = \{(.*?)\};", texto, re.S)
    if not bloque:
        raise SystemExit(f"no se encontró TRANSICIONES_VALIDAS en {CLIENTE}")
    desde_por_accion = {}
    for accion, lista in re.findall(r"(\w+):\s*\[([^\]]*)\]", bloque.group(1)):
        desde_por_accion[accion] = re.findall(r"FILA\.(\w+)", lista)

    # `digitada: function (...) { ... cambioDe(FILA, FILA.DIGITADA) ... }`
    hacia_por_accion = {}
    for accion in desde_por_accion:
        # el nombre de la función pública no siempre es el de la clave del mapa
        nombre = {"rechazadaas400": "rechazadaAs400"}.get(accion, accion)
        m = re.search(nombre + r":\s*function[^}]*?cambioDe\(FILA,\s*FILA\.(\w+)\)", texto, re.S)
        if not m:
            raise SystemExit(f"no se encontró a qué estado escribe la acción {nombre!r} en {CLIENTE}")
        hacia_por_accion[accion] = m.group(1)

    pares = set()
    for accion, desdes in desde_por_accion.items():
        for d in desdes:
            pares.add((d, hacia_por_accion[accion]))
    return pares


def main():
    dominio = {(CSHARP_A_JS.get(d, d), CSHARP_A_JS.get(h, h)) for d, h in transiciones_del_dominio()}
    cliente = transiciones_del_cliente()

    sin_traducir = {e for par in dominio for e in par} - set(CSHARP_A_JS.values())
    if sin_traducir:
        print(f"  Hay estados del dominio sin equivalente declarado: {sorted(sin_traducir)}")
        print("  Agregalos a CSHARP_A_JS o la comparación miente.")
        return 1

    print(f"dominio  (TransicionesDeFila.cs): {len(dominio)} transiciones")
    print(f"cliente  (comandos.js)         : {len(cliente)} transiciones\n")

    faltan = sorted(dominio - cliente)
    sobran = sorted(cliente - dominio)
    for d, h in sorted(dominio & cliente):
        print(f"   OK   {d} → {h}")
    for d, h in faltan:
        print(f"   FALTA en el cliente: {d} → {h}  (el botón no se va a ofrecer nunca)")
    for d, h in sobran:
        print(f"   SOBRA en el cliente: {d} → {h}  (el botón se ofrece y el plugin lo rechaza)")

    if faltan or sobran:
        print(f"\n  NO COINCIDEN: {len(faltan)} de menos, {len(sobran)} de más.")
        print("  La autoridad es el dominio: hay que alinear `TRANSICIONES_VALIDAS` de comandos.js.")
        return 1
    print("\nLas dos copias dicen lo mismo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
