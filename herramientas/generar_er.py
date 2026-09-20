#!/usr/bin/env python3
"""Genera diseno/02-modelo-datos.svg a partir del modelo declarado acá abajo.

Uso:  python3 herramientas/generar_er.py
El modelo de este archivo tiene que acompañar a 02-diccionario-datos.md: si cambia
el diccionario, se cambia acá y se regenera. Sin dependencias fuera de la stdlib.
"""
import os
from xml.sax.saxutils import escape

W_BOX, H_HEAD, H_ROW, PAD = 360, 44, 18, 8
CAT, UH, F3 = "#2f5d8a", "#8a4b2f", "#6b6b6b"

# (columna, tipo, marca)  marca: PK nombre · AK clave alternativa · FK lookup · "" normal
TABLAS = {
    "autorizado": dict(x=40, y=90, color=CAT, titulo="Autorizado", logico="sanic_mppp_tbl_autorizado", filas=[
        ("sanic_nombre  (= correo)", "T(320)", "AK"),
        ("sanic_clienteid", "→ Cliente", "AK FK"),
        ("sanic_documentofirmado", "Archivo", ""),
        ("sanic_fechadocumento", "Fecha", ""),
    ]),
    "cliente": dict(x=440, y=90, color=CAT, titulo="Cliente", logico="sanic_mppp_tbl_cliente", filas=[
        ("sanic_nombre", "T(200)", "PK"),
        ("sanic_cifbac", "T(9) · dígitos, relleno con 0", "AK"),
        ("sanic_cifcom", "T(12) · 9 alfanum. + 3 dígitos", "AK"),
        ("ownerid  (= ejecutivo)", "→ systemuser", "FK"),
    ]),
    "plan": dict(x=840, y=90, color=CAT, titulo="Plan", logico="sanic_mppp_tbl_plan", filas=[
        ("sanic_nombre", "T(100)", "PK"),
        ("sanic_codigo", "T(4) · relleno con 0", "AK"),
        ("sanic_tipoformato", "Choice 06·10·11", ""),
        ("sanic_moneda", "Choice COR·USD", ""),
        ("sanic_clienteid", "→ Cliente", "FK"),
    ]),
    "regla": dict(x=1240, y=90, color=CAT, titulo="Regla", logico="sanic_mppp_tbl_regla", filas=[
        ("sanic_nombre", "T(200)", "PK"),
        ("sanic_codigo", "T(50)", "AK"),
        ("sanic_nivel", "Solicitud · Registro", ""),
        ("sanic_orden", "Entero", ""),
        ("sanic_dependede", "códigos de reglas", ""),
        ("sanic_efecto", "Choice · 3 efectos", ""),
        ("sanic_mensajecliente", "Multilínea", ""),
    ]),
    "autorizacionplan": dict(x=440, y=330, color=CAT, titulo="AutorizacionPlan", logico="sanic_mppp_tbl_autorizacionplan", filas=[
        ("sanic_nombre", "T(400)", "PK"),
        ("sanic_autorizadoid", "→ Autorizado", "AK FK"),
        ("sanic_planid", "→ Plan", "AK FK"),
    ]),
    "parametro": dict(x=1240, y=330, color=CAT, titulo="Parametro", logico="sanic_mppp_tbl_parametro", filas=[
        ("sanic_nombre  (= código)", "T(100)", "AK"),
        ("sanic_version", "Entero", "AK"),
        ("sanic_tipo", "Texto·Número·JSON", ""),
        ("sanic_valor", "Multilínea", ""),
        ("sanic_descripcion", "Multilínea", ""),
    ]),
    "bitacora": dict(x=40, y=600, color=UH, titulo="Bitacora", logico="sanic_mppp_tbl_bitacora", filas=[
        ("sanic_nombre", "T(200)", "PK"),
        ("sanic_solicitudid", "→ Solicitud", "FK"),
        ("sanic_fechaevento", "Fecha y hora", ""),
        ("sanic_evento", "Choice", ""),
        ("sanic_origen", "Choice", ""),
        ("sanic_numerofila", "Entero · 0 = solicitud", ""),
        ("sanic_actortexto", "T(200)", ""),
        ("sanic_detalle", "Multilínea", ""),
    ]),
    "solicitud": dict(x=440, y=600, color=UH, titulo="Solicitud", logico="sanic_mppp_tbl_solicitud", filas=[
        ("sanic_nombre", "MPPP-{SEQNUM:8}", "PK"),
        ("sanic_messageid", "T(450)", "AK"),
        ("sanic_remitente", "T(320)", ""),
        ("sanic_asunto", "T(400)", ""),
        ("sanic_fecharecibido", "Fecha y hora", ""),
        ("sanic_fechaingresada", "Fecha y hora", ""),
        ("sanic_estadoprocesamiento", "Choice", ""),
        ("sanic_fechavalidada", "Fecha y hora", ""),
        ("sanic_fechaacuseiniciado", "Fecha y hora", ""),
        ("sanic_fechaacuseenviado", "Fecha y hora", ""),
        ("sanic_acusecontenido", "Multilínea", ""),
        ("sanic_fechaprocesada", "Fecha y hora", ""),
        ("sanic_fecharespuestafinaliniciada", "Fecha y hora", ""),
        ("sanic_fecharespuestafinalenviada", "Fecha y hora", ""),
        ("sanic_respuestafinalcontenido", "Multilínea", ""),
        ("sanic_fechacerrada", "Fecha y hora", ""),
        ("sanic_correocrudo", "Archivo", ""),
        ("sanic_exceloriginal", "Archivo", ""),
        ("sanic_filas…", "totales·válidas·rechazadas", ""),
        ("sanic_versionparametros", "T(200)", ""),
        ("sanic_reintentosvalidacion", "Entero", ""),
        ("sanic_requiererevision", "Sí/No + motivo", ""),
    ]),
    "fila": dict(x=840, y=600, color=UH, titulo="Fila", logico="sanic_mppp_tbl_fila", filas=[
        ("sanic_nombre", "T(120)", "PK"),
        ("sanic_solicitudid", "→ Solicitud", "AK FK"),
        ("sanic_numerofila", "Entero", "AK"),
        ("sanic_gestion", "Choice · vacío si inválido", ""),
        ("sanic_clasificacion", "Choice · vacío si inválido", ""),
        ("sanic_numeroplan", "T(4) normalizado", ""),
        ("sanic_planid", "→ Plan · puede ir vacío", "FK"),
        ("sanic_nombrebeneficiario", "Texto", ""),
        ("sanic_tipoidentificacion", "Choice · vacío si inválido", ""),
        ("sanic_numeroidentificacion", "PROTEGIDA", ""),
        ("sanic_referencia", "la que rige · f.11 construida", ""),
        ("sanic_referenciarecibida", "tal cual vino en el Excel", ""),
        ("sanic_numerocuenta", "PROTEGIDA", ""),
        ("sanic_moneda", "Choice · vacío si inválido", ""),
        ("sanic_banco", "Choice · vacío si inválido", ""),
        ("sanic_estado", "Choice", ""),
        ("sanic_mensaje", "historial de reglas de la fila", ""),
        ("sanic_fechavalidada", "Fecha y hora", ""),
        ("sanic_digitadapor", "→ systemuser + fecha", "FK"),
        ("sanic_aprobadapor", "→ systemuser + fecha", "FK"),
    ]),
    "resultadoregla": dict(x=1240, y=600, color=UH, titulo="ResultadoRegla", logico="sanic_mppp_tbl_resultadoregla", filas=[
        ("sanic_nombre", "T(200)", "PK"),
        ("sanic_solicitudid", "→ Solicitud", "AK FK"),
        ("sanic_reglacodigo", "T(50)", "AK"),
        ("sanic_reglaid", "→ Regla", "FK"),
        ("sanic_resultado", "Cumplida·No cumplida·Omitida", ""),
        ("sanic_razon", "Multilínea", ""),
        ("sanic_efectoaplicado", "Choice", ""),
        ("sanic_fechaevaluacion", "Fecha y hora", ""),
        ("sanic_orden", "Entero", ""),
    ]),
    "corrida": dict(x=40, y=830, color=F3, titulo="CorridaHistorico  · fase 3", logico="sanic_mppp_tbl_corridahistorico", punteada=True, filas=[
        ("sanic_corridaid", "T(60)", "AK"),
        ("tipo · inicio · fin · contadores", "", ""),
        ("sin lookups a la unidad histórica", "", ""),
    ]),
}

