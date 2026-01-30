"""HfssDesktop for pyaedt backend."""

from pyEPR.ansys._wrapper import COMWrapper, _unwrap_aedt_handle
from pyEPR.ansys.hfss_project import HfssProject


class HfssDesktop(COMWrapper):
    """Desktop wrapper for pyaedt backend."""
    def __init__(self, app, desktop):
        super(HfssDesktop, self).__init__()
        self.parent = app
        self._desktop_original = desktop
        self.version = self.get_version()

    def __bool__(self):
        try:
            return self._get_odesktop() is not None
        except Exception:
            return False

    def _get_odesktop(self):
        desktop_obj = self._desktop_original
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
        projs = self._get_odesktop().GetProjects()
        if projs is None:
            return 0
        return len(list(projs))

    def get_active_project(self):
        oproject = self._get_odesktop().GetActiveProject()
        return HfssProject(self, oproject, pyaedt_desktop=self._desktop_original)

    def get_projects(self):
        projs = self._get_odesktop().GetProjects()
        if projs is None:
            return []
        return [HfssProject(self, p, pyaedt_desktop=self._desktop_original) for p in list(projs)]

    def get_project_names(self):
        names = self._get_odesktop().GetProjectList()
        if names is None:
            return []
        return list(names)

    def get_messages(self, project_name="", design_name="", level=0):
        return self._get_odesktop().GetMessages(project_name, design_name, level)

    def get_version(self):
        if self._desktop_original and hasattr(self._desktop_original, "aedt_version_id"):
            return self._desktop_original.aedt_version_id
        return self._get_odesktop().GetVersion()

    def new_project(self):
        oproject = self._get_odesktop().NewProject()
        return HfssProject(self, oproject, pyaedt_desktop=self._desktop_original)

    def open_project(self, path):
        oproject = self._get_odesktop().OpenProject(str(path))
        return HfssProject(self, oproject, pyaedt_desktop=self._desktop_original)

    def set_active_project(self, name):
        self._get_odesktop().SetActiveProject(name)

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
