#!/usr/bin/env python3
"""Genera los Excel de los casos de prueba funcionales, a partir de la
plantilla REAL del cliente.

    python3 herramientas/pruebas/generar_excel.py

Parte de `datos/plantilla/Inclusiones_Exclusiones en PPP.xlsx` y solo escribe
las filas de datos. Así cada archivo de prueba es, hasta el último detalle de
formato, el mismo que el cliente manda: encabezados en la fila 12, datos desde
la 13, columnas B a K y la hoja `Datos` con su hoja `Listas` al lado.

**Por qué no se arma un Excel desde cero**: la validación lee la plantilla con
la estructura del parámetro `plantilla.estructura`. Un archivo hecho a mano
podría fallar por una diferencia de formato que el cliente nunca va a producir,
y una prueba que falla por el andamio no prueba nada.

Los valores salen de `plantilla.listas` y de los planes de prueba que crea
`preparar_datos.py`. Cada caso está pensado para que falle UNA regla, o para
que no falle ninguna.
"""
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLANTILLA = os.path.join(RAIZ, "datos", "plantilla", "Inclusiones_Exclusiones en PPP.xlsx")
DESTINO = os.path.join(RAIZ, "pruebas", "adjuntos")

# `plantilla.estructura`, verificado contra el entorno el 2026-09-22.
HOJA = "Datos"
PRIMERA_FILA = 13
COLUMNAS = {"gestion": "B", "clasificacion": "C", "numeroPlan": "D", "nombreBeneficiario": "E",
            "tipoIdentificacion": "F", "numeroIdentificacion": "G", "referencia": "H",
            "numeroCuenta": "I", "moneda": "J", "banco": "K"}


def fila(gestion="Inclusion", clasificacion="ACH", plan="PR11", nombre="Juan Perez Prueba",
         tipoid="CNA", numeroid="0011805900012X", referencia="", cuenta="12345678901234",
         moneda="COR", banco="BAC"):
    return {"gestion": gestion, "clasificacion": clasificacion, "numeroPlan": plan,
            "nombreBeneficiario": nombre, "tipoIdentificacion": tipoid,
            "numeroIdentificacion": numeroid, "referencia": referencia,
            "numeroCuenta": cuenta, "moneda": moneda, "banco": banco}