for t in TABLAS.values():
    t["w"] = W_BOX
    t["h"] = H_HEAD + len(t["filas"]) * H_ROW + PAD

def b(n):
    return TABLAS[n]

Y_BAJO = max(t["y"] + t["h"] for t in TABLAS.values()) + 28
A = 50  # altura del anclaje lateral, medida desde el borde superior de la caja

# (puntos, parental, etiqueta)  —  el primer punto es el lado "1", el último el lado "N"
REL = [
    ([(b("cliente")["x"] + W_BOX, b("cliente")["y"] + A), (b("plan")["x"], b("plan")["y"] + A)], False, ""),
    ([(b("cliente")["x"], b("cliente")["y"] + A), (b("autorizado")["x"] + W_BOX, b("autorizado")["y"] + A)], False, ""),
    ([(b("autorizado")["x"] + 150, b("autorizado")["y"] + b("autorizado")["h"]),
      (b("autorizado")["x"] + 150, b("autorizacionplan")["y"] + A),
      (b("autorizacionplan")["x"], b("autorizacionplan")["y"] + A)], False, ""),
    ([(b("plan")["x"] + 60, b("plan")["y"] + b("plan")["h"]),
      (b("plan")["x"] + 60, b("autorizacionplan")["y"] + A),
      (b("autorizacionplan")["x"] + W_BOX, b("autorizacionplan")["y"] + A)], False, ""),
    ([(b("plan")["x"] + 260, b("plan")["y"] + b("plan")["h"]), (b("plan")["x"] + 260, b("fila")["y"])], False, ""),
    ([(b("solicitud")["x"] + W_BOX, b("solicitud")["y"] + A), (b("fila")["x"], b("fila")["y"] + A)], True, ""),
    ([(b("solicitud")["x"], b("solicitud")["y"] + A), (b("bitacora")["x"] + W_BOX, b("bitacora")["y"] + A)], True, ""),
    ([(b("solicitud")["x"] + 155, b("solicitud")["y"] + b("solicitud")["h"]),
      (b("solicitud")["x"] + 155, Y_BAJO),
      (b("resultadoregla")["x"] + 155, Y_BAJO),
      (b("resultadoregla")["x"] + 155, b("resultadoregla")["y"] + b("resultadoregla")["h"])], True, ""),
    ([(b("regla")["x"] + W_BOX, b("regla")["y"] + A),
      (b("regla")["x"] + W_BOX + 22, b("regla")["y"] + A),
      (b("regla")["x"] + W_BOX + 22, b("resultadoregla")["y"] + A),
      (b("resultadoregla")["x"] + W_BOX, b("resultadoregla")["y"] + A)], False, ""),
]

