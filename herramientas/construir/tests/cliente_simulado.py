"""Doble de prueba de `dataverse_api.Dataverse`, para las pruebas de
`herramientas/construir/`. Nunca toca la red. Mismo método `call()` que el
cliente real (misma firma, mismo tipo de retorno), y además:

- Registra cada llamada en `self.llamadas`, para que una prueba pueda
  comprobar qué se pidió y, sobre todo, qué **nunca** se llegó a pedir
  (un POST, un PATCH o un DELETE).
- Las respuestas se configuran de antemano con `.responder(metodo, matcher,
  respuesta)`. `matcher` es un string exacto o un `callable(ruta) -> bool`.
  `respuesta` es una tupla `(estado_http, cuerpo, cabeceras)`, una excepción
  (se lanza tal cual, para simular una falla de red o un timeout), o un
  `callable(ruta, cuerpo, solucion) -> tupla` para respuestas que dependen de
  lo que se mandó.
- Una llamada sin regla configurada es un error de la prueba (no del código
  bajo prueba): lanza `AssertionError` para que el fallo señale la prueba mal
  armada y no se confunda con una respuesta real del entorno.
"""


class ClienteSimulado:
    def __init__(self):
        self._reglas = []
        self.llamadas = []

    def responder(self, metodo, matcher, respuesta):
        self._reglas.append((metodo, matcher, respuesta))
        return self

    def call(self, metodo, ruta, cuerpo=None, solucion=None, cabeceras=None, timeout=180):
        self.llamadas.append({"metodo": metodo, "ruta": ruta, "cuerpo": cuerpo, "solucion": solucion})
        for m, matcher, respuesta in self._reglas:
            if m != metodo:
                continue
            coincide = matcher(ruta) if callable(matcher) else (ruta == matcher)
            if not coincide:
                continue
            if isinstance(respuesta, BaseException):
                raise respuesta
            if callable(respuesta):
                return respuesta(ruta, cuerpo, solucion)
            return respuesta
        raise AssertionError(f"ClienteSimulado: no hay regla configurada para {metodo} {ruta!r}")

    def metodos_llamados(self):
        return [l["metodo"] for l in self.llamadas]

    def hubo_escritura(self):
        """True si en algún momento se llamó POST, PATCH, DELETE o PUT."""
        return any(m in ("POST", "PATCH", "DELETE", "PUT") for m in self.metodos_llamados())


class FabricaFalla:
    """Zero-arg callable que simula que `Dataverse()` no se pudo construir
    (por ejemplo, falla de red o de credenciales al pedir el token)."""

    def __init__(self, excepcion):
        self._excepcion = excepcion

    def __call__(self):
        raise self._excepcion


class FabricaCentinela:
    """Zero-arg callable que NUNCA debería invocarse: se usa en las pruebas
    de validación previa (offline) para demostrar que, ante un playbook
    inválido, la herramienta ni siquiera intenta construir el cliente de
    Dataverse (cero llamadas de red, ni siquiera para pedir el token)."""

    def __init__(self):
        self.llamada = False

    def __call__(self):
        self.llamada = True
        raise AssertionError("FabricaCentinela: no debería haberse invocado (el error tenía que ser offline)")
