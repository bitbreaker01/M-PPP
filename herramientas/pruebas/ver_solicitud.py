#!/usr/bin/env python3
"""Muestra, de una sola vez, TODO lo que pasó con una Solicitud.

    python3 herramientas/pruebas/ver_solicitud.py MPPP-00001234
    python3 herramientas/pruebas/ver_solicitud.py --ultima
    python3 herramientas/pruebas/ver_solicitud.py --ultimas 5
    python3 herramientas/pruebas/ver_solicitud.py --parametros

Existe para que verificar un caso de prueba sea leer una pantalla y no abrir
seis pestañas: estado y contadores, **cada regla con su resultado y su razón**,
las filas con su estado y su mensaje, y la Bitácora en orden.

Es de solo lectura: no escribe nada en el entorno.
"""
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(_AQUI))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))

ESTADO_SOLICITUD = {159460001: "Ingresada", 159460002: "No reconocida", 159460003: "Descartada",
                    159460004: "Rechazada", 159460005: "En proceso", 159460006: "Procesada",
                    159460007: "Cerrada", 159460008: "No es correo nuevo", 159460009: "Vencida"}
ESTADO_FILA = {159460001: "Rechazada en validacion", 159460002: "Sin autorizacion",
               159460003: "Validada", 159460004: "Digitada", 159460005: "Aprobada",
               159460006: "Rechazada en AS400", 159460007: "Anulada"}
EVENTO = {159460001: "Ingresada", 159460002: "Validacion terminada", 159460003: "Acuse iniciado",
          159460004: "Acuse enviado", 159460005: "Fila digitada", 159460006: "Fila aprobada",
          159460007: "Fila devuelta", 159460008: "Fila rechazada en AS400", 159460018: "Fila anulada",
          159460009: "Procesada", 159460010: "Respuesta final iniciada",
          159460011: "Respuesta final enviada", 159460012: "Cerrada",
          159460013: "No reconocida atendida", 159460014: "Descartada", 159460015: "Reintento",
          159460016: "Requiere revision", 159460017: "Error", 159460019: "Correo clasificado",
          159460020: "Vencida"}
ORIGEN = {159460001: "MPPP-REC", 159460002: "MPPP-ING", 159460003: "MPPP-COM", 159460004: "MPPP-ENV",
          159460005: "MPPP-VIG", 159460006: "Custom API", 159460007: "Plugin", 159460008: "App"}
RESULTADO = {159460001: "Cumplida", 159460002: "NO CUMPLIDA", 159460003: "Omitida"}
EFECTO = {159460001: "Rechaza", 159460002: "Envia a revision", 159460003: "Advierte"}


def _corto(texto, n=100):
    if texto is None:
        return ""
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= n else texto[:n - 1] + "…"


def parametros(dv):
    est, r, _ = dv.call("GET", "sanic_mppp_tbl_parametros?$select=sanic_nombre,sanic_valor,sanic_version"
                               "&$filter=statecode eq 0&$orderby=sanic_nombre")
    filas = r.get("value", [])
    print(f"=== parámetros activos: {len(filas)} ===")
    for p in filas:
        print(f"  {p['sanic_nombre']:34} {_corto(p.get('sanic_valor'), 90)}")


def _resultados(dv, id_sol):
    ruta = ("sanic_mppp_tbl_resultadoreglas?$select=sanic_reglacodigo,sanic_resultado,sanic_razon,"
            "sanic_efectoaplicado,sanic_orden"
            f"&$filter=_sanic_solicitudid_value eq {id_sol}&$orderby=sanic_orden")
    est, r, _ = dv.call("GET", ruta)
    return r.get("value", [])