ANCHO = 1240 + W_BOX + 60
ALTO = Y_BAJO + 120
o = []
o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" width="{ANCHO}" height="{ALTO}" '
         f'font-family="Segoe UI, Helvetica, Arial, sans-serif" role="img" aria-labelledby="t d">')
o.append('<title id="t">Modelo de datos de Mantenimiento PPP</title>')
o.append('<desc id="d">Diagrama entidad-relación: seis catálogos, cuatro tablas de la unidad histórica que cuelgan '
         'de Solicitud con relación parental, y una tabla de corridas de histórico de la fase 3.</desc>')
o.append(f'<rect width="{ANCHO}" height="{ALTO}" fill="#ffffff"/>')
o.append('<text x="40" y="38" font-size="21" font-weight="700" fill="#1c1c1c">Modelo de datos · SOL - MPPP - Mantenimiento PPP</text>')
o.append('<text x="40" y="60" font-size="12" fill="#555">Revisado con el aprobador el 2026-09-18 · todas las tablas user-owned · estado nativo Activo/Inactivo, nadie borra · '
         'fuente: diseno/02-diccionario-datos.md</text>')

# bandas
o.append(f'<text x="40" y="82" font-size="12" font-weight="700" fill="{CAT}">CATÁLOGOS — nunca se purgan, se desactivan</text>')
o.append(f'<line x1="40" y1="{b("solicitud")["y"] - 38}" x2="{ANCHO - 40}" y2="{b("solicitud")["y"] - 38}" stroke="#d0d0d0" stroke-dasharray="3 5"/>')
o.append(f'<text x="40" y="{b("solicitud")["y"] - 12}" font-size="12" font-weight="700" fill="{UH}">'
         'UNIDAD HISTÓRICA — todo cuelga de Solicitud; se archiva y se purga entera</text>')

# relaciones (debajo de las cajas)
for pts, parental, _ in REL:
    d = "M " + " L ".join(f"{x},{y}" for x, y in pts)
    estilo = 'stroke="#8a4b2f" stroke-width="2.6"' if parental else 'stroke="#44607a" stroke-width="1.6" stroke-dasharray="6 4"'
    o.append(f'<path d="{d}" fill="none" {estilo} stroke-linejoin="round"/>')
    (x1, y1), (x2, y2) = pts[0], pts[1]
    (xn, yn), (xm, ym) = pts[-1], pts[-2]
    def etiqueta(x, y, xo, yo, txt):
        dx = 9 if xo > x else (-9 if xo < x else 9)
        dy = 14 if yo > y else (-6 if yo < y else -6)
        ancla = "start" if dx > 0 else "end"
        o.append(f'<text x="{x + dx}" y="{y + dy}" font-size="12" font-weight="700" fill="#222" text-anchor="{ancla}">{txt}</text>')
    etiqueta(x1, y1, x2, y2, "1")
    etiqueta(xn, yn, xm, ym, "N")

