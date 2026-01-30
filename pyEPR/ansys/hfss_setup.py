"""HfssSetup and subclasses for pyaedt backend."""

import io
import os
import re
import tempfile
from pathlib import Path

import pandas as pd

from .. import logger
from ._units import increment_name, ureg
from ._wrapper import HfssPropertyObject, make_float_prop, make_int_prop, make_str_prop
from .hfss_design_solutions import (
    HfssDMDesignSolutions,
    HfssEMDesignSolutions,
    HfssDTDesignSolutions,
    HfssQ3DDesignSolutions,
)
from .hfss_frequency_sweep import HfssFrequencySweep


class HfssSetup(HfssPropertyObject):
    prop_tab = "HfssTab"
    passes = make_int_prop("Passes")
    n_modes = make_int_prop("Modes")
    pct_refinement = make_float_prop("Percent Refinement")
    delta_f = make_float_prop("Delta F")
    min_freq = make_float_prop("Min Freq")
    basis_order = make_str_prop("Basis Order")

    def __init__(self, design, setup: str):
        super(HfssSetup, self).__init__()
        self.parent = design
        self.prop_holder = design._design
        self._setup_module = design._setup_module
        self._reporter = design._reporter
        self._solutions = design._solutions
        self.name = setup
        self.solution_name = setup + " : LastAdaptive"
        self.prop_server = "AnalysisSetup:" + setup
        self.expression_cache_items = []
        self._ansys_version = self.parent._ansys_version

    def analyze(self, name=None):
        name = name or self.name
        logger.info("Analyzing setup %s", name)
        pyaedt_app = self.parent._get_pyaedt_app()
        if pyaedt_app is not None and hasattr(pyaedt_app, "analyze"):
            try:
                setup_name = name.split(" : ")[0] if " : " in name else name
                return pyaedt_app.analyze(setup=setup_name)
            except Exception as e:
                logger.debug("PyAEDT analyze failed: %s, falling back to COM", e)
        return self.parent._get_odesign().Analyze(name)

    def solve(self, name=None):
        name = name or self.name
        pyaedt_app = self.parent._get_pyaedt_app()
        if pyaedt_app is not None and hasattr(pyaedt_app, "analyze"):
            try:
                return pyaedt_app.analyze(setup=name)
            except Exception as e:
                logger.debug("PyAEDT solve failed: %s, falling back to COM", e)
        return self.parent._get_odesign().Solve(name)

    def insert_sweep(
        self,
        start_ghz,
        stop_ghz,
        count=None,
        step_ghz=None,
        name="Sweep",
        type="Fast",
        save_fields=False,
    ):
        if type not in ["Fast", "Interpolating", "Discrete"]:
            logger.error("insert_sweep: type must be in ['Fast', 'Interpolating', 'Discrete']")
        name = increment_name(name, self.get_sweep_names())
        created_name = name
        sweep_created = False
        pyaedt_app = self.parent._get_pyaedt_app()
        if pyaedt_app is not None:
            try:
                sweep_type_map = {"Fast": "Fast", "Interpolating": "Interpolating", "Discrete": "Discrete"}
                pyaedt_type = sweep_type_map.get(type, "Fast")
                if count and hasattr(pyaedt_app, "create_linear_count_sweep"):
                    sweep = pyaedt_app.create_linear_count_sweep(
                        setup=self.name, units="GHz",
                        start_frequency=start_ghz, stop_frequency=stop_ghz,
                        num_of_freq_points=count, name=name,
                        sweep_type=pyaedt_type, save_fields=save_fields,
                    )
                    if sweep:
                        sweep_created = True
                        created_name = getattr(sweep, "name", name) or name
                elif step_ghz and hasattr(pyaedt_app, "create_linear_step_sweep"):
                    sweep = pyaedt_app.create_linear_step_sweep(
                        setup=self.name, unit="GHz",
                        start_frequency=start_ghz, stop_frequency=stop_ghz,
                        step_size=step_ghz, name=name,
                        sweep_type=pyaedt_type, save_fields=save_fields,
                    )
                    if sweep:
                        sweep_created = True
                        created_name = getattr(sweep, "name", name) or name
            except Exception as e:
                logger.debug("PyAEDT sweep creation failed: %s, falling back to COM", e)
        if not sweep_created:
            params = [
                "NAME:" + name, "IsEnabled:=", True, "Type:=", type,
                "SaveFields:=", save_fields, "SaveRadFields:=", False, "ExtrapToDC:=", False,
            ]
            if self._ansys_version >= "2019":
                if count:
                    params.extend([
                        "RangeType:=", "LinearCount",
                        "RangeStart:=", "%fGHz" % start_ghz,
                        "RangeEnd:=", "%fGHz" % stop_ghz, "RangeCount:=", count,
                    ])
                if step_ghz:
                    params.extend([
                        "RangeType:=", "LinearStep",
                        "RangeStart:=", "%fGHz" % start_ghz,
                        "RangeEnd:=", "%fGHz" % stop_ghz, "RangeStep:=", step_ghz,
                    ])
            else:
                params.extend(["StartValue:=", "%fGHz" % start_ghz, "StopValue:=", "%fGHz" % stop_ghz])
                if step_ghz is not None:
                    params.extend(["SetupType:=", "LinearSetup", "StepSize:=", "%fGHz" % step_ghz])
                else:
                    params.extend(["SetupType:=", "LinearCount", "Count:=", count])
            self._setup_module.InsertFrequencySweep(self.name, params)
        return HfssFrequencySweep(self, created_name)

    def delete_sweep(self, name):
        self._setup_module.DeleteSweep(self.name, name)

    def get_sweep_names(self):
        return self._setup_module.GetSweeps(self.name)

    def get_sweep(self, name=None):
        sweeps = self.get_sweep_names()
        if not sweeps:
            raise EnvironmentError("No Sweeps Present")
        name = name or sweeps[0]
        if name not in sweeps:
            raise EnvironmentError("Sweep %s not found in %s" % (name, sweeps))
        return HfssFrequencySweep(self, name)

    def add_fields_convergence_expr(self, expr, pct_delta, phase=0):
        from .hfss_fields_calc import NamedCalcObject
        assert isinstance(expr, NamedCalcObject)
        self.expression_cache_items.append([
            "NAME:CacheItem", "Title:=", expr.name + "_conv", "Expression:=", expr.name,
            "Intrinsics:=", "Phase='%sdeg'" % phase, "IsConvergence:=", True,
            "UseRelativeConvergence:=", 1, "MaxConvergenceDelta:=", pct_delta,
            "MaxConvergeValue:=", "0.05", "ReportType:=", "Fields", ["NAME:ExpressionContext"],
        ])

    def commit_convergence_exprs(self):
        args = ["NAME:" + self.name, ["NAME:ExpressionCache", self.expression_cache_items]]
        self._setup_module.EditSetup(self.name, args)

    def get_convergence(self, variation="", pre_fn_args=None, overwrite=True):
        pre_fn_args = pre_fn_args or []
        temp = tempfile.NamedTemporaryFile()
        temp.close()
        temp_path = temp.name + ".conv"
        export_success = False
        actual_path = temp_path
        pyaedt_app = self.parent._get_pyaedt_app()
        if pyaedt_app is not None and hasattr(pyaedt_app, "export_convergence"):
            try:
                pyaedt_app.export_convergence(
                    setup=self.name, variations=variation or "", output_file=temp_path,
                )
                export_success = True
                if not Path(temp_path).is_file():
                    base_path = temp_path.rsplit(".", 1)[0]
                    for suffix in ["CG", "RL", "DCRL"]:
                        alt_path = "%s%s.conv" % (base_path, suffix)
                        if Path(alt_path).is_file():
                            actual_path = alt_path
                            break
            except Exception as e:
                logger.debug("PyAEDT export_convergence failed: %s", e)
        if not export_success:
            try:
                self.parent._get_odesign().ExportConvergence(
                    self.name, variation, *pre_fn_args, temp_path, overwrite,
                )
            except Exception as e:
                logger.error("ExportConvergence failed: %s", e)
                return None, ""
        temp_f = Path(actual_path)
        if not temp_f.is_file():
            return None, ""
        text = temp_f.read_text()
        text2 = text.split(r"==================")
        if len(text2) >= 3:
            df = pd.read_csv(io.StringIO(text2[3].strip()), sep="|", skipinitialspace=True, index_col=0)
            if "Unnamed: 3" in df.columns:
                df = df.drop("Unnamed: 3", axis=1)
        else:
            df = None
        return df, text

    def get_mesh_stats(self, variation=""):
        temp = tempfile.NamedTemporaryFile()
        temp.close()
        mesh_file = temp.name + ".mesh"
        pyaedt_app = self.parent._get_pyaedt_app()
        if pyaedt_app is not None and hasattr(pyaedt_app, "export_mesh_stats"):
            try:
                pyaedt_app.export_mesh_stats(setup=self.name, variations=variation or "", output_file=mesh_file)
            except Exception:
                self.parent._get_odesign().ExportMeshStats(self.name, variation, mesh_file, True)
        else:
            self.parent._get_odesign().ExportMeshStats(self.name, variation, mesh_file, True)
        try:
            df = pd.read_csv(mesh_file, delimiter="|", skipinitialspace=True, skiprows=7, skipfooter=1, engine="python")
            if "Unnamed: 9" in df.columns:
                df = df.drop("Unnamed: 9", axis=1)
        except Exception:
            df = None
        return df

    def get_profile(self, variation=""):
        fn = tempfile.mktemp()
        pyaedt_app = self.parent._get_pyaedt_app()
        if pyaedt_app is not None and hasattr(pyaedt_app, "export_profile"):
            try:
                pyaedt_app.export_profile(setup=self.name, variations=variation or "", output_file=fn)
            except Exception:
                self.parent._get_odesign().ExportProfile(self.name, variation, fn, False)
        else:
            self.parent._get_odesign().ExportProfile(self.name, variation, fn, False)
        try:
            return pd.read_csv(fn, delimiter="\t", skipinitialspace=True, skiprows=6, skipfooter=1, engine="python")
        except Exception:
            return None

    def get_fields(self):
        from .hfss_fields_calc import HfssFieldsCalc
        return HfssFieldsCalc(self)


