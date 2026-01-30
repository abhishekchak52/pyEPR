"""
Backend detection and selection for pyEPR Ansys interface.
Respects PYEPR_USE_PYAEDT: default (unset) = COM; when set truthy = pyaedt if available.
"""

import os

# Import logger from parent package (ansys is pyEPR.ansys)
from pyEPR import logger

_PYAEDT_AVAILABLE = False
_COM_AVAILABLE = False
_BACKEND = None

try:
    from ansys.aedt.core import Desktop as PyAEDTDesktop  # noqa: F401
    from ansys.aedt.core import Hfss as PyAEDTHfss  # noqa: F401
    from ansys.aedt.core import Q3d as PyAEDTQ3d  # noqa: F401
    _PYAEDT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PyAEDTDesktop = None
    PyAEDTHfss = None
    PyAEDTQ3d = None

try:
    import pythoncom  # noqa: F401
    from win32com.client import Dispatch, CDispatch  # noqa: F401
    _COM_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    pythoncom = None
    Dispatch = None
    CDispatch = None


def _is_truthy(val):
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "on")


def _is_falsy(val):
    if val is None:
        return True
    s = str(val).strip().lower()
    return s in ("0", "false", "no", "off", "")


def _resolve_backend_from_env():
    """Set _BACKEND from PYEPR_USE_PYAEDT. Default = COM."""
    global _BACKEND
    env_val = os.environ.get("PYEPR_USE_PYAEDT")
    if _is_truthy(env_val):
        if _PYAEDT_AVAILABLE:
            _BACKEND = "pyaedt"
            logger.info("Ansys backend: pyaedt (PYEPR_USE_PYAEDT is set)")
        elif _COM_AVAILABLE:
            _BACKEND = "com"
            logger.warning(
                "PYEPR_USE_PYAEDT is set but pyaedt not available; using COM backend."
            )
        else:
            _BACKEND = None
            logger.warning("No Ansys backend available.")
    else:
        if _COM_AVAILABLE:
            _BACKEND = "com"
            logger.info("Ansys backend: com (default)")
        elif _PYAEDT_AVAILABLE:
            _BACKEND = "pyaedt"
            logger.info("Ansys backend: pyaedt (COM not available)")
        else:
            _BACKEND = None
            logger.warning(
                "No Ansys backend available! Install pyaedt or win32com (Windows)."
            )


def get_available_backends():
    """Return list of available backends."""
    backends = []
    if _PYAEDT_AVAILABLE:
        backends.append("pyaedt")
    if _COM_AVAILABLE:
        backends.append("com")
    return backends


def get_backend():
    """Get the currently active backend."""
    return _BACKEND


def set_backend(backend: str):
    """Set the backend to 'pyaedt' or 'com'. Raises ValueError if not available."""
    global _BACKEND
    backend = backend.lower()
    if backend == "pyaedt":
        if not _PYAEDT_AVAILABLE:
            raise ValueError(
                "pyaedt backend requested but not available. pip install pyaedt"
            )
        _BACKEND = "pyaedt"
    elif backend == "com":
        if not _COM_AVAILABLE:
            raise ValueError(
                "COM backend only available on Windows with win32com installed."
            )
        _BACKEND = "com"
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'pyaedt' or 'com'.")
    logger.info(f"Ansys backend set to: {_BACKEND}")


def using_pyaedt():
    """True if pyaedt backend is active."""
    return _BACKEND == "pyaedt"


def using_com():
    """True if COM backend is active."""
    return _BACKEND == "com"


# Resolve backend from PYEPR_USE_PYAEDT on module load
_resolve_backend_from_env()