# cajas
for t in TABLAS.values():
    x, y, w, h, c = t["x"], t["y"], t["w"], t["h"], t["color"]
    trazo = 'stroke-dasharray="7 4"' if t.get("punteada") else ""
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#fbfbfb" stroke="{c}" stroke-width="1.6" {trazo}/>')
    o.append(f'<path d="M {x},{y + H_HEAD} L {x},{y + 6} Q {x},{y} {x + 6},{y} L {x + w - 6},{y} Q {x + w},{y} {x + w},{y + 6} L {x + w},{y + H_HEAD} Z" fill="{c}"/>')
    o.append(f'<text x="{x + 12}" y="{y + 19}" font-size="14" font-weight="700" fill="#ffffff">{escape(t["titulo"])}</text>')
    o.append(f'<text x="{x + 12}" y="{y + 35}" font-size="10.5" fill="#e6edf3" font-family="Consolas, Menlo, monospace">{escape(t["logico"])}</text>')
    for i, (col, tipo, marca) in enumerate(t["filas"]):
        yy = y + H_HEAD + i * H_ROW + 14
        if i % 2 == 1:
            o.append(f'<rect x="{x + 1}" y="{yy - 13}" width="{w - 2}" height="{H_ROW}" fill="#f0f2f4"/>')
        peso = "700" if "AK" in marca or "PK" in marca else "400"
        color = "#9a5b00" if col.rstrip().endswith("?") else "#1c1c1c"
        o.append(f'<text x="{x + 46}" y="{yy}" font-size="11" font-weight="{peso}" fill="{color}" font-family="Consolas, Menlo, monospace">{escape(col)}</text>')
        o.append(f'<text x="{x + w - 8}" y="{yy}" font-size="10" fill="#666" text-anchor="end">{escape(tipo)}</text>')
        xx = x + 6
        for m in marca.split():
            fondo = {"PK": "#555", "AK": "#1a7f4b", "FK": "#44607a"}[m]
            o.append(f'<rect x="{xx}" y="{yy - 10}" width="18" height="12" rx="2" fill="{fondo}"/>')
            o.append(f'<text x="{xx + 9}" y="{yy - 1}" font-size="8" font-weight="700" fill="#fff" text-anchor="middle">{m}</text>')
            xx += 20

# leyenda
ly = ALTO - 70
lx = 440
o.append(f'<rect x="{lx}" y="{ly}" width="{ANCHO - lx - 40}" height="52" rx="6" fill="#f7f7f7" stroke="#d0d0d0"/>')
o.append(f'<path d="M {lx + 16},{ly + 18} L {lx + 70},{ly + 18}" stroke="#8a4b2f" stroke-width="2.6"/>')
o.append(f'<text x="{lx + 80}" y="{ly + 22}" font-size="11.5" fill="#222">Relación parental: borrar la Solicitud borra lo suyo en cascada (solo el job nativo de purga)</text>')
o.append(f'<path d="M {lx + 16},{ly + 38} L {lx + 70},{ly + 38}" stroke="#44607a" stroke-width="1.6" stroke-dasharray="6 4"/>')
o.append(f'<text x="{lx + 80}" y="{ly + 42}" font-size="11.5" fill="#222">Relación referencial con borrado restringido: un catálogo en uso no se borra</text>')
for i, (m, fondo, txt) in enumerate([("PK", "#555", "columna primaria"), ("AK", "#1a7f4b", "parte de una clave alternativa"), ("FK", "#44607a", "lookup")]):
    xx = lx + 700  # columna fija, apiladas
    yy = ly + 14 + i * 14
    o.append(f'<rect x="{xx}" y="{yy - 9}" width="18" height="12" rx="2" fill="{fondo}"/>')
    o.append(f'<text x="{xx + 9}" y="{yy}" font-size="8" font-weight="700" fill="#fff" text-anchor="middle">{m}</text>')
    o.append(f'<text x="{xx + 26}" y="{yy + 1}" font-size="11" fill="#222">{txt}</text>')

o.append("</svg>")
destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "diseno", "02-modelo-datos.svg")
with open(destino, "w", encoding="utf-8") as f:
    f.write("\n".join(o))
print("escrito", os.path.normpath(destino), f"{ANCHO}x{ALTO}")
