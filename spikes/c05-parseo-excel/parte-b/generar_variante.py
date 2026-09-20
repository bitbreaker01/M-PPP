#!/usr/bin/env python3
"""Genera una variante de la plantilla real con N filas de datos sinteticos en la hoja
'Datos' (filas 13 en adelante, columnas B a K), para medir la pregunta 2 del spike C-05
parte B con volumenes distintos a los 25 reales. Solo stdlib (zipfile + re).

No modifica el archivo original (datos/plantilla/...); escribe una copia nueva.

Uso:
    python3 spikes/c05-parseo-excel/parte-b/generar_variante.py 100 parte-b/variante-100filas.xlsx
"""
import re
import sys
import zipfile

RAIZ_PLANTILLA = "datos/plantilla/Inclusiones_Exclusiones en PPP.xlsx"
PRIMERA_FILA = 13

GESTIONES = ["INCLUSION", "EXCLUSION", "MODIFICACION"]
CLASIFICACIONES = ["BAC", "ACH", "CK"]
BANCOS = ["BAC", "BANPRO", "FICOHSA", "LAFISE"]
MONEDAS = ["COR", "USD"]


def escapar(texto):
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def celda_inline(ref, valor):
    return f'<c r="{ref}" t="inlineStr"><is><t>{escapar(valor)}</t></is></c>'


def generar_fila(numero_fila, i):
    celdas = [
        celda_inline(f"B{numero_fila}", GESTIONES[i % len(GESTIONES)]),
        celda_inline(f"C{numero_fila}", CLASIFICACIONES[i % len(CLASIFICACIONES)]),
        celda_inline(f"D{numero_fila}", str(1000 + i)),
        celda_inline(f"E{numero_fila}", f"Proveedor de prueba {i}"),
        celda_inline(f"F{numero_fila}", "CNA"),
        celda_inline(f"G{numero_fila}", f"{100000000 + i:09d}"),
        celda_inline(f"H{numero_fila}", f"REF-{i}"),
        celda_inline(f"I{numero_fila}", str(1600000000000000 + i)),
        celda_inline(f"J{numero_fila}", MONEDAS[i % len(MONEDAS)]),
        celda_inline(f"K{numero_fila}", BANCOS[i % len(BANCOS)]),
    ]
    return f'<row r="{numero_fila}">' + "".join(celdas) + "</row>"


def generar(cantidad_filas):
    with zipfile.ZipFile(RAIZ_PLANTILLA) as z:
        entradas = {n: z.read(n) for n in z.namelist()}

    sheet1 = entradas["xl/worksheets/sheet1.xml"].decode("utf-8")

    # Saca las filas 13 en adelante que ya trae la plantilla distribuible (vacias), para no
    # duplicar indices de fila.
    sheet1_sin_datos = re.sub(
        r'<row r="(?:1[3-9]|[2-9]\d|\d{3,})"[^>]*(?:/>|>.*?</row>)',
        "",
        sheet1,
        flags=re.S,
    )

    filas_nuevas = "".join(
        generar_fila(PRIMERA_FILA + i, i) for i in range(cantidad_filas)
    )

    sheet1_final = sheet1_sin_datos.replace("</sheetData>", filas_nuevas + "</sheetData>")
    entradas["xl/worksheets/sheet1.xml"] = sheet1_final.encode("utf-8")
    return entradas


def escribir(entradas, ruta_salida):
    with zipfile.ZipFile(ruta_salida, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in entradas.items():
            z.writestr(nombre, contenido)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cantidad = int(sys.argv[1])
    salida = sys.argv[2]
    entradas = generar(cantidad)
    escribir(entradas, salida)
    print(f"Generado {salida}: {cantidad} filas sinteticas (13..{12 + cantidad})")


if __name__ == "__main__":
    main()
