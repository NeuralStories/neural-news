"""Límite de intentos por IP (NN-111.10).

Contra la fuerza bruta de la contraseña del editor: tras varios fallos desde la
misma dirección, la entrada se rechaza con `429` durante una ventana de
enfriamiento.

Es un límite **en memoria**, por proceso. Suficiente para la instalación de un
único editor (el modelo del producto); con varias instancias habría que
compartir el contador (Redis, base de datos) o dejar el límite en el proxy.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Contador de intentos fallidos por clave (normalmente la IP)."""

    def __init__(self, max_attempts: int = 5, window_s: int = 300, cooldown_s: int = 60):
        self.max_attempts = max_attempts
        self.window_s = window_s
        self.cooldown_s = cooldown_s
        self._fallos: dict[str, deque[float]] = defaultdict(deque)
        self._bloqueo_hasta: dict[str, float] = {}
        self._candado = threading.Lock()

    def comprobar(self, clave: str) -> None:
        """Lanza `DemasiadosIntentos` si la clave está bloqueada."""
        ahora = time.monotonic()
        with self._candado:
            hasta = self._bloqueo_hasta.get(clave)
            if hasta is None:
                return
            if ahora >= hasta:
                self._bloqueo_hasta.pop(clave, None)
                self._fallos.pop(clave, None)
                return
            restantes = int(hasta - ahora)
        raise DemasiadosIntentos(
            f"Demasiados intentos fallidos. Vuelve a probar en {restantes} segundos."
        )

    def registrar_fallo(self, clave: str) -> None:
        ahora = time.monotonic()
        with self._candado:
            fallos = self._fallos[clave]
            fallos.append(ahora)
            while fallos and ahora - fallos[0] > self.window_s:
                fallos.popleft()
            if len(fallos) >= self.max_attempts:
                self._bloqueo_hasta[clave] = ahora + self.cooldown_s

    def registrar_exito(self, clave: str) -> None:
        with self._candado:
            self._fallos.pop(clave, None)
            self._bloqueo_hasta.pop(clave, None)

    def limpiar(self) -> None:
        """Olvida los contadores (se usa en las pruebas)."""
        with self._candado:
            self._fallos.clear()
            self._bloqueo_hasta.clear()


class DemasiadosIntentos(Exception):
    """Se han superado los intentos permitidos desde esa dirección."""


# Un único limitador para la aplicación.
limitador_entradas = RateLimiter()
