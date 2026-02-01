"""HfssProject for pyaedt backend."""

from pyEPR.ansys._units import VariableString, increment_name
from pyEPR.ansys._wrapper import _unwrap_aedt_handle, COMWrapper
from pyEPR.ansys.hfss_design import HfssDesign


class HfssProject(COMWrapper):
    """Project wrapper for pyaedt backend."""
    def __init__(self, desktop, project, pyaedt_desktop=None):
        super(HfssProject, self).__init__()
        self.parent = desktop
        self._pyaedt_desktop = pyaedt_desktop
        if project is not None:
            oproj = _unwrap_aedt_handle(project, "oproject")
            self._project = oproj if oproj is not None else project
        else:
            self._project = project
        self._ansys_version = self.parent.version

    def __bool__(self):
        return self._project is not None

    def close(self):
        if self._project is not None:
            self._project.Close()

    def make_active(self):
        if self.name:
            self.parent.set_active_project(self.name)

    def get_designs(self):
        return [
            HfssDesign(self, d, pyaedt_desktop=self._pyaedt_desktop)
            for d in self._get_designs_list()
        ]

    def get_design_names(self):
        return [d.GetName() for d in self._get_designs_list()]

    def _get_designs_list(self):
        oproject = self._get_oproject()
        if oproject is None:
            return []
        try:
            designs = oproject.GetDesigns()
        except Exception:
            designs = None
        if designs is None:
            return []
        try:
            return list(designs)
        except TypeError:
            return [designs]

    def save(self, path=None):
        oproject = self._get_oproject()
        if oproject is None:
            raise EnvironmentError("No Project Available")
        if path is None:
            oproject.Save()
        else:
            oproject.SaveAs(str(path), True)

    def simulate_all(self):
        oproject = self._get_oproject()
        if oproject is None:
            raise EnvironmentError("No Project Available")
        oproject.SimulateAll()

    def import_dataset(self, path):
        oproject = self._get_oproject()
        if oproject is None:
            raise EnvironmentError("No Project Available")
        oproject.ImportDataset(str(path))

    def rename_design(self, design, rename):
        if design in self.get_designs():
            design.rename_design(design.name, rename)
        else:
            raise ValueError("%s design does not exist" % design.name)

    def duplicate_design(self, target, source):
        src_design = self.get_design(source)
        return src_design.duplicate(name=target)

    def get_variable_names(self):
        oproject = self._get_oproject()
        if oproject is None:
            return []
        vars_ = oproject.GetVariables()
        if vars_ is None:
            return []
        return [VariableString(s) for s in list(vars_)]

    def get_variables(self):
        oproject = self._get_oproject()
        if oproject is None:
            return {}
        vars_ = oproject.GetVariables()
        if vars_ is None:
            return {}
        return {VariableString(s): self.get_variable_value(s) for s in list(vars_)}

    def get_variable_value(self, name):
        oproject = self._get_oproject()
        if oproject is None:
            return None
        return oproject.GetVariableValue(name)

    def create_variable(self, name, value):
        oproject = self._get_oproject()
        if oproject is None:
            raise EnvironmentError("No Project Available")
        oproject.ChangeProperty([
            "NAME:AllTabs", [
                "NAME:ProjectVariableTab",
                ["NAME:PropServers", "ProjectVariables"],
                ["Name:NewProps", [
                    "NAME:" + name,
                    "PropType:=", "VariableProp",
                    "UserDef:=", True,
                    "Value:=", value,
                ]],
            ],
        ])

    def set_variable(self, name, value):
        oproject = self._get_oproject()
        if oproject is None:
            raise EnvironmentError("No Project Available")
        existing = oproject.GetVariables()
        existing = list(existing) if existing is not None else []
        if name not in existing:
            self.create_variable(name, value)
        else:
            oproject.SetVariableValue(name, value)
        return VariableString(name)

    def get_path(self):
        if self._project:
            return self._project.GetPath()
        raise Exception("Error: HFSS Project does not have a path.")

    def new_design(self, design_name, solution_type, design_type="HFSS"):
        oproject = self._get_oproject()
        existing_names = [d.GetName() for d in self._get_designs_list()]
        design_name_int = increment_name(design_name, existing_names)
        odesign = oproject.InsertDesign(design_type, design_name_int, solution_type, "")
        return HfssDesign(self, odesign, pyaedt_desktop=self._pyaedt_desktop)

    def _get_oproject(self):
        if self._project is None:
            return None
        oproject = _unwrap_aedt_handle(self._project, "oproject")
        if oproject is not None and (hasattr(oproject, "InsertDesign") or hasattr(oproject, "GetDesigns")):
            return oproject
        if hasattr(self._project, "InsertDesign") or hasattr(self._project, "GetDesigns"):
            return self._project
        return self._project

    def get_design(self, name):
        oproject = self._get_oproject()
        if oproject is None:
            raise EnvironmentError("No Project Available")
        return HfssDesign(self, oproject.GetDesign(name), pyaedt_desktop=self._pyaedt_desktop)

    def get_active_design(self):
        oproject = self._get_oproject()
        if oproject is None:
            raise EnvironmentError("No Project Available")
        d = oproject.GetActiveDesign()
        if d is None:
            raise EnvironmentError("No Design Active")
        return HfssDesign(self, d, pyaedt_desktop=self._pyaedt_desktop)

    def new_dm_design(self, name: str):
        return self.new_design(name, "DrivenModal")

    def new_em_design(self, name: str):
        return self.new_design(name, "Eigenmode")

    def new_q3d_design(self, name: str):
        return self.new_design(name, "Q3D", "Q3D Extractor")

    @property
    def name(self):
        if self._project is None:
            return None
        return self._project.GetName()
