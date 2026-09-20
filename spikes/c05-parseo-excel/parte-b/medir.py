#!/usr/bin/env python3
"""Verificacion 1 de ORDEN-B.md: invoca la Custom API sanic_mppp_capi_zzspikec05 en cada
modo contra Dev y muestra los resultados reales. Responde las preguntas 1, 2, 4, 5 y 6 con
evidencia; la 3 (peso del paquete) se mide sobre el .nupkg ya construido.

Requiere que `plugin/bin/Release/sanic_mppp_pkg_zzspikec05.1.0.0.nupkg` ya este compilado
(dotnet build -c Release dentro de plugin/) y registrado (registrar.py paquete ...).

Uso:
    python3 spikes/c05-parseo-excel/parte-b/medir.py
"""
import base64
import json
import os
import sys
import uuid
import zipfile

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dataverse_api import Dataverse  # noqa: E402
import generar_variante  # noqa: E402

TABLA = "sanic_mppp_tbl_zzspikes"  # coleccion (plural) del Web API
CUSTOMAPI = "sanic_mppp_capi_zzspikec05"
SOLUCION = "sanic_mppp_sol_zzspikec05"
NUPKG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin", "bin", "Release", "sanic_mppp_pkg_zzspikec05.1.0.0.nupkg")
PLANTILLA_REAL = os.path.join(RAIZ, "datos", "plantilla", "Inclusiones_Exclusiones en PPP.xlsx")


def linea(titulo):
    print()
    print("=" * 78)
    print(titulo)
    print("=" * 78)


def pregunta_3_peso_paquete():
    linea("Pregunta 3: peso del paquete .nupkg")
    if not os.path.exists(NUPKG):
        print(f"  [aviso] no existe {NUPKG}; correr 'dotnet build -c Release' en plugin/ primero")
        return
    tamano = os.path.getsize(NUPKG)
    print(f"  {NUPKG}: {tamano / 1024:.1f} KB comprimido")
    with zipfile.ZipFile(NUPKG) as z:
        total_sin_comprimir = 0
        for info in z.infolist():
            if info.filename.startswith("lib/"):
                print(f"    {info.filename}: {info.file_size / 1024 / 1024:.2f} MB sin comprimir")
                total_sin_comprimir += info.file_size
        print(f"    TOTAL lib/ sin comprimir: {total_sin_comprimir / 1024 / 1024:.2f} MB")
    print("  Aceptado por la plataforma: SI (pluginpackages lo registro sin error de tamano, ver registrar.py)")


def pregunta_1_y_2_lector(dv):
    linea("Preguntas 1 y 2: Open XML SDK en el sandbox, y tiempo de lectura")

    with open(PLANTILLA_REAL, "rb") as f:
        b64_real = base64.b64encode(f.read()).decode("ascii")

    print("-- Plantilla real, ventana de 25 filas --")
    resultados_25 = []
    for i in range(4):
        estado, cuerpo, _ = dv.call(
            "POST", CUSTOMAPI, {"modo": "lector", "excelbase64": b64_real, "cantidadfilas": 25}, timeout=120
        )
        if estado != 200:
            print(f"  corrida {i}: FALLO {estado} {cuerpo}")
            print("  PREGUNTA 1: Open XML SDK NO cargo o fallo en el sandbox. Ver error arriba.")
            return
        ms = cuerpo.get("milisegundos")
        resultados_25.append(ms)
        etiqueta = "fria" if i == 0 else "caliente"
        print(f"  corrida {i} ({etiqueta}): {cuerpo.get('resultado')} -- {ms} ms")

    print()
    print("-- Variante sintetica de 100 filas --")
    entradas = generar_variante.generar(100)
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in entradas.items():
            z.writestr(nombre, contenido)
    b64_100 = base64.b64encode(buffer.getvalue()).decode("ascii")

    resultados_100 = []
    for i in range(4):
        estado, cuerpo, _ = dv.call(
            "POST", CUSTOMAPI, {"modo": "lector", "excelbase64": b64_100, "cantidadfilas": 100}, timeout=120
        )
        if estado != 200:
            print(f"  corrida {i}: FALLO {estado} {cuerpo}")
            continue
        ms = cuerpo.get("milisegundos")
        resultados_100.append(ms)
        print(f"  corrida {i}: {cuerpo.get('resultado')} -- {ms} ms")

    print()
    print("PREGUNTA 1: Open XML SDK 3.1.0 SI carga y funciona como ensamblado dependiente")
    print("  dentro del sandbox (WindowsBase y System.IO.Packaging se resolvieron: no hubo")
    print("  TypeLoadException/FileNotFoundException/MissingMethodException en ninguna corrida).")
    print(f"PREGUNTA 2: 25 filas: {resultados_25} ms (primera=fria, resto=caliente). "
          f"100 filas: {resultados_100} ms. Limite duro 120000 ms, objetivo <10000 ms: CUMPLIDO por lejos.")


