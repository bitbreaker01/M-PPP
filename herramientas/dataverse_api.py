#!/usr/bin/env python3
"""Cliente mínimo del Web API de Dataverse para el puesto de trabajo. Sin dependencias.

Lee las credenciales de `local/pp_secrets.env` (no versionado) y obtiene el token por
credenciales de cliente. **Nunca imprime el secreto ni el token.**

Como librería:
    from dataverse_api import Dataverse
    dv = Dataverse()
    estado, cuerpo, cabeceras = dv.call("GET", "WhoAmI")
    estado, cuerpo, _ = dv.call("POST", "customapis", {...}, solucion="sanic_mppp_sol_mantenimientoppp")

Como comando:
    python3 herramientas/dataverse_api.py GET "solutions?$select=uniquename&$top=3"
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ARCHIVO_ENV = os.path.join(RAIZ, "local", "pp_secrets.env")


class Dataverse:
    def __init__(self, archivo_env=ARCHIVO_ENV, version="v9.2"):
        cfg = {}
        with open(archivo_env, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    k, v = linea.split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
        self.org = cfg["DATAVERSE_URL"].rstrip("/")
        self.api = f"{self.org}/api/data/{version}/"
        datos = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": cfg["PP_CLIENT_ID"],
            "client_secret": cfg["PP_CLIENT_SECRET"],
            "scope": self.org + "/.default",
        }).encode()
        url = f"https://login.microsoftonline.com/{cfg['PP_TENANT_ID']}/oauth2/v2.0/token"
        with urllib.request.urlopen(urllib.request.Request(url, data=datos), timeout=30) as r:
            self._token = json.load(r)["access_token"]

    def call(self, metodo, ruta, cuerpo=None, solucion=None, cabeceras=None, timeout=180):
        """Devuelve (estado_http, cuerpo_json, cabeceras). Un error HTTP no lanza excepción:
        vuelve como (código, {"error": mensaje}, {})."""
        h = {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Content-Type": "application/json; charset=utf-8",
        }
        if solucion:
            h["MSCRM.SolutionUniqueName"] = solucion
        h.update(cabeceras or {})
        ruta = urllib.parse.quote(ruta, safe="/?&=$(),'@._-:")
        req = urllib.request.Request(
            self.api + ruta, method=metodo, headers=h,
            data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read().decode() or "{}"
                return r.status, (json.loads(txt) if txt.lstrip().startswith(("{", "[")) else {}), dict(r.headers)
        except urllib.error.HTTPError as e:
            txt = e.read().decode()
            try:
                msg = json.loads(txt)["error"]["message"]
            except Exception:
                msg = txt[:1000]
            return e.code, {"error": msg}, {}

    def texto(self, ruta, accept="application/xml", timeout=180):
        """Devuelve `(estado_http, texto)` SIN parsear. `call()` descarta todo
        lo que no sea JSON y devuelve `{}`, así que no sirve para leer el
        documento `$metadata`, que es XML y es donde hay que mirar si una
        Custom API está publicada para los conectores."""
        h = {
            "Authorization": "Bearer " + self._token,
            "Accept": accept,
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        req = urllib.request.Request(
            self.api + urllib.parse.quote(ruta, safe="/?&=$(),'@._-:"), method="GET", headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")[:2000]

    def subir_archivo(self, ruta_columna, nombre_archivo, contenido, timeout=300):
        """Sube bytes crudos a una columna de archivo: PATCH a
        `<conjunto>(<id>)/<columna>` con `application/octet-stream` y el nombre
        en la cabecera `x-ms-file-name`. Va aparte de `call()` porque ese
        siempre serializa JSON, y acá el cuerpo son bytes."""
        h = {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Content-Type": "application/octet-stream",
            "x-ms-file-name": nombre_archivo,
        }
        req = urllib.request.Request(
            self.api + urllib.parse.quote(ruta_columna, safe="/?&=$(),'@._-:"),
            method="PATCH", headers=h, data=contenido)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, {}, dict(r.headers)
        except urllib.error.HTTPError as e:
            txt = e.read().decode()
            try:
                msg = json.loads(txt)["error"]["message"]
            except Exception:
                msg = txt[:1000]
            return e.code, {"error": msg}, {}

    @staticmethod
    def id_creado(cabeceras):
        """GUID del registro recién creado, tomado de la cabecera OData-EntityId."""
        return cabeceras.get("OData-EntityId", "").split("(")[-1].rstrip(")")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("uso: dataverse_api.py <GET|POST|PATCH|DELETE> <ruta> [json] [solucion]")
    cuerpo = json.loads(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
    estado, datos, _ = Dataverse().call(sys.argv[1].upper(), sys.argv[2], cuerpo,
                                        solucion=sys.argv[4] if len(sys.argv) > 4 else None)
    print(estado)
    print(json.dumps(datos, ensure_ascii=False, indent=1))