class HfssDMSetup(HfssSetup):
    solution_freq = make_float_prop("Solution Freq")
    delta_s = make_float_prop("Delta S")
    solver_type = make_str_prop("Solver Type")

    def setup_link(self, linked_setup):
        args = [
            "NAME:" + self.name,
            ["NAME:MeshLink", "Project:=", "This Project*", "Design:=", linked_setup.parent.name,
             "Soln:=", linked_setup.solution_name, self._map_variables_by_name(),
             "ForceSourceToSolve:=", True, "PathRelativeTo:=", "TargetProject"],
        ]
        self._setup_module.EditSetup(self.name, args)

    def _map_variables_by_name(self):
        project_variables = self.parent.parent.get_variable_names()
        design_variables = self.parent.get_variable_names()
        args = ["NAME:Params"]
        for name in project_variables:
            args.extend([str(name) + ":=", str(name)])
        for name in design_variables:
            args.extend([str(name) + ":=", str(name)])
        return args

    def get_solutions(self):
        return HfssDMDesignSolutions(self, self.parent._solutions)


class HfssDTSetup(HfssDMSetup):
    def get_solutions(self):
        return HfssDTDesignSolutions(self, self.parent._solutions)


class HfssEMSetup(HfssSetup):
    min_freq = make_float_prop("Min Freq")
    n_modes = make_int_prop("Modes")
    delta_f = make_float_prop("Delta F")

    def get_solutions(self):
        return HfssEMDesignSolutions(self, self.parent._solutions)


