#!/usr/bin/env python3
"""Indicador de progreso de la construcción: x/Y componentes de la fase 1.

Fuente: `playbooks/progreso.json` (una fila por renglón del inventario que
pasa por el ciclo de construcción; `total` > 1 cuando el renglón agrupa varios
componentes, p. ej. las vistas). Se actualiza al CERRAR cada ciclo.
Comprueba que el libro no se haya desalineado del inventario.

Uso:  python3 herramientas/progreso.py            # tablero completo
      python3 herramientas/progreso.py --linea    # solo la línea x/Y
"""
import json, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRO = os.path.join(RAIZ, "playbooks", "progreso.json")
INVENTARIO = os.path.join(RAIZ, "diseno", "06-inventario-componentes.md")


def barra(hechos, total, ancho=24):
    llenos = 0 if total == 0 else round(ancho * hechos / total)
    if hechos and not llenos:
        llenos = 1
    return "█" * llenos + "░" * (ancho - llenos)


def ids_del_inventario():
    ids = set()
    with open(INVENTARIO, encoding="utf-8") as f:
        for linea in f:
            m = re.match(r"^\| (\d+\.\d+[a-z]?) \|", linea)
            if m:
                ids.add(m.group(1))
    return ids


def main():
    libro = json.load(open(LIBRO, encoding="utf-8"))
    filas = libro["filas"]
    hechos = sum(f["hechos"] for f in filas)
    total = sum(f["total"] for f in filas)
    pct = 100 * hechos / total if total else 0
    linea = f"{libro['proyecto']} — componentes construidos: {hechos}/{total}  {barra(hechos, total)}  {pct:.1f} %"
    if "--linea" in sys.argv:
        print(linea)
        return 0
    print(linea)
    if libro.get("en_curso"):
        print(f"En curso: {libro['en_curso']}")
    print()
    for clave, nombre in libro["grupos"].items():
        del_grupo = [f for f in filas if f["grupo"] == clave]
        h, t = sum(f["hechos"] for f in del_grupo), sum(f["total"] for f in del_grupo)
        marca = "✔" if t and h == t else " "
        print(f" {marca} {clave:<8} {nombre:<46} {h:>3}/{t:<3} {barra(h, t, 12)}")
    # coherencia con el inventario
    inv = ids_del_inventario()
    conocidos = {f["id"] for f in filas} | set(libro.get("fuera_de_alcance", {}))
    sobran, faltan = sorted(conocidos - inv), sorted(inv - conocidos)
    malos = [f["id"] for f in filas if not 0 <= f["hechos"] <= f["total"]]
    if sobran or faltan or malos:
        print()
        if faltan:
            print(f"AVISO: renglones del inventario que el libro no conoce: {faltan}")
        if sobran:
            print(f"AVISO: renglones del libro que ya no están en el inventario: {sobran}")
        if malos:
            print(f"AVISO: 'hechos' fuera de rango en: {malos}")
        return 1
    print()
    print(f"Hecho = {libro['criterio_hecho']}.")
    print(f"Fuera de la cuenta: {len(libro.get('fuera_de_alcance', {}))} renglones (fases 2 y 3, versión 1.1 y tareas de administración).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
