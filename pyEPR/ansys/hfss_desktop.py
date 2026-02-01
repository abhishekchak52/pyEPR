"""HfssApp and HfssDesktop for pyaedt backend."""

import os

from ansys.aedt.core import Desktop as PyAEDTDesktop

from pyEPR import logger
from pyEPR.ansys._wrapper import (
    COMWrapper,
    _pyaedt_sessions,
    _unwrap_aedt_handle,
)
from pyEPR.ansys.hfss_project import HfssProject


class HfssApp(COMWrapper):
    """Connect to Ansys AEDT via pyaedt (gRPC)."""

    def __init__(
        self,
        ProgID="AnsoftHfss.HfssScriptInterface",
        version=None,
        non_graphical=None,
        new_desktop=None,
    ):
        super(HfssApp, self).__init__()
        self._pyaedt_desktop = None
        self._app = None
        non_graphical = (
            os.getenv("PYAEDT_NON_GRAPHICAL", False)
            if non_graphical is None
            else non_graphical
        )
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


class HfssDesktop(COMWrapper):
    """Desktop wrapper for pyaedt backend."""
    def __init__(self, app, desktop):
        super(HfssDesktop, self).__init__()
        self.parent = app
        self._desktop_pyaedt = desktop
        self.version = self.get_version()

    def __bool__(self):
        try:
            return self._get_odesktop() is not None
        except Exception:
            return False

    def _get_odesktop(self):
        desktop_obj = self._desktop_pyaedt
        odesk = _unwrap_aedt_handle(desktop_obj, "odesktop")
        if odesk is not None:
            return odesk
        return desktop_obj

    @property
    def odesktop(self):
        return self._get_odesktop()

    @property
    def _desktop(self):
        return self._get_odesktop()

    def close_all_windows(self):
        self._get_odesktop().CloseAllWindows()

    def project_count(self):
        return len(self._desktop_pyaedt.project_list)
        # projs = self._get_odesktop().GetProjects()
        # if projs is None:
        #     return 0
        # return len(list(projs))

    def get_active_project(self):
        oproject = self._desktop_pyaedt.active_project()
        return HfssProject(self, oproject)

    def get_projects(self):
        projs = self._get_odesktop().GetProjects()
        if projs is None:
            return []
        return [HfssProject(self, p) for p in list(projs)]

    def get_project_names(self):
        return self._desktop_pyaedt.project_list
        # names = self._get_odesktop().GetProjectList()
        # if names is None:
        #     return []
        # return list(names)

    def get_messages(self, project_name="", design_name="", level=0):
        return self._get_odesktop().GetMessages(project_name, design_name, level)

    def get_version(self):
        return self._desktop_pyaedt.aedt_version_id

    def new_project(self):
        oproject = self._get_odesktop().NewProject()
        return HfssProject(self, oproject)

    def open_project(self, path):
        oproject = self._get_odesktop().OpenProject(str(path))
        return HfssProject(self, oproject)

    def set_active_project(self, name):
        # This automatically returns to the active project after setting it. 
        self._desktop_pyaedt.active_project(name)

    @property
    def project_directory(self):
        return self._get_odesktop().GetProjectDirectory()

    @project_directory.setter
    def project_directory(self, path):
        self._get_odesktop().SetProjectDirectory(str(path))

    @property
    def library_directory(self):
        return self._get_odesktop().GetLibraryDirectory()

    @library_directory.setter
    def library_directory(self, path):
        self._get_odesktop().SetLibraryDirectory(str(path))

    @property
    def temp_directory(self):
        return self._get_odesktop().GetTempDirectory()

    @temp_directory.setter
    def temp_directory(self, path):
        self._get_odesktop().SetTempDirectory(str(path))
