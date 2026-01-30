"""Standalone load/get functions for pyaedt backend."""

from pathlib import Path

from pyEPR import logger
from pyEPR.ansys._backend import get_backend
from pyEPR.ansys.hfss_app import HfssApp
from pyEPR.ansys.hfss_report import HfssReport


def get_active_project():
    app = HfssApp()
    desktop = app.get_app_desktop()
    return desktop.get_active_project()


def get_active_design():
    project = get_active_project()
    return project.get_active_design()


def get_report_arrays(name: str):
    d = get_active_design()
    r = HfssReport(d, name)
    return r.get_arrays()


def load_ansys_project(
    proj_name: str,
    project_path: str = None,
    extension: str = ".aedt",
    version: str = None,
    non_graphical: bool = False,
):
    logger.info("Using backend: %s", get_backend())
    if project_path:
        project_path = Path(project_path)
        assert project_path.is_dir(), "project_path is not a valid directory."
        project_path = Path(project_path, proj_name).with_suffix(extension)
        if not project_path.is_file():
            raise Exception("Invalid project filename. Not found: %s" % project_path)
        if Path(str(project_path) + ".lock").is_file():
            logger.warning("File is locked. If connection fails, delete the .lock file.")
    app = HfssApp(version=version, non_graphical=non_graphical)
    logger.info("Opened Ansys App")
    desktop = app.get_app_desktop()
    logger.info("Opened Ansys Desktop v%s", desktop.get_version())
    if proj_name is not None:
        if proj_name in desktop.get_project_names():
            desktop.set_active_project(proj_name)
            project = desktop.get_active_project()
        else:
            if project_path is None:
                raise ValueError("project_path is required to open project %s" % proj_name)
            project = desktop.open_project(str(project_path))
    else:
        projects_in_app = desktop.get_projects()
        project = desktop.get_active_project() if projects_in_app else None
    if project:
        logger.info("Opened Ansys Project\n\tFolder: %s\n\tProject: %s", project.get_path(), project.name)
    else:
        logger.info("Ansys Project was not found. Project is None.")
    return app, desktop, project