def mostrar(dv, numero=None, id_sol=None):
    if id_sol is None:
        est, r, _ = dv.call("GET", "sanic_mppp_tbl_solicituds?$filter=sanic_nombre eq '" + numero + "'")
        if not r.get("value"):
            print(f"No existe ninguna Solicitud {numero!r}")
            return 1
        s = r["value"][0]
    else:
        est, s, _ = dv.call("GET", f"sanic_mppp_tbl_solicituds({id_sol})")
    id_sol = s["sanic_mppp_tbl_solicitudid"]

    print("=" * 78)
    print(f"  {s.get('sanic_nombre')}   estado: {ESTADO_SOLICITUD.get(s.get('sanic_estadoprocesamiento'), s.get('sanic_estadoprocesamiento'))}")
    print("=" * 78)
    print(f"  remitente          {s.get('sanic_remitente')}")
    print(f"  asunto             {_corto(s.get('sanic_asunto'), 70)}")
    print(f"  recibido           {s.get('sanic_fecharecibido')}")
    print(f"  adjuntos / excel   {s.get('sanic_cantidadadjuntos')} / {s.get('sanic_cantidadexcel')}")
    print(f"  filas t/v/r        {s.get('sanic_filastotales')} / {s.get('sanic_filasvalidas')} / {s.get('sanic_filasrechazadas')}")
    print(f"  requiere revision  {s.get('sanic_requiererevision')}   motivo: {_corto(s.get('sanic_motivorevision'), 60)}")
    print(f"  motivo clasific.   {_corto(s.get('sanic_motivoclasificacion'), 70)}")
    print(f"  version parametros {s.get('sanic_versionparametros')}")
    print(f"  reintentos         {s.get('sanic_reintentosvalidacion')}")
    print(f"  outlook message id {'sí' if s.get('sanic_outlookmessageid') else 'NO'}")
    print(f"  acuse   iniciado/enviado   {s.get('sanic_fechaacuseiniciado')} / {s.get('sanic_fechaacuseenviado')}")
    print(f"  final   iniciada/enviada   {s.get('sanic_fecharespuestafinaliniciada')} / {s.get('sanic_fecharespuestafinalenviada')}")
    print(f"  archivos           correo: {'sí' if s.get('sanic_correocrudo_name') else 'NO'}"
          f"   excel: {'sí' if s.get('sanic_exceloriginal_name') else 'NO'}")

    res = _resultados(dv, id_sol)
    print(f"\n--- reglas evaluadas: {len(res)} ---")
    for x in res:
        cod = x.get("sanic_reglacodigo")
        resu = RESULTADO.get(x.get("sanic_resultado"), x.get("sanic_resultado"))
        efecto = EFECTO.get(x.get("sanic_efectoaplicado"), "")
        print(f"  {str(x.get('sanic_orden')):>3} {str(cod):26} {str(resu):12} {efecto:18} {_corto(x.get('sanic_razon'), 44)}")

    est, r, _ = dv.call("GET", "sanic_mppp_tbl_filas?$select=sanic_nombre,sanic_numerofila,sanic_estado,"
                               "sanic_mensaje,sanic_referencia,sanic_referenciarecibida,sanic_numerocuenta,"
                               "sanic_banco,sanic_moneda,sanic_gestion,sanic_clasificacion"
                               f"&$filter=_sanic_solicitudid_value eq {id_sol}&$orderby=sanic_numerofila")
    filas = r.get("value", [])
    print(f"\n--- filas: {len(filas)} ---")
    for f in filas:
        print(f"  #{str(f.get('sanic_numerofila')):>3} {ESTADO_FILA.get(f.get('sanic_estado'), f.get('sanic_estado')):24}"
              f" ref={str(f.get('sanic_referencia')):22} recibida={str(f.get('sanic_referenciarecibida'))}")
        if f.get("sanic_mensaje"):
            print(f"        {_corto(f.get('sanic_mensaje'), 90)}")

    est, r, _ = dv.call("GET", "sanic_mppp_tbl_bitacoras?$select=sanic_evento,sanic_origen,sanic_fechaevento,"
                               "sanic_actortexto,sanic_detalle,sanic_numerofila"
                               f"&$filter=_sanic_solicitudid_value eq {id_sol}&$orderby=sanic_fechaevento")
    bit = r.get("value", [])
    print(f"\n--- bitácora: {len(bit)} ---")
    for b in bit:
        print(f"  {b.get('sanic_fechaevento')}  {EVENTO.get(b.get('sanic_evento'), b.get('sanic_evento')):26}"
              f" {ORIGEN.get(b.get('sanic_origen'), b.get('sanic_origen')):12} {_corto(b.get('sanic_detalle'), 44)}")

    if s.get("sanic_acusecontenido"):
        print(f"\n--- acuse ({len(s['sanic_acusecontenido'])} caracteres) ---")
        print("  " + _corto(s["sanic_acusecontenido"], 400))
    if s.get("sanic_respuestafinalcontenido"):
        print(f"\n--- respuesta final ({len(s['sanic_respuestafinalcontenido'])} caracteres) ---")
        print("  " + _corto(s["sanic_respuestafinalcontenido"], 400))
    return 0


def main():
    argv = sys.argv[1:]
    from dataverse_api import Dataverse

    dv = Dataverse()
    if "--parametros" in argv:
        parametros(dv)
        return 0
    if "--ultima" in argv or "--ultimas" in argv:
        n = 1
        if "--ultimas" in argv:
            i = argv.index("--ultimas")
            n = int(argv[i + 1]) if i + 1 < len(argv) and argv[i + 1].isdigit() else 3
        est, r, _ = dv.call("GET", "sanic_mppp_tbl_solicituds?$select=sanic_mppp_tbl_solicitudid,sanic_nombre"
                                   f"&$orderby=createdon desc&$top={n}")
        filas = r.get("value", [])
        if not filas:
            print("No hay ninguna Solicitud en el entorno.")
            return 1
        for f in filas:
            mostrar(dv, id_sol=f["sanic_mppp_tbl_solicitudid"])
            print()
        return 0
    numeros = [a for a in argv if not a.startswith("--") and not a.isdigit()]
    if not numeros:
        print(__doc__)
        return 1
    for n in numeros:
        mostrar(dv, numero=n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