# ---------------------------------------------------------------------------
# Los casos. Cada uno: (archivo, [filas], hoja a renombrar o None)
# ---------------------------------------------------------------------------
def casos():
    c = []

    # E01 — todo bien, plan formato 11 (ACH). Tres filas validas.
    c.append(("E01-feliz-formato11.xlsx", [
        fila(nombre="Ana Lopez Prueba", cuenta="10203040506070"),
        fila(gestion="Exclusion", nombre="Bruno Diaz Prueba", cuenta="11223344556677"),
        fila(gestion="Modificacion", nombre="Carla Ruiz Prueba", cuenta="99887766554433"),
    ], None))

    # E02 — valores fuera de las listas. Falla LISTAS_VALIDAS.
    c.append(("E02-listas-invalidas.xlsx", [
        fila(gestion="Alta", nombre="Falla Gestion"),
        fila(moneda="EUR", nombre="Falla Moneda"),
        fila(banco="SANTANDER", nombre="Falla Banco"),
        fila(tipoid="XXX", nombre="Falla TipoID"),
        fila(clasificacion="TRANSFER", nombre="Falla Clasificacion"),
    ], None))

    # E03 — largos por encima del maximo de `plantilla.estructura`.
    c.append(("E03-largos-invalidos.xlsx", [
        fila(nombre="Nombre Larguisimo De Beneficiario Que Pasa Los Cuarenta Y Cuatro"),  # max 44
        fila(plan="PR11XX", nombre="Plan Largo"),                                          # max 4
        fila(cuenta="123456789012345678901", nombre="Cuenta Larga"),                       # max 16
        fila(numeroid="0011805900012XABCDEFGH", nombre="Identificacion Larga"),            # max 16
    ], None))

    # E04 — plan que no existe. Falla PLAN_EXISTE.
    c.append(("E04-plan-inexistente.xlsx", [
        fila(plan="ZZ99", nombre="Plan Fantasma"),
    ], None))

    # E05 — plan formato 11 con clasificacion distinta de ACH. Falla FORMATO_11_SOLO_ACH.
    c.append(("E05-formato11-no-ach.xlsx", [
        fila(clasificacion="BAC", nombre="Once Con BAC"),
        fila(clasificacion="CK", nombre="Once Con CK"),
    ], None))

    # E06 — campos obligatorios vacios. Falla OBLIGATORIEDAD.
    # La ultima fila deja vacia SOLO la Referencia, que es opcional: tiene que pasar.
    c.append(("E06-obligatoriedad.xlsx", [
        fila(nombre="", ),
        fila(cuenta="", nombre="Sin Cuenta"),
        fila(tipoid="", nombre="Sin Tipo Id"),
        fila(nombre="Sin Referencia Y Esta Bien", referencia=""),
    ], None))

    # E07 — moneda de la cuenta distinta de la del plan (PR10 es USD).
    c.append(("E07-moneda-distinta.xlsx", [
        fila(plan="PR10", clasificacion="BAC", moneda="COR", nombre="Cordobas En Plan Dolar"),
    ], None))

    # E08 — plan sobre el que el remitente NO tiene autorizacion.
    c.append(("E08-sin-autorizacion.xlsx", [
        fila(plan="PRNA", clasificacion="BAC", nombre="Plan Sin Autorizacion"),
    ], None))

    # E09 — referencia de formato 11 que no se puede construir.
    c.append(("E09-referencia-formato11.xlsx", [
        fila(cuenta="1234ABCD5678", nombre="Cuenta Con Letras"),
        fila(cuenta="123456789012345678", nombre="Cuenta De Dieciocho"),
    ], None))

    # E10 — mezcla: dos validas, una sin autorizacion, una rechazada.
    c.append(("E10-mixto.xlsx", [
        fila(nombre="Valida Uno", cuenta="10101010101010"),
        fila(nombre="Valida Dos", cuenta="20202020202020"),
        fila(plan="PRNA", clasificacion="BAC", nombre="Sin Autorizacion"),
        fila(moneda="EUR", nombre="Moneda Invalida"),
    ], None))

    # E11 — ninguna fila. Falla TIENE_FILAS.
    c.append(("E11-sin-filas.xlsx", [], None))

    # E12 — la hoja de datos se llama distinto. Falla ESTRUCTURA_PLANTILLA.
    c.append(("E12-hoja-renombrada.xlsx", [fila(nombre="No Se Deberia Leer")], "Datos2"))

    # E13 — plan formato 06: la referencia se respeta TAL CUAL, no se deriva.
    c.append(("E13-formato06-referencia-libre.xlsx", [
        fila(plan="PR06", clasificacion="BAC", referencia="REF-LIBRE-000123", nombre="Formato Seis"),
    ], None))

    # E14 — volumen: 100 filas validas, para mirar el tiempo de la validacion.
    c.append(("E14-volumen-100.xlsx", [
        fila(nombre=f"Beneficiario Volumen {i:03}", cuenta=f"{10000000000000 + i}")
        for i in range(1, 101)
    ], None))

    # E15 — plan que existe pero esta INACTIVO. Falla PLAN_EXISTE.
    c.append(("E15-plan-inactivo.xlsx", [
        fila(plan="PRIN", clasificacion="BAC", nombre="Plan Desactivado"),
    ], None))

    return c


def escribir(nombre_archivo, filas, renombrar_hoja):
    import openpyxl

    destino = os.path.join(DESTINO, nombre_archivo)
    shutil.copyfile(PLANTILLA, destino)
    libro = openpyxl.load_workbook(destino)
    hoja = libro[HOJA]
    for i, datos in enumerate(filas):
        fila_excel = PRIMERA_FILA + i
        for campo, col in COLUMNAS.items():
            hoja[f"{col}{fila_excel}"] = datos[campo]
    if renombrar_hoja:
        hoja.title = renombrar_hoja
    libro.save(destino)
    return destino, len(filas)


def main():
    if not os.path.exists(PLANTILLA):
        print(f"ERROR: no está la plantilla real en {PLANTILLA}")
        return 1
    os.makedirs(DESTINO, exist_ok=True)

    # Un adjunto que NO es Excel, para el caso de ADJUNTO_ES_EXCEL.
    ruta_txt = os.path.join(DESTINO, "A01-no-es-excel.txt")
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write("Este archivo no es un Excel. Sirve para el caso ADJUNTO_ES_EXCEL.\n")

    total = 0
    for nombre, filas, renombrar in casos():
        ruta, n = escribir(nombre, filas, renombrar)
        print(f"  {nombre:38} {n:>3} fila(s)")
        total += 1
    print(f"\n{total} Excel + 1 adjunto que no es Excel, en {DESTINO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
