"""Hulpstuk om de Home Assistant-proeven ook op Windows te kunnen draaien.

Home Assistant draait zelf niet op Windows: homeassistant/runner.py importeert
de POSIX-modules `fcntl` en `resource` op modulehoogte, en de Windows-lus van
asyncio maakt zijn eigen wekkerpijp met een socket, die het proefharnas
blokkeert. Geen van die drie dingen raakt de code van deze integratie.

Gebruik op Windows:

    python -m pytest -p windows_shim

Op Linux en in CI is dit bestand niet nodig en doet het niets: daar draaien de
proeven met de echte modules. Dit hulpstuk hoort dus bij het harnas, niet bij de
integratie, en er zit geen enkele regel van virtual_ems in.

Dit bestand moet als plugin geladen worden (-p), niet als conftest: pytest laadt
de plugins van pytest-homeassistant-custom-component eerder dan een conftest.py,
en dan is homeassistant/runner.py al geimporteerd.
"""

from __future__ import annotations

import sys
import types

WINDOWS = sys.platform == "win32"


def _fake_fcntl() -> types.ModuleType:
    module = types.ModuleType("fcntl")
    module.LOCK_SH = 1
    module.LOCK_EX = 2
    module.LOCK_NB = 4
    module.LOCK_UN = 8

    def _niet_op_windows(*_args, **_kwargs):
        raise OSError("fcntl bestaat niet op Windows")

    module.flock = _niet_op_windows
    module.lockf = _niet_op_windows
    module.fcntl = _niet_op_windows
    module.ioctl = _niet_op_windows
    return module


def _fake_resource() -> types.ModuleType:
    module = types.ModuleType("resource")
    module.RLIMIT_NOFILE = 7
    module.RLIM_INFINITY = -1
    # Home Assistant verhoogt de limiet op open bestanden. Door een ruime
    # limiet te melden concludeert die code dat er niets te doen is.
    module.getrlimit = lambda _which: (8192, 8192)
    module.setrlimit = lambda _which, _limits: None
    return module


if WINDOWS:
    sys.modules.setdefault("fcntl", _fake_fcntl())
    sys.modules.setdefault("resource", _fake_resource())

    import socket as _socket

    _echte_socket = _socket.socket
    _echte_socketpair = _socket.socketpair

    def _socketpair(*args, **kwargs):
        """Maak de wekkerpijp van de asyncio-lus met een echte socket.

        Op Linux gebruikt asyncio hiervoor een AF_UNIX-paar, en dat laat het
        harnas door. Op Windows bestaat AF_UNIX niet en valt socketpair terug op
        AF_INET over 127.0.0.1, wat het harnas tegenhoudt. Het gaat hier om de
        interne pijp van de lus, niet om netwerkverkeer van de proef: het slot
        staat alleen open zolang die pijp gemaakt wordt.
        """
        slot = _socket.socket
        _socket.socket = _echte_socket
        try:
            return _echte_socketpair(*args, **kwargs)
        finally:
            _socket.socket = slot

    _socket.socketpair = _socketpair
