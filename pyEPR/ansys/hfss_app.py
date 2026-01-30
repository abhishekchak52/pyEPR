"""HfssApp for pyaedt backend."""

import os

from ansys.aedt.core import Desktop as PyAEDTDesktop

from .. import logger
from ._wrapper import COMWrapper, _add_release_fn, _pyaedt_sessions
from .hfss_desktop import HfssDesktop


class HfssApp(COMWrapper):
    """Connect to Ansys AEDT via pyaedt (gRPC)."""
    def __init__(self, ProgID="AnsoftHfss.HfssScriptInterface",
                 version=None, non_graphical=None, new_desktop=None):
        super(HfssApp, self).__init__()
        self._pyaedt_desktop = None
        self._app = None
        non_graphical = os.getenv("PYAEDT_NON_GRAPHICAL", "False") if non_graphical is None else non_graphical
        self._pyaedt_desktop = PyAEDTDesktop(
            version=version,
            non_graphical=non_graphical,
            new_desktop=new_desktop,
            close_on_exit=True,
        )
        _pyaedt_sessions.append(self._pyaedt_desktop)
        self._app = self._pyaedt_desktop
        logger.info("Connected to Ansys via pyaedt backend")

    def get_app_desktop(self):
        return HfssDesktop(self, self._pyaedt_desktop)

    def release(self):
        super().release()
        if self._pyaedt_desktop is not None:
            try:
                self._pyaedt_desktop.release_desktop()
            except Exception:
                pass
            self._pyaedt_desktop = None
