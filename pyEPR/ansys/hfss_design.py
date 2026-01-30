"""HfssDesign for pyaedt backend."""

from pathlib import Path

from ansys.aedt.core import Hfss as PyAEDTHfss
from ansys.aedt.core import Q3d as PyAEDTQ3d

from pyEPR import logger
from pyEPR.ansys._reporter import _ReporterWrapper
from pyEPR.ansys._wrapper import _unwrap_aedt_handle, COMWrapper
from pyEPR.ansys.hfss_fields_calc import HfssFieldsCalc
from pyEPR.ansys.hfss_modeler import HfssModeler
from pyEPR.ansys.hfss_setup import AnsysQ3DSetup, HfssDMSetup, HfssDTSetup, HfssEMSetup
from pyEPR.ansys.optimetrics import Optimetrics


class HfssDesign(COMWrapper):
    def __init__(self, project, design, pyaedt_desktop=None):
        super(HfssDesign, self).__init__()
        self.parent = project
        self._pyaedt_desktop = pyaedt_desktop
        self._pyaedt_app = None
        if design is not None:
            odes = _unwrap_aedt_handle(design, "odesign")
            self._design = odes if odes is not None else design
        else:
            self._design = design
        if self._design is None:
            self.name = None
            self.solution_type = None
            return
        self.name = self._design.GetName()
        self._ansys_version = self.parent._ansys_version
        try:
            self.solution_type = self._design.GetSolutionType()
        except Exception as e:
            logger.debug("design.GetSolutionType() %s. Assuming Q3D design", e)
            self.solution_type = "Q3D"
        self._setup_module = self._design.GetModule("AnalysisSetup")
        self._solutions = self._design.GetModule("Solutions")
        self._fields_calc = self._design.GetModule("FieldsReporter")
        self._output = self._design.GetModule("OutputVariable")
        self._boundaries = self._design.GetModule("BoundarySetup")
        self._reporter_raw = self._design.GetModule("ReportSetup")
        self._reporter = _ReporterWrapper(self._reporter_raw, self)
        self._modeler = self._design.SetActiveEditor("3D Modeler")
        self._optimetrics = self._design.GetModule("Optimetrics")
        self._mesh = self._design.GetModule("MeshSetup")
        self.modeler = HfssModeler(self, self._modeler, self._boundaries, self._mesh)
        self.optimetrics = Optimetrics(self)

    def __bool__(self):
        return self._design is not None

    def _get_pyaedt_app(self):
        if self._pyaedt_app is not None:
            return self._pyaedt_app
        try:
            project_name = self.parent.name
            design_name = self.name
            if self.solution_type == "Q3D":
                self._pyaedt_app = PyAEDTQ3d(project=project_name, design=design_name)
            else:
                self._pyaedt_app = PyAEDTHfss(project=project_name, design=design_name)
            logger.debug("Created PyAEDT app for %s/%s", project_name, design_name)
            return self._pyaedt_app
        except Exception as e:
            logger.warning("Could not create PyAEDT app: %s", e)
            return None

    def _get_odesktop(self):
        project = self.parent
        desktop = project.parent
        if hasattr(desktop, "_desktop_original") and desktop._desktop_original and hasattr(desktop._desktop_original, "odesktop"):
            odesk = getattr(desktop._desktop_original, "odesktop", None)
            if callable(odesk):
                return odesk()
            return odesk
        return desktop._get_odesktop()

    def _get_odesign(self):
        if self._design is None:
            raise AttributeError("_design is None")
        odesign = _unwrap_aedt_handle(self._design, "odesign")
        if odesign is not None and (hasattr(odesign, "ExportConvergence") or hasattr(odesign, "Analyze")):
            return odesign
        if hasattr(self._design, "ExportConvergence") or hasattr(self._design, "Analyze"):
            return self._design
        return self._design

    def export_report_to_file(self, report_name: str, filepath: str):
        self._reporter.ExportToFile(report_name, str(filepath))

    def add_message(self, message: str, severity: int = 0):
        self._get_odesktop().AddMessage(self.parent.name, self.name, severity, message)

    def save_screenshot(self, path: str = None, show: bool = True):
        if not path:
            path = Path().absolute() / "ansys.png"
        self._modeler._modeler.ExportModelImageToFile(
            str(path), 0, 0,
            ["NAME:SaveImageParams", "ShowAxis:=", "True", "ShowGrid:=", "True",
             "ShowRuler:=", "True", "ShowRegion:=", "Default", "Selections:=", "", "Orientation:=", ""],
        )
        if show:
            try:
                from IPython.display import display, Image
                display(Image(str(path)))
            except Exception:
                pass
        return path

    def rename_design(self, name):
        old_name = self._design.GetName()
        self._get_odesign().RenameDesignInstance(old_name, name)

    def copy_to_project(self, project):
        project.make_active()
        project._project.CopyDesign(self.name)
        project._project.Paste()
        return project.get_active_design()

    def duplicate(self, name=None):
        dup = self.copy_to_project(self.parent)
        if name is not None:
            dup.rename_design(name)
        return dup

    def get_setup_names(self):
        return self._setup_module.GetSetups()

    def get_setup(self, name=None):
        setups = self.get_setup_names()
        if not setups:
            raise EnvironmentError("No Setups Present")
        name = name or setups[0]
        if name not in setups:
            raise EnvironmentError("Setup %s not found: %s" % (name, setups))
        if self.solution_type == "Eigenmode":
            return HfssEMSetup(self, name)
        if self.solution_type in ("DrivenModal", "HFSS Hybrid Modal Network", "HFSS Modal Network"):
            return HfssDMSetup(self, name)
        if self.solution_type in ("DrivenTerminal", "HFSS Terminal Network"):
            return HfssDTSetup(self, name)
        if self.solution_type == "Q3D":
            return AnsysQ3DSetup(self, name)
        logger.warning("Unknown solution type '%s'. Defaulting to DrivenModal setup.", self.solution_type)
        return HfssDMSetup(self, name)

    def get_variable_names(self):
        try:
            vars_ = self._design.GetVariables()
            return list(vars_) if vars_ is not None else []
        except Exception:
            return []

    def get_nominal_variation(self):
        try:
            return self._design.GetNominalVariation()
        except Exception:
            return ""

    def clean_up_solutions(self):
        self._get_odesign().DeleteFullVariation("All", True)

    def get_fields(self):
        return HfssFieldsCalc(self)