class AnsysQ3DSetup(HfssSetup):
    prop_tab = "CG"
    max_pass = make_int_prop("Max. Number of Passes")
    min_pass = make_int_prop("Min. Number of Passes")
    pct_error = make_int_prop("Percent Error")
    frequency = make_str_prop("Adaptive Freq", "General")
    n_modes = 0

    def get_frequency_Hz(self):
        return int(ureg(self.frequency).to("Hz").magnitude)

    def get_solutions(self):
        return HfssQ3DDesignSolutions(self, self.parent._solutions)

    def get_convergence(self, variation="", pre_fn_args=None, overwrite=True):
        return super().get_convergence(variation, pre_fn_args=["CG"] if pre_fn_args is None else ["CG"] + list(pre_fn_args), overwrite=overwrite)

    def get_matrix(
        self,
        variation="",
        pass_number=0,
        frequency=None,
        MatrixType="Maxwell",
        solution_kind="LastAdaptive",
        ACPlusDCResistance=False,
        soln_type="C",
    ):
        import tempfile as tf
        path = tf.mktemp(suffix=".txt")
        export_success = False
        pyaedt_app = self.parent._get_pyaedt_app()
        if pyaedt_app is not None and hasattr(pyaedt_app, "export_matrix_data"):
            try:
                pyaedt_app.export_matrix_data(
                    file_name=path, problem_type=soln_type, variations=variation or None,
                    setup=self.name, sweep=solution_kind, reduce_matrix="Original",
                    r_unit="ohm", l_unit="nH", c_unit="fF", g_unit="mSie",
                    freq=frequency, matrix_type=MatrixType, export_ac_dc_res=ACPlusDCResistance,
                )
                export_success = True
            except Exception as e:
                logger.debug("PyAEDT export_matrix_data failed: %s", e)
        if not export_success:
            try:
                self.parent._get_odesign().ExportMatrixData(
                    path, soln_type, variation, "%s:%s" % (self.name, solution_kind),
                    "Original", "ohm", "nH", "fF", "mSie", frequency,
                    MatrixType, pass_number, ACPlusDCResistance,
                )
                export_success = True
            except Exception as e:
                logger.error("ExportMatrixData failed: %s", e)
                return None, None, (None, None), None
        if not os.path.exists(path):
            return None, None, (None, None), None
        return self.load_q3d_matrix(path)

    @staticmethod
    def _readin_Q3D_matrix(path: str):
        text = Path(path).read_text()
        s1 = text.split("Capacitance Matrix")
        assert len(s1) == 2
        s2 = s1[1].split("Conductance Matrix")
        df_cmat = pd.read_csv(io.StringIO(s2[0].strip()), delim_whitespace=True, skipinitialspace=True, index_col=0)
        units = re.findall(r"C Units:(.*?),", text)[0]
        if len(s2) > 1:
            df_cond = pd.read_csv(io.StringIO(s2[1].strip()), delim_whitespace=True, skipinitialspace=True, index_col=0)
            units_cond = re.findall(r"G Units:(.*?)\n", text)[0]
        else:
            df_cond = units_cond = None
        var = re.findall(r"DesignVariation:(.*?)\n", text)
        if not var:
            var = re.findall(r"Design Variation:(.*?)\n", text)
        design_variation = var[0] if var else ""
        return df_cmat, units, design_variation, df_cond, units_cond

    @staticmethod
    def load_q3d_matrix(path, user_units="fF"):
        (df_cmat, Cunits, design_variation, df_cond, units_cond) = AnsysQ3DSetup._readin_Q3D_matrix(path)
        q = ureg.parse_expression(Cunits).to(user_units)
        df_cmat = df_cmat * q.magnitude
        return df_cmat, user_units, (df_cond, units_cond), design_variation