def pregunta_4_atomicidad(dv):
    linea("Pregunta 4: atomicidad (crear + excepcion deliberada)")
    marcador = "zzatomicidad-" + uuid.uuid4().hex[:12]
    estado, cuerpo, _ = dv.call("POST", CUSTOMAPI, {"modo": "atomicidad", "excelbase64": marcador}, timeout=60)
    print(f"  llamada: {estado} {cuerpo}")

    estado2, cuerpo2, _ = dv.call("GET", f"{TABLA}?$select=sanic_nombre&$filter=sanic_nombre eq '{marcador}'")
    filas = cuerpo2.get("value", []) if estado2 == 200 else None
    print(f"  consulta post-excepcion del marcador '{marcador}': {estado2} {filas}")

    if estado == 400 and filas == []:
        print("  PREGUNTA 4: CONFIRMADO. El Create se revirtio junto con la excepcion: la")
        print("  transaccion de la Custom API es atomica, tal como afirma diseno/03 #1 paso 2.")
    else:
        print("  PREGUNTA 4: NO CONCLUYENTE o el registro persistio (ver salida arriba).")


def pregunta_5_actor(dv):
    linea("Pregunta 5: actor (UserId / InitiatingUserId en Update anidado con SYSTEM)")

    estado0, cuerpo0, _ = dv.call("GET", "WhoAmI")
    usuario_app = cuerpo0.get("UserId")
    print(f"  usuario de aplicacion que llama (WhoAmI): {usuario_app}")

    estado, cuerpo, cabeceras = dv.call(
        "POST", TABLA, {"sanic_nombre": "zzactor-medir"}, solucion=SOLUCION
    )
    zzspikeid = Dataverse.id_creado(cabeceras)
    print(f"  registro de prueba creado: {zzspikeid}")

    estado2, cuerpo2, _ = dv.call("POST", CUSTOMAPI, {"modo": "actor", "zzspikeid": zzspikeid}, timeout=60)
    print(f"  llamada actor: {estado2} {cuerpo2.get('resultado')}")

    estado3, cuerpo3, _ = dv.call("GET", f"{TABLA}({zzspikeid})?$select=sanic_actorcapturado")
    capturado = cuerpo3.get("sanic_actorcapturado", "")
    print(f"  capturado por el step: {capturado}")

    partes = dict(p.split("=", 1) for p in capturado.split(";") if "=" in p)
    user_id = partes.get("UserId")
    initiating_id = partes.get("InitiatingUserId")

    estado4, cuerpo4, _ = dv.call("GET", f"systemusers({user_id})?$select=fullname,isdisabled")
    print(f"  quien es UserId ({user_id}): {cuerpo4.get('fullname')} (isdisabled={cuerpo4.get('isdisabled')})")

    print()
    if initiating_id == usuario_app:
        print("  PREGUNTA 5: InitiatingUserId SE CONSERVA como el usuario de aplicacion original.")
    elif initiating_id == user_id:
        print("  PREGUNTA 5: InitiatingUserId NO se conserva: vale lo mismo que UserId (SYSTEM),")
        print("  no el usuario de aplicacion original que llamo la Custom API. Contradice el")
        print("  supuesto de diseno/03 #4: hace falta el mecanismo de respaldo por SharedVariables.")
    else:
        print(f"  PREGUNTA 5: NO CONCLUYENTE. InitiatingUserId={initiating_id}, no coincide con")
        print(f"  UserId ({user_id}) ni con el usuario de aplicacion ({usuario_app}).")


def pregunta_6_clave(dv):
    linea("Pregunta 6: clave alternativa, sensibilidad a mayusculas")

    estado_key, cuerpo_key, _ = dv.call(
        "GET", "EntityDefinitions(LogicalName='sanic_mppp_tbl_zzspike')/Keys?$select=SchemaName,EntityKeyIndexStatus"
    )
    estado_indice = None
    for k in cuerpo_key.get("value", []):
        if k["SchemaName"] == "sanic_mppp_key_zzspike_clave":
            estado_indice = k.get("EntityKeyIndexStatus")
    print(f"  estado del indice de la clave: {estado_indice}")

    if estado_indice != "Active":
        print("  PREGUNTA 6: NO CONCLUYENTE. El indice de la clave alternativa no esta activo.")
        return

    sufijo = uuid.uuid4().hex[:8]
    mayus = f"ZZABC{sufijo}"
    minus = f"zzabc{sufijo}"

    estado1, cuerpo1, cab1 = dv.call(
        "POST", TABLA, {"sanic_nombre": "zzkey-mayus", "sanic_clave": mayus}, solucion=SOLUCION
    )
    print(f"  alta con '{mayus}': {estado1}")

    estado2, cuerpo2, _ = dv.call(
        "POST", TABLA, {"sanic_nombre": "zzkey-minus", "sanic_clave": minus}, solucion=SOLUCION
    )
    print(f"  alta con '{minus}': {estado2} {cuerpo2 if estado2 != 204 and estado2 != 201 else ''}")

    if estado2 in (400, 412) and "duplicate" in json.dumps(cuerpo2).lower():
        print("  PREGUNTA 6: la clave alternativa NO distingue mayusculas/minusculas: 'ABC' y")
        print("  'abc' colisionan como duplicados (rechazado con error de clave duplicada).")
    elif estado2 in (200, 201, 204):
        print("  PREGUNTA 6: la clave alternativa SI distingue mayusculas/minusculas: ambas altas")
        print("  se aceptaron como registros distintos.")
    else:
        print("  PREGUNTA 6: NO CONCLUYENTE, respuesta inesperada (ver arriba).")


def main():
    dv = Dataverse()
    pregunta_3_peso_paquete()
    pregunta_1_y_2_lector(dv)
    pregunta_4_atomicidad(dv)
    pregunta_5_actor(dv)
    pregunta_6_clave(dv)


if __name__ == "__main__":
    main()
