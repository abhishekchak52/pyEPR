"""
pyEPR.ansys_aedt
    PyAEDT-based implementation

Purpose:
    Handles Ansys interaction and control using PyAEDT API.
    This module provides the same interface as ansys_com.py but uses PyAEDT instead of COM.

@authors:
    Originally contributed by Phil Reinhold.
    Developed further by Zlatko Minev, Zaki Leghtas, and the pyEPR team.
    PyAEDT migration by the pyEPR team.
"""


from typing import List, Optional

import atexit
import signal
import time
from collections.abc import Iterable
from numbers import Number
from pathlib import Path

from sympy.parsing import sympy_parser

from . import logger

# Handle a few usually troublesome to import packages, which the user may not have
# installed yet
try:
    import pyaedt  # noqa: F401
except (ImportError, ModuleNotFoundError):
    pass  # raise NameError ("pyaedt module not installed. Please install.")

try:
    from pint import UnitRegistry

    ureg = UnitRegistry()
    Q = ureg.Quantity
except (ImportError, ModuleNotFoundError):
    pass  # raise NameError ("Pint module not installed. Please install.")


##############################################################################
###

BASIS_ORDER = {"Zero Order": 0, "First Order": 1, "Second Order": 2, "Mixed Order": -1}

# UNITS
# LENGTH_UNIT         --- HFSS UNITS
# #Assumed default input units for ansys hfss
LENGTH_UNIT = "meter"
# LENGTH_UNIT_ASSUMED --- USER UNITS
# if a user inputs a blank number with no units in `parse_fix`,
# we can assume the following using
LENGTH_UNIT_ASSUMED = "mm"


def simplify_arith_expr(expr):
    """
    TODO: Implement using PyAEDT
    """
    try:
        out = repr(sympy_parser.parse_expr(str(expr)))
        return out
    except:
        print("Couldn't parse", expr)
        raise


def increment_name(base, existing):
    """
    TODO: Implement using PyAEDT
    """
    if base not in existing:
        return base
    n = 1

    def make_name():
        return base + str(n)

    while make_name() in existing:
        n += 1
    return make_name()


def extract_value_unit(expr, units):
    """
    :type expr: str
    :type units: str
    :return: float
    """
    try:
        return Q(expr).to(units).magnitude
    except Exception:
        try:
            return float(expr)
        except Exception:
            return expr


def extract_value_dim(expr):
    """
    type expr: str
    """
    return str(Q(expr).dimensionality)


def parse_entry(entry, convert_to_unit=LENGTH_UNIT):
    """
    Should take a list of tuple of list... of int, float or str...
    For iterables, returns lists
    """
    if not isinstance(entry, list) and not isinstance(entry, tuple):
        return extract_value_unit(entry, convert_to_unit)
    else:
        entries = entry
        _entry = []
        for entry in entries:
            _entry.append(parse_entry(entry, convert_to_unit=convert_to_unit))
        return _entry


def fix_units(x, unit_assumed=None):
    """
    Convert all numbers to string and append the assumed units if needed.
    For an iterable, returns a list
    """
    unit_assumed = LENGTH_UNIT_ASSUMED if unit_assumed is None else unit_assumed
    if isinstance(x, str):
        # Check if there are already units defined, assume of form 2.46mm  or 2.0 or 4.
        if x[-1].isdigit() or x[-1] == ".":  # number
            return x + unit_assumed
        else:  # units are already applied
            return x

    elif isinstance(x, Number):
        return fix_units(str(x) + unit_assumed, unit_assumed=unit_assumed)

    elif isinstance(x, Iterable):  # hasattr(x, '__iter__'):
        return [fix_units(y, unit_assumed=unit_assumed) for y in x]
    else:
        return x


def parse_units(x):
    """
    Convert number, string, and lists/arrays/tuples to numbers scaled
    in HFSS units.

    Converts to                  LENGTH_UNIT = meters  [HFSS UNITS]
    Assumes input units  LENGTH_UNIT_ASSUMED = mm      [USER UNITS]

    [USER UNITS] ----> [HFSS UNITS]
    """
    return parse_entry(fix_units(x))


def unparse_units(x):
    """
    Undo effect of parse_unit.

    Converts to     LENGTH_UNIT_ASSUMED = mm     [USER UNITS]
    Assumes input units     LENGTH_UNIT = meters [HFSS UNITS]

    [HFSS UNITS] ----> [USER UNITS]
    """
    return parse_entry(fix_units(x, unit_assumed=LENGTH_UNIT), LENGTH_UNIT_ASSUMED)


def parse_units_user(x):
    """
    Convert from user assumed units to user assumed units
    [USER UNITS] ----> [USER UNITS]
    """
    return parse_entry(fix_units(x, LENGTH_UNIT_ASSUMED), LENGTH_UNIT_ASSUMED)


class VariableString(str):
    """
    TODO: Implement using PyAEDT
    """
    def __add__(self, other):  # type: ignore
        return var("(%s) + (%s)" % (self, other))

    def __radd__(self, other):  # type: ignore
        return var("(%s) + (%s)" % (other, self))

    def __sub__(self, other):  # type: ignore
        return var("(%s) - (%s)" % (self, other))

    def __rsub__(self, other):  # type: ignore
        return var("(%s) - (%s)" % (other, self))

    def __mul__(self, other):  # type: ignore
        return var("(%s) * (%s)" % (self, other))

    def __rmul__(self, other):  # type: ignore
        return var("(%s) * (%s)" % (other, self))

    def __div__(self, other):
        return var("(%s) / (%s)" % (self, other))

    def __rdiv__(self, other):
        return var("(%s) / (%s)" % (other, self))

    def __truediv__(self, other):
        return var("(%s) / (%s)" % (self, other))

    def __rtruediv__(self, other):
        return var("(%s) / (%s)" % (other, self))

    def __pow__(self, other):
        return var("(%s) ^ (%s)" % (self, other))

    def __rpow__(self, other):
        return var("(%s) ^ (%s)" % (other, self))

    def __neg__(self):
        return var("-(%s)" % self)

    def __abs__(self):
        return var("abs(%s)" % self)


def var(x):
    """
    TODO: Implement using PyAEDT
    """
    if isinstance(x, str):
        return VariableString(simplify_arith_expr(x))
    return x


_release_fns = []


def _add_release_fn(fn):
    """
    TODO: Implement using PyAEDT
    """
    global _release_fns
    _release_fns.append(fn)
    atexit.register(fn)
    signal.signal(signal.SIGTERM, fn)
    signal.signal(signal.SIGABRT, fn)


def release():
    """
    Release connection to Ansys.
    TODO: Implement using PyAEDT
    """
    global _release_fns
    for fn in _release_fns:
        fn()
    time.sleep(0.1)
    # Note: PyAEDT handles connection cleanup differently than COM
    # TODO: Add PyAEDT-specific cleanup if needed


class COMWrapper(object):
    """
    TODO: Rename or adapt for PyAEDT - this was originally for COM objects
    """
    def __init__(self):
        _add_release_fn(self.release)

    def release(self):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssPropertyObject(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    prop_holder = None
    prop_tab = None
    prop_server = None


def make_str_prop(name, prop_tab=None, prop_server=None):
    """
    TODO: Implement using PyAEDT
    """
    return make_prop(name, prop_tab=prop_tab, prop_server=prop_server)


def make_int_prop(name, prop_tab=None, prop_server=None):
    """
    TODO: Implement using PyAEDT
    """
    return make_prop(
        name,
        prop_tab=prop_tab,
        prop_server=prop_server,
        prop_args=["MustBeInt:=", True],
    )


def make_float_prop(name, prop_tab=None, prop_server=None):
    """
    TODO: Implement using PyAEDT
    """
    return make_prop(
        name,
        prop_tab=prop_tab,
        prop_server=prop_server,
        prop_args=["MustBeInt:=", False],
    )


def make_prop(name, prop_tab=None, prop_server=None, prop_args=None):
    """
    TODO: Implement using PyAEDT
    """
    def set_prop(
        self, value, prop_tab=prop_tab, prop_server=prop_server, prop_args=prop_args
    ):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_prop(self, prop_tab=prop_tab, prop_server=prop_server):
        """
        TODO: Implement using PyAEDT
        """
        pass

    return property(get_prop, set_prop)


def set_property(prop_holder, prop_tab, prop_server, name, value, prop_args=None):
    """
    More general non obj oriented, functional version
    prop_args = [] by default
    TODO: Implement using PyAEDT
    """
    pass


class HfssApp(COMWrapper):
    """
    TODO: Implement using PyAEDT - likely using pyaedt.Desktop or similar
    """
    def __init__(self, ProgID="AnsoftHfss.HfssScriptInterface"):
        """
        Connect to PyAEDT-based object.
            Parameter is kept for compatibility but may not be used in PyAEDT.

        Version changes for Ansys HFSS for the main object
            v2016 - 'Ansoft.ElectronicsDesktop'
            v2017 and subsequent - 'AnsoftHfss.HfssScriptInterface'

        TODO: Implement using PyAEDT Desktop API
        """
        super(HfssApp, self).__init__()
        # TODO: Initialize PyAEDT Desktop connection
        # self._app = pyaedt.Desktop(...)

    def get_app_desktop(self):
        """
        TODO: Implement using PyAEDT
        """
        # return HfssDesktop(self, self._app.GetAppDesktop())
        pass


class HfssDesktop(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, app, desktop):
        """
        :type app: HfssApp
        :type desktop: PyAEDT Desktop object
        """
        super(HfssDesktop, self).__init__()
        self.parent = app
        # TODO: Store PyAEDT desktop object
        # self._desktop = desktop

        # ansys version, needed to check for command changes,
        # since some commands have changed over the years
        self.version = self.get_version()

    def close_all_windows(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def project_count(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_active_project(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_projects(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_project_names(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_messages(self, project_name="", design_name="", level=0):
        """
        Use:  Collects the messages from a specified project and design.
        Syntax:              GetMessages <ProjectName>, <DesignName>, <SeverityName>
        Return Value:    A simple array of strings.

        Parameters:
        <ProjectName>
            Type:<string>
            Name of the project for which to collect messages.
            An incorrect project name results in no messages (design is ignored)
            An empty project name results in all messages (design is ignored)

        <DesignName>
            Type: <string>
            Name of the design in the named project for which to collect messages
            An incorrect design name results in no messages for the named project
            An empty design name results in all messages for the named project

        <SeverityName>
            Type: <integer>
            Severity is 0-3, and is tied in to info/warning/error/fatal types as follows:
                0 is info and above
                1 is warning and above
                2 is error and fatal
                3 is fatal only (rarely used)
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_version(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def new_project(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def open_project(self, path):
        """
        returns error if already open
        TODO: Implement using PyAEDT
        """
        pass

    def set_active_project(self, name):
        """
        TODO: Implement using PyAEDT
        """
        pass

    @property
    def project_directory(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    @project_directory.setter
    def project_directory(self, path):
        """
        TODO: Implement using PyAEDT
        """
        pass

    @property
    def library_directory(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    @library_directory.setter
    def library_directory(self, path):
        """
        TODO: Implement using PyAEDT
        """
        pass

    @property
    def temp_directory(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    @temp_directory.setter
    def temp_directory(self, path):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssProject(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, desktop, project):
        """
        :type desktop: HfssDesktop
        :type project: PyAEDT Project object
        """
        super(HfssProject, self).__init__()
        self.parent = desktop
        # TODO: Store PyAEDT project object
        # self._project = project
        # self.name = project.GetName()
        self._ansys_version = self.parent.version

    def close(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def make_active(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_designs(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_design_names(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def save(self, path=None):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def simulate_all(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def import_dataset(self, path):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def rename_design(self, design, rename):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def duplicate_design(self, target, source):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_variable_names(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_variables(self):
        """
        Returns the project variables only, which start with $. These are global variables.
        TODO: Implement using PyAEDT
        """
        pass

    def get_variable_value(self, name):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def create_variable(self, name, value):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def set_variable(self, name, value):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_path(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def new_design(self, design_name, solution_type, design_type="HFSS"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_design(self, name):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_active_design(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def new_dm_design(self, name: str):
        """
        Create a new driven model design

        Args:
            name (str): Name of driven modal design
        
        TODO: Implement using PyAEDT
        """
        pass

    def new_em_design(self, name: str):
        """
        Create a new eigenmode design

        Args:
            name (str): Name of eigenmode design
        
        TODO: Implement using PyAEDT
        """
        pass

    def new_q3d_design(self, name: str):
        """
        Create a new Q3D design.
        Args:
            name (str): Name of Q3D design
        
        TODO: Implement using PyAEDT
        """
        pass

    @property  # v2016
    def name(self):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssDesign(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, project, design):
        """
        TODO: Implement using PyAEDT
        """
        super(HfssDesign, self).__init__()
        self.parent = project
        # TODO: Store PyAEDT design object
        # self._design = design
        # self.name = design.GetName()
        self._ansys_version = self.parent._ansys_version

        try:
            # This function does not exist if the design is not HFSS
            # self.solution_type = design.GetSolutionType()
            self.solution_type = "Unknown"
        except Exception as e:
            logger.debug(
                f"Exception occurred at design.GetSolutionType() {e}. Assuming Q3D design"
            )
            self.solution_type = "Q3D"

        # TODO: Initialize PyAEDT modules
        # self._setup_module = design.GetModule("AnalysisSetup")
        # self._solutions = design.GetModule("Solutions")
        # self._fields_calc = design.GetModule("FieldsReporter")
        # self._output = design.GetModule("OutputVariable")
        # self._boundaries = design.GetModule("BoundarySetup")
        # self._reporter = design.GetModule("ReportSetup")
        # self._modeler = design.SetActiveEditor("3D Modeler")
        # self._optimetrics = design.GetModule("Optimetrics")
        # self._mesh = design.GetModule("MeshSetup")
        # self.modeler = HfssModeler(self, self._modeler, self._boundaries, self._mesh)
        # self.optimetrics = Optimetrics(self)

    def add_message(self, message: str, severity: int = 0):
        """
        Add a message to HFSS log with severity and context to message window.

        Keyword Args:
            severity (int) : 0 = Informational, 1 = Warning, 2 = Error, 3 = Fatal..
        
        TODO: Implement using PyAEDT
        """
        pass

    def save_screenshot(self, path: Optional[str] = None, show: bool = True):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def rename_design(self, name):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def copy_to_project(self, project):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def duplicate(self, name=None):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_setup_names(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_setup(self, name=None):
        """
        :rtype: HfssSetup
        
        TODO: Implement using PyAEDT
        """
        pass

    def create_q3d_setup(
        self,
        freq_ghz=5.0,
        name="Setup",
        save_fields=False,
        enabled=True,
        max_passes=15,
        min_passes=2,
        min_converged_passes=2,
        percent_error=0.5,
        percent_refinement=30,
        auto_increase_solution_order=True,
        solution_order="High",
        solver_type="Iterative",
    ):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def create_dm_setup(
        self,
        freq_ghz=1,
        name="Setup",
        max_delta_s=0.1,
        max_passes=10,
        min_passes=1,
        min_converged=1,
        pct_refinement=30,
        basis_order=-1,
    ):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def create_dt_setup(
        self,
        freq_ghz=1,
        name="Setup",
        max_delta_s=0.1,
        max_passes=10,
        min_passes=1,
        min_converged=1,
        pct_refinement=30,
        basis_order=-1,
    ):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def create_em_setup(
        self,
        name="Setup",
        min_freq_ghz=1,
        n_modes=1,
        max_delta_f=0.1,
        max_passes=10,
        min_passes=1,
        min_converged=1,
        pct_refinement=30,
        basis_order=-1,
    ):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def delete_setup(self, name):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def delete_full_variation(self, DesignVariationKey="All", del_linked_data=False):
        """
        DeleteFullVariation
        Use:                   Use to selectively make deletions or delete all solution data.
        Command:         HFSS>Results>Clean Up Solutions...
        Syntax:              DeleteFullVariation Array(<parameters>), boolean
        Parameters:      All | <DataSpecifierArray>
                        If, All, all data of existing variations is deleted.
                        Array(<DesignVariationKey>, )
                        <DesignVariationKey>
                            Type: <string>
                            Design variation string.
                        <Boolean>
                        Type: boolean
                        Whether to also delete linked data.
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_nominal_variation(self):
        """
        Use: Gets the nominal variation string
        Return Value: Returns a string representing the nominal variation
        Returns string such as "Height='0.06mm' Lj='13.5nH'"
        
        TODO: Implement using PyAEDT
        """
        pass

    def create_variable(self, name, value, postprocessing=False):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _variation_string_to_variable_list(
        self, variation_string: str, for_prop_server=True
    ):
        """
        Example:
        Takes
            "Cj='2fF' Lj='13.5nH'"
        for for_prop_server=True into
            [['NAME:Cj', 'Value:=', '2fF'], ['NAME:Lj', 'Value:=', '13.5nH']]
        or for for_prop_server=False into
            [['Cj', '2fF'], ['Lj', '13.5nH']]
        
        TODO: Implement using PyAEDT
        """
        pass

    def set_variables(self, variation_string: str):
        """
        Set all variables to match a solved variation string.

        Args:
            variation_string (str) :  Variation string such as
                "Cj='2fF' Lj='13.5nH'"
        
        TODO: Implement using PyAEDT
        """
        pass

    def set_variable(self, name: str, value: str, postprocessing=False):
        """
        Warning: This is case sensitive,

        Arguments:
            name {str} -- Name of variable to set, such as 'Lj_1'.
                          This is not the same as as 'LJ_1'.
                          You must use the same casing.
            value {str} -- Value, such as '10nH'

        Keyword Arguments:
            postprocessing {bool} -- Postprocessing variable only or not.
                          (default: {False})

        Returns:
            VariableString
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_variable_value(self, name):
        """
        Can only access the design variables, i.e., the local ones
        Cannot access the project (global) variables, which start with $.
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_variable_names(self):
        """
        Returns the local design variables.
        Does not return the project (global) variables, which start with $.
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_variables(self):
        """
        Returns dictionary of local design variables and their values.
        Does not return the project (global) variables and their values,
        whose names start with $.
        
        TODO: Implement using PyAEDT
        """
        pass

    def copy_design_variables(self, source_design):
        """
        does not check that variables are all present
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_excitations(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _evaluate_variable_expression(self, expr, units):
        """
        :type expr: str
        :type units: str
        :return: float
        
        TODO: Implement using PyAEDT
        """
        pass

    def eval_expr(self, expr, units="mm"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def Clear_Field_Clac_Stack(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def clean_up_solutions(self):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssSetup(HfssPropertyObject):
    """
    TODO: Implement using PyAEDT
    """
    prop_tab = "HfssTab"
    passes = make_int_prop("Passes")  # see EditSetup
    n_modes = make_int_prop("Modes")
    pct_refinement = make_float_prop("Percent Refinement")
    delta_f = make_float_prop("Delta F")
    min_freq = make_float_prop("Min Freq")
    basis_order = make_str_prop("Basis Order")

    def __init__(self, design, setup: str):
        """
        :type design: HfssDesign
        :type setup: str

        :COM Scripting Help: "Analysis Setup Module Script Commands"

        Get properties:
            setup.parent._design.GetProperties("HfssTab",'AnalysisSetup:Setup1')
        
        TODO: Implement using PyAEDT
        """
        super(HfssSetup, self).__init__()
        self.parent = design
        # TODO: Store PyAEDT setup object
        # self.prop_holder = design._design
        # self._setup_module = design._setup_module
        # self._reporter = design._reporter
        # self._solutions = design._solutions
        self.name = setup
        self.solution_name = setup + " : LastAdaptive"
        # self.solution_name_pass = setup + " : AdaptivePass"
        # self.prop_server = "AnalysisSetup:" + setup
        self.expression_cache_items = []
        self._ansys_version = self.parent._ansys_version

    def analyze(self, name=None):
        """
        Use:             Solves a single solution setup and all of its frequency sweeps.
        Command:         Right-click a solution setup in the project tree, and then click Analyze
                         on the shortcut menu.
        Syntax:          Analyze(<SetupName>)
        Parameters:      <setupName>
        Return Value:    None
        -----------------------------------------------------

        Will block the until the analysis is completely done.
        Will raise a com_error if analysis is aborted in HFSS.
        
        TODO: Implement using PyAEDT
        """
        pass

    def solve(self, name=None):
        """
        Use:             Performs a blocking simulation.
                         The next script command will not be executed
                         until the simulation is complete.

        Command:         HFSS>Analyze
        Syntax:          Solve <SetupNameArray>
        Return Value:   Type: <int>
                        -1: simulation error
                        0: normal completion
        Parameters:      <SetupNameArray>: Array(<SetupName>, <SetupName>, ...)
           <SetupName>
        Type: <string>
        Name of the solution setup to solve.
        Example:
            return_status = oDesign.Solve Array("Setup1", "Setup2")
        -----------------------------------------------------

        HFSS abort: still returns 0 , since termination by user.
        
        TODO: Implement using PyAEDT
        """
        pass

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
        """
        TODO: Implement using PyAEDT
        """
        pass

    def delete_sweep(self, name):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_sweep_names(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_sweep(self, name=None):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def add_fields_convergence_expr(self, expr, pct_delta, phase=0):
        """
        note: because of hfss idiocy, you must call "commit_convergence_exprs"
        after adding all exprs
        
        TODO: Implement using PyAEDT
        """
        pass

    def commit_convergence_exprs(self):
        """
        note: this will eliminate any convergence expressions not added through this interface
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_convergence(self, variation="", pre_fn_args=[], overwrite=True):
        """
        Returns converge as a dataframe
            Variation should be in the form
            variation = "scale_factor='1.2001'" ...
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_mesh_stats(self, variation=""):
        """
        variation should be in the form
        variation = "scale_factor='1.2001'" ...
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_profile(self, variation=""):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_fields(self):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssDMSetup(HfssSetup):
    """
    Driven modal setup
    
    TODO: Implement using PyAEDT
    """
    solution_freq = make_float_prop("Solution Freq")
    delta_s = make_float_prop("Delta S")
    solver_type = make_str_prop("Solver Type")

    def setup_link(self, linked_setup):
        """
        type: linked_setup <HfssSetup>
        
        TODO: Implement using PyAEDT
        """
        pass

    def _map_variables_by_name(self):
        """
        does not check that variables are all present
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_solutions(self):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssDTSetup(HfssDMSetup):
    """
    TODO: Implement using PyAEDT
    """
    def get_solutions(self):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssEMSetup(HfssSetup):
    """
    Eigenmode setup
    
    TODO: Implement using PyAEDT
    """
    min_freq = make_float_prop("Min Freq")
    n_modes = make_int_prop("Modes")
    delta_f = make_float_prop("Delta F")

    def get_solutions(self):
        """
        TODO: Implement using PyAEDT
        """
        pass


class AnsysQ3DSetup(HfssSetup):
    """
    Q3D setup
    
    TODO: Implement using PyAEDT
    """
    prop_tab = "CG"
    max_pass = make_int_prop("Max. Number of Passes")
    min_pass = make_int_prop("Min. Number of Passes")
    pct_error = make_int_prop("Percent Error")
    frequency = make_str_prop("Adaptive Freq", "General")  # e.g., '5GHz'
    n_modes = 0  # type: ignore  # for compatibility with eigenmode

    def get_frequency_Hz(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_solutions(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_convergence(self, variation="", pre_fn_args=None, overwrite=True):
        """
        Returns df
                    # Triangle   Delta %
            Pass
            1            164       NaN
        
        TODO: Implement using PyAEDT
        """
        if pre_fn_args is None:
            pre_fn_args = ["CG"]
        pass

    def get_matrix(
        self,
        variation="",
        pass_number=0,
        frequency=None,
        MatrixType="Maxwell",
        solution_kind="LastAdaptive",  # AdaptivePass
        ACPlusDCResistance=False,
        soln_type="C",
    ):
        """
        Arguments:
        -----------
            variation: an empty string returns nominal variation.
                        Otherwise need the list
            frequency: in Hz
            soln_type = "C", "AC RL" and "DC RL"
            solution_kind = 'LastAdaptive' # AdaptivePass
        Internals:
        -----------
            Uses self.solution_name  = Setup1 : LastAdaptive

        Returns:
        ---------------------
            df_cmat, user_units, (df_cond, units_cond), design_variation
        
        TODO: Implement using PyAEDT
        """
        pass

    @staticmethod
    def _readin_Q3D_matrix(path: str):
        """
        Read in the txt file created from q3d export
        and output the capacitance matrix

        When exporting pick "save as type: data table"

        See Zlatko

        RETURNS: Dataframe

        Example file:
        ```
        DesignVariation:$BBoxL='650um' $boxH='750um' $boxL='2mm' $QubitGap='30um' \
                        $QubitH='90um' \$QubitL='450um' Lj_1='13nH'
        Setup1:LastAdaptive
        Problem Type:C
        C Units:farad, G Units:mSie
        Reduce Matrix:Original
        Frequency: 5.5E+09 Hz

        Capacitance Matrix
            ground_plane	Q1_bus_Q0_connector_pad	Q1_bus_Q2_connector_pad	Q1_pad_bot	Q1_pad_top1	Q1_readout_connector_pad
        ground_plane	2.8829E-13	-3.254E-14	-3.1978E-14	-4.0063E-14	-4.3842E-14	-3.0053E-14
        Q1_bus_Q0_connector_pad	-3.254E-14	4.7257E-14	-2.2765E-16	-1.269E-14	-1.3351E-15	-1.451E-16
        Q1_bus_Q2_connector_pad	-3.1978E-14	-2.2765E-16	4.5327E-14	-1.218E-15	-1.1552E-14	-5.0414E-17
        Q1_pad_bot	-4.0063E-14	-1.269E-14	-1.218E-15	9.5831E-14	-3.2415E-14	-8.3665E-15
        Q1_pad_top1	-4.3842E-14	-1.3351E-15	-1.1552E-14	-3.2415E-14	9.132E-14	-1.0199E-15
        Q1_readout_connector_pad	-3.0053E-14	-1.451E-16	-5.0414E-17	-8.3665E-15	-1.0199E-15	3.9884E-14

        Conductance Matrix
            ground_plane	Q1_bus_Q0_connector_pad	Q1_bus_Q2_connector_pad	Q1_pad_bot	Q1_pad_top1	Q1_readout_connector_pad
        ground_plane	0	0	0	0	0	0
        Q1_bus_Q0_connector_pad	0	0	0	0	0	0
        Q1_bus_Q2_connector_pad	0	0	0	0	0	0
        Q1_pad_bot	0	0	0	0	0	0
        Q1_pad_top1	0	0	0	0	0	0
        Q1_readout_connector_pad	0	0	0	0	0	0
        ```
        
        TODO: This is a static method that parses files - may not need PyAEDT changes
        """
        pass

    @staticmethod
    def load_q3d_matrix(path, user_units="fF"):
        """
        Load Q3D capacitance file exported as Maxwell matrix.
        Exports also conductance conductance.
        Units are read in automatically and converted to user units.

        Arguments:
            path {[str or Path]} -- [path to file text with matrix]

        Returns:
            df_cmat, user_units, (df_cond, units_cond), design_variation

            dataframes: df_cmat, df_cond
        
        TODO: This is a static method that parses files - may not need PyAEDT changes
        """
        pass


class HfssDesignSolutions(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, setup, solutions):
        """
        :type setup: HfssSetup
        
        TODO: Implement using PyAEDT
        """
        super(HfssDesignSolutions, self).__init__()
        self.parent = setup
        # TODO: Store PyAEDT solutions object
        # self._solutions = solutions
        self._ansys_version = self.parent._ansys_version

    def get_valid_solution_list(self):
        """
        Gets all available solution names that exist in a design.
        Return example:
           ('Setup1 : AdaptivePass', 'Setup1 : LastAdaptive')
        
        TODO: Implement using PyAEDT
        """
        pass

    def list_variations(self, setup_name: Optional[str] = None):
        """
        Get a list of solved variations.

        Args:
            setup_name(str) : Example name ("Setup1 : LastAdaptive") Defaults to None.

        Returns:
             An array of strings corresponding to solved variations.

             .. code-block:: python

                ("Cj='2fF' Lj='12nH'",
                "Cj='2fF' Lj='12.5nH'",
                "Cj='2fF' Lj='13nH'",
                "Cj='2fF' Lj='13.5nH'",
                "Cj='2fF' Lj='14nH'")
        
        TODO: Implement using PyAEDT
        """
        pass


class HfssEMDesignSolutions(HfssDesignSolutions):
    """
    TODO: Implement using PyAEDT
    """
    def eigenmodes(self, lv=""):
        """
        Returns the eigenmode data of freq and kappa/2p
        
        TODO: Implement using PyAEDT
        """
        pass

    def set_mode(self, n, phase=0, FieldType="EigenStoredEnergy"):
        """
        Indicates which source excitations should be used for fields post processing.
        HFSS>Fields>Edit Sources

        Mode count starts at 1

        Amplitude is set to 1

        No error is thrown if a number exceeding number of modes is set

            FieldType -- EigenStoredEnergy or EigenPeakElecticField
        
        TODO: Implement using PyAEDT
        """
        pass

    def has_fields(self, variation_string=None):
        """
        Determine if fields exist for a particular solution.

        variation_string : str | None
            This must the string that describes the variation in hFSS, not 0 or 1, but
            the string of variables, such as
                "Cj='2fF' Lj='12.75nH'"
            If None, gets the nominal variation
        
        TODO: Implement using PyAEDT
        """
        pass

    def create_report(self, plot_name, xcomp, ycomp, params, pass_name="LastAdaptive"):
        """
        pass_name: AdaptivePass, LastAdaptive

        Example
        -------
        Example plot for a single variation all pass converge of mode freq

        .. code-block:: python

            ycomp = [f"re(Mode({i}))" for i in range(1,1+epr_hfss.n_modes)]
            params = ["Pass:=", ["All"]]+variation
            setup.create_report("Freq. vs. pass", "Pass", ycomp, params, pass_name='AdaptivePass')
        
        TODO: Implement using PyAEDT
        """
        pass


class HfssDMDesignSolutions(HfssDesignSolutions):
    """
    TODO: Implement using PyAEDT
    """
    pass


class HfssDTDesignSolutions(HfssDesignSolutions):
    """
    TODO: Implement using PyAEDT
    """
    pass


class HfssQ3DDesignSolutions(HfssDesignSolutions):
    """
    TODO: Implement using PyAEDT
    """
    pass


class HfssFrequencySweep(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    prop_tab = "HfssTab"
    start_freq = make_float_prop("Start")
    stop_freq = make_float_prop("Stop")
    step_size = make_float_prop("Step Size")
    count = make_float_prop("Count")
    sweep_type = make_str_prop("Type")

    def __init__(self, setup, name):
        """
        :type setup: HfssSetup
        :type name: str
        
        TODO: Implement using PyAEDT
        """
        super(HfssFrequencySweep, self).__init__()
        self.parent = setup
        self.name = name
        self.solution_name = self.parent.name + " : " + name
        # self.prop_holder = self.parent.prop_holder
        # self.prop_server = self.parent.prop_server + ":" + name
        self._ansys_version = self.parent._ansys_version

    def analyze_sweep(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_network_data(self, formats):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def create_report(self, name, expr):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_report_arrays(self, expr):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssReport(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, design, name):
        """
        :type design: HfssDesign
        :type name: str
        
        TODO: Implement using PyAEDT
        """
        super(HfssReport, self).__init__()
        self.parent_design = design
        self.name = name

    def export_to_file(self, filename):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_arrays(self):
        """
        TODO: Implement using PyAEDT
        """
        pass


class Optimetrics(COMWrapper):
    """
    Optimetrics script commands executed by the "Optimetrics" module.

    Example use:

    .. code-block:: python

        opti = Optimetrics(pinfo.design)
        names = opti.get_setup_names()
        print('Names of optimetrics: ', names)
        opti.solve_setup(names[0])

    Note that running optimetrics requires the license for Optimetrics by Ansys.
    
    TODO: Implement using PyAEDT
    """

    def __init__(self, design):
        """
        TODO: Implement using PyAEDT
        """
        super(Optimetrics, self).__init__()

        self.design = design  # parent
        # TODO: Store PyAEDT optimetrics module
        # self._optimetrics = self.design._optimetrics  # <COMObject GetModule>
        self.setup_names = None

    def get_setup_names(self):
        """
        Return list of Optimetrics setup names
        
        TODO: Implement using PyAEDT
        """
        pass

    def solve_setup(self, setup_name: str):
        """
        Solves the specified Optimetrics setup.
        Corresponds to:  Right-click the setup in the project tree, and then click
        Analyze on the shortcut menu.

        setup_name (str) : name of setup, should be in get_setup_names

        Blocks execution until ready to use.

        Note that this requires the license for Optimetrics by Ansys.
        
        TODO: Implement using PyAEDT
        """
        pass

    def create_setup(
        self,
        variable,
        swp_params,
        name="ParametricSetup1",
        swp_type="linear_step",
        setup_name=None,
        save_fields=True,
        copy_mesh=True,
        solve_with_copied_mesh_only=True,
        setup_type="parametric",
    ):
        """
        Inserts a new parametric setup of one variable. Either with sweep
        definition or from file.

        *Synchronized* sweeps (more than one variable changing at once)
        can be implemented by giving a list of variables to ``variable``
        and corresponding lists to ``swp_params`` and ``swp_type``.
        The lengths of the sweep types should match (excluding single value).

        Corresponds to ui access:
        Right-click the Optimetrics folder in the project tree, and then click
        Add> Parametric on the shortcut menu.

        Ansys provides six sweep definitions types specified using the swp_type
        variable.

        Sweep type definitions:

        - 'single_value'
            Specify a single value for the sweep definition.
        - 'linear_step'
            Specify a linear range of values with a constant step size.
        - 'linear_count'
            Specify a linear range of values and the number, or count of points
            within this range.
        - 'decade_count'
            Specify a logarithmic (base 10) series of values, and the number of
            values to calculate in each decade.
        - 'octave_count'
            Specify a logarithmic (base 2) series of values, and the number of
            values to calculate in each octave.
        - 'exponential_count'
            Specify an exponential (base e) series of values, and the number of
            values to calculate.

        For swp_type='single_value' swp_params is the single value.

        For swp_type='linear_step' swp_params is start, stop, step:
            swp_params = ("12.8nH", "13.6nH", "0.2nH")

        All other types swp_params is start, stop, count:
            swp_params = ("12.8nH", "13.6nH", 4)
            The definition of count varies amongst the available types.

        For Decade count and Octave count, the Count value specifies the number
        of points to calculate in every decade or octave. For Exponential count,
        the Count value is the total number of points. The total number of
        points includes the start and stop values.

        For parametric from file, setup_type='parametric_file', pass in a file
        name and path to swp_params like "C:\\test.csv" or "C:\\test.txt" for
        example.

        Example csv formatting:
        *,Lj_qubit
        1,12.2nH
        2,9.7nH
        3,10.2nH

        See Ansys documentation for additional formatting instructions.
        
        TODO: Implement using PyAEDT
        """
        pass


class HfssModeler(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, design, modeler, boundaries, mesh):
        """
        :type design: HfssDesign
        
        TODO: Implement using PyAEDT
        """
        super(HfssModeler, self).__init__()
        self.parent = design
        # TODO: Store PyAEDT modeler, boundaries, mesh objects
        # self._modeler = modeler
        # self._boundaries = boundaries
        # self._mesh = mesh  # Mesh module

    def set_units(self, units, rescale=True):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_units(self):
        """
        Get the model units.
        Return Value:    A string contains current model units.
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_all_properties(self, obj_name, PropTab="Geometry3DAttributeTab"):
        """
        Get all properties for modeler PropTab, PropServer
        
        TODO: Implement using PyAEDT
        """
        pass

    def _attributes_array(
        self,
        name=None,
        nonmodel=False,
        wireframe=False,
        color=None,
        transparency=0.9,
        material=None,  # str
        solve_inside=None,  # bool
        coordinate_system="Global",
    ):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _selections_array(self, *names):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def mesh_length(self, name_mesh, objects: list, MaxLength="0.1mm", **kwargs):
        """
        "RefineInside:="	, False,
        "Enabled:="		, True,
        "RestrictElem:="	, False,
        "NumMaxElem:="		, "1000",
        "RestrictLength:="	, True,
        "MaxLength:="		, "0.1mm"

        Example use:
        modeler.assign_mesh_length('mesh2', ["Q1_mesh"], MaxLength=0.1)
        
        TODO: Implement using PyAEDT
        """
        pass

    def mesh_reassign(self, name_mesh, objects: list):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def mesh_get_names(self, kind="Length Based"):
        """
        "Length Based", "Skin Depth Based", ...
        
        TODO: Implement using PyAEDT
        """
        pass

    def mesh_get_all_props(self, mesh_name):
        """
        # TODO: make mesh its own class with properties
        
        TODO: Implement using PyAEDT
        """
        pass

    def draw_box_corner(self, pos, size, **kwargs):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def draw_box_center(self, pos, size, **kwargs):
        """
        Creates a 3-D box centered at pos [x0, y0, z0], with width
        size [xwidth, ywidth, zwidth] along each respective direction.

        Args:
            pos (list): Coordinates of center of box, [x0, y0, z0]
            size (list): Width of box along each direction, [xwidth, ywidth, zwidth]
        
        TODO: Implement using PyAEDT
        """
        pass

    def draw_polyline(self, points, closed=True, **kwargs):
        """
        Draws a closed or open polyline.
        If closed = True, then will make into a sheet.
        points : need to be in the correct units

        For optional arguments, see _attributes_array; these include:
        ```
            nonmodel=False,
            wireframe=False,
            color=None,
            transparency=0.9,
            material=None,  # str
            solve_inside=None,  # bool
            coordinate_system="Global"
        ```
        
        TODO: Implement using PyAEDT
        """
        pass

    def draw_rect_corner(self, pos, x_size=0, y_size=0, z_size=0, **kwargs):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def draw_rect_center(self, pos, x_size=0, y_size=0, z_size=0, **kwargs):
        """
        Creates a rectangle centered at pos [x0, y0, z0].
        It is assumed that the rectangle lies parallel to the xy, yz, or xz plane.
        User inputs 2 of 3 of the following: x_size, y_size, and z_size
        depending on how the rectangle is oriented.

        Args:
            pos (list): Coordinates of rectangle center, [x0, y0, z0]
            x_size (int, optional): Width along the x direction. Defaults to 0.
            y_size (int, optional):  Width along the y direction. Defaults to 0.
            z_size (int, optional):  Width along the z direction]. Defaults to 0.
        
        TODO: Implement using PyAEDT
        """
        pass

    def draw_cylinder(self, pos, radius, height, axis, **kwargs):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def draw_cylinder_center(self, pos, radius, height, axis, **kwargs):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def draw_wirebond(
        self,
        pos,
        ori,
        width,
        height="0.1mm",
        z=0,
        wire_diameter="0.02mm",
        NumSides=6,
        **kwargs,
    ):
        """
        Args:
            pos: 2D position vector  (specify center point)
            ori: should be normed
            z: z position

        # TODO create Wirebond class
        position is the origin of one point
        ori is the orientation vector, which gets normalized
        
        TODO: Implement using PyAEDT
        """
        pass

    def draw_region(
        self,
        Padding,
        PaddingType="Percentage Offset",
        name="Region",
        material='"vacuum"',
    ):
        """
        PaddingType : 'Absolute Offset', "Percentage Offset"
        
        TODO: Implement using PyAEDT
        """
        pass

    def unite(self, names, keep_originals=False):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def intersect(self, names, keep_originals=False):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def translate(self, name, vector):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_boundary_assignment(self, boundary_name: str):
        """
        Gets a list of face IDs associated with the given boundary or excitation assignment.
        Gets an object name corresponding to the input face id. Returns the name of the corresponding object name.
        
        TODO: Implement using PyAEDT
        """
        pass

    def append_PerfE_assignment(self, boundary_name: str, object_names: list):
        """
        This will create a new boundary if need, and will
        otherwise append given names to an existing boundary
        
        TODO: Implement using PyAEDT
        """
        pass

    def append_mesh(self, mesh_name: str, object_names: list, old_objs: list, **kwargs):
        """
        This will create a new boundary if need, and will
        otherwise append given names to an existing boundary
        old_obj = circ._mesh_assign
        
        TODO: Implement using PyAEDT
        """
        pass

    def assign_perfect_E(self, obj: List[str], name: str = "PerfE"):
        """
        Assign a boundary condition to a list of objects.

        Arg:
            objs (List[str]): Takes a name of an object or a list of object names.
            name(str): If `name` is not specified `PerfE` is appended to object name for the name.
        
        TODO: Implement using PyAEDT
        """
        pass

    def _make_lumped_rlc(self, r, inductance, c, start, end, obj_arr, name="LumpRLC"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _make_lumped_port(self, start, end, obj_arr, z0="50ohm", name="LumpPort"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_face_ids(self, obj):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_object_name_by_face_id(self, ID: str):
        """
        Gets an object name corresponding to the input face id.
        
        TODO: Implement using PyAEDT
        """
        pass

    def get_vertex_ids(self, obj):
        """
        Get the vertex IDs of given an object name
        oVertexIDs = oEditor.GetVertexIDsFromObject("Box1")
        
        TODO: Implement using PyAEDT
        """
        pass

    def eval_expr(self, expr, units="mm"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def get_objects_in_group(self, group):
        """
        Use:              Returns the objects for the specified group.
        Return Value:    The objects in the group.
        Parameters:      <groupName>  Type: <string>
        One of  <materialName>, <assignmentName>, "Non Model",
                "Solids", "Unclassi­fied", "Sheets", "Lines"
        
        TODO: Implement using PyAEDT
        """
        pass

    def set_working_coordinate_system(self, cs_name="Global"):
        """
        Use:                   Sets the working coordinate system.
        Command:         Modeler>Coordinate System>Set Working CS
        
        TODO: Implement using PyAEDT
        """
        pass

    def create_relative_coorinate_system_both(
        self,
        cs_name,
        origin=["0um", "0um", "0um"],
        XAxisVec=["1um", "0um", "0um"],
        YAxisVec=["0um", "1um", "0um"],
    ):
        """
        Use:     Creates a relative coordinate system. Only the    Name attribute of the <AttributesArray> parameter is supported.
        Command: Modeler>Coordinate System>Create>Relative CS->Offset
        Modeler>Coordinate System>Create>Relative CS->Rotated
        Modeler>Coordinate System>Create>Relative CS->Both

        Current coordinate system is set right after this.

        cs_name : name of coord. sys
            If the name already exists, then a new coordinate system with _1 is created.

        origin, XAxisVec, YAxisVec: 3-vectors
            You can also pass in params such as origin = [0,1,0] rather than ["0um","1um","0um"], but these will be interpreted in default units, so it is safer to be explicit. Explicit over implicit.
        
        TODO: Implement using PyAEDT
        """
        pass

    def subtract(self, blank_name, tool_names, keep_originals=False):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _fillet(self, radius, vertex_index, obj):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _fillet_edges(self, radius, edge_index, obj):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _fillets(self, radius, vertices, obj):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _sweep_along_path(self, to_sweep, path_obj):
        """
        Adds thickness to path_obj by extending to a new dimension.
        to_sweep acts as a putty knife that determines the thickness.

        Args:
            to_sweep (polyline): Small polyline running perpendicular to path_obj
                                    whose length is the desired resulting thickness
            path_obj (polyline): Original polyline; want to broaden this
        
        TODO: Implement using PyAEDT
        """
        pass

    def sweep_along_vector(self, names, vector):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def rename_obj(self, obj, name):
        """
        TODO: Implement using PyAEDT
        """
        pass


class ModelEntity(str, HfssPropertyObject):
    """
    TODO: Implement using PyAEDT
    """
    prop_tab = "Geometry3DCmdTab"
    model_command = None
    transparency = make_float_prop(
        "Transparent", prop_tab="Geometry3DAttributeTab", prop_server=lambda self: self
    )
    material = make_str_prop(
        "Material", prop_tab="Geometry3DAttributeTab", prop_server=lambda self: self
    )
    wireframe = make_float_prop(
        "Display Wireframe",
        prop_tab="Geometry3DAttributeTab",
        prop_server=lambda self: self,
    )
    coordinate_system = make_str_prop("Coordinate System")

    def __new__(self, val, *args, **kwargs):
        return str.__new__(self, val)

    def __init__(self, val, modeler):
        """
        :type val: str
        :type modeler: HfssModeler
        
        TODO: Implement using PyAEDT
        """
        super(
            ModelEntity, self
        ).__init__()  # val) #Comment out keyword to match arguments
        self.modeler = modeler
        # self.prop_server = self + ":" + self.model_command + ":1"


class Box(ModelEntity):
    """
    TODO: Implement using PyAEDT
    """
    model_command = "CreateBox"
    position = make_float_prop("Position")
    x_size = make_float_prop("XSize")
    y_size = make_float_prop("YSize")
    z_size = make_float_prop("ZSize")

    def __init__(self, name, modeler, corner, size):
        """
        :type name: str
        :type modeler: HfssModeler
        :type corner: [(VariableString, VariableString, VariableString)]
        :param size: [(VariableString, VariableString, VariableString)]
        
        TODO: Implement using PyAEDT
        """
        super(Box, self).__init__(name, modeler)
        self.modeler = modeler
        # self.prop_holder = modeler._modeler
        self.corner = corner
        self.size = size
        self.center = [c + s / 2 for c, s in zip(corner, size)]  # type: ignore
        # faces = modeler.get_face_ids(self)
        # self.z_back_face, self.z_front_face = faces[0], faces[1]
        # self.y_back_face, self.y_front_face = faces[2], faces[4]
        # self.x_back_face, self.x_front_face = faces[3], faces[5]


class Rect(ModelEntity):
    """
    TODO: Implement using PyAEDT
    """
    model_command = "CreateRectangle"

    # TODO: Add a rotated rectangle object.
    # Will need to first create rect, then apply rotate operation.

    def __init__(self, name, modeler, corner, size):
        """
        TODO: Implement using PyAEDT
        """
        super(Rect, self).__init__(name, modeler)
        # self.prop_holder = modeler._modeler
        self.corner = corner
        self.size = size
        self.center = [c + s / 2 if s else c for c, s in zip(corner, size)]  # type: ignore

    def make_center_line(self, axis):
        """
        Returns `start` and `end` list of 3 coordinates
        
        TODO: Implement using PyAEDT
        """
        pass

    def make_rlc_boundary(self, axis, r=0, inductance=0, c=0, name="LumpRLC"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def make_lumped_port(self, axis, z0="50ohm", name="LumpPort"):
        """
        TODO: Implement using PyAEDT
        """
        pass


class Polyline(ModelEntity):
    """
    Assume closed polyline, which creates a polygon.
    
    TODO: Implement using PyAEDT
    """
    model_command = "CreatePolyline"

    def __init__(self, name, modeler, points=None):
        """
        TODO: Implement using PyAEDT
        """
        super(Polyline, self).__init__(name, modeler)
        # self.prop_holder = modeler._modeler
        if points is not None:
            self.points = points
            self.n_points = len(points)
        else:
            pass
            # TODO: points = collection of points

    #        axis = find_orth_axis()

    # TODO: find the plane of the polyline for now, assume Z
    #    def find_orth_axis():
    #        X, Y, Z = (True, True, True)
    #        for point in points:
    #            X =

    def unite(self, list_other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def make_center_line(self, axis):  # Expects to act on a rectangle...
        """
        first : find center and size
        
        TODO: Implement using PyAEDT
        """
        pass

    def make_rlc_boundary(self, axis, r=0, inductance=0, c=0, name="LumpRLC"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def fillet(self, radius, vertex_index):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def vertices(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def rename(self, new_name):
        """
        Warning: The increment_name only works if the sheet has not been stracted or used as a tool elsewhere.
        These names are not checked; they require modifying get_objects_in_group.
        
        TODO: Implement using PyAEDT
        """
        pass


class OpenPolyline(ModelEntity):  # Assume closed polyline
    """
    TODO: Implement using PyAEDT
    """
    model_command = "CreatePolyline"
    show_direction = make_prop(
        "Show Direction",
        prop_tab="Geometry3DAttributeTab",
        prop_server=lambda self: self,
    )

    def __init__(self, name, modeler, points=None):
        """
        TODO: Implement using PyAEDT
        """
        super(OpenPolyline, self).__init__(name, modeler)
        # self.prop_holder = modeler._modeler
        if points is not None:
            self.points = points
            self.n_points = len(points)
        else:
            pass

    #        axis = find_orth_axis()

    # TODO: find the plane of the polyline for now, assume Z
    #    def find_orth_axis():
    #        X, Y, Z = (True, True, True)
    #        for point in points:
    #            X =

    def vertices(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def fillet(self, radius, vertex_index):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def fillets(self, radius, do_not_fillet=[]):
        """
        do_not_fillet : Index list of vertices to not fillete
        
        TODO: Implement using PyAEDT
        """
        pass

    def sweep_along_path(self, to_sweep):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def rename(self, new_name):
        """
        Warning: The  increment_name only works if the sheet has not been stracted or used as a tool elsewher.
        These names are not checked - They require modifying get_objects_in_group
        
        TODO: Implement using PyAEDT
        """
        pass

    def copy(self, new_name):
        """
        TODO: Implement using PyAEDT
        """
        pass


class HfssFieldsCalc(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, setup):
        """
        :type setup: HfssSetup
        
        TODO: Implement using PyAEDT
        """
        self.setup = setup
        super(HfssFieldsCalc, self).__init__()
        self.parent = setup
        # TODO: Initialize field calculation objects
        # self.Mag_E = NamedCalcObject("Mag_E", setup)
        # self.Mag_H = NamedCalcObject("Mag_H", setup)
        # self.Mag_Jsurf = NamedCalcObject("Mag_Jsurf", setup)
        # self.Mag_Jvol = NamedCalcObject("Mag_Jvol", setup)
        # self.Vector_E = NamedCalcObject("Vector_E", setup)
        # self.Vector_H = NamedCalcObject("Vector_H", setup)
        # self.Vector_Jsurf = NamedCalcObject("Vector_Jsurf", setup)
        # self.Vector_Jvol = NamedCalcObject("Vector_Jvol", setup)
        # self.ComplexMag_E = NamedCalcObject("ComplexMag_E", setup)
        # self.ComplexMag_H = NamedCalcObject("ComplexMag_H", setup)
        # self.ComplexMag_Jsurf = NamedCalcObject("ComplexMag_Jsurf", setup)
        # self.ComplexMag_Jvol = NamedCalcObject("ComplexMag_Jvol", setup)
        # self.P_J = NamedCalcObject("P_J", setup)

        self.named_expression = {}  # dictionary to hold additional named expressions

    def clear_named_expressions(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def declare_named_expression(self, name):
        """
        If a named expression has been created in the fields calculator, this
        function can be called to initialize the name to work with the fields object
        
        TODO: Implement using PyAEDT
        """
        pass

    def use_named_expression(self, name):
        """
        Expression can be used to access dictionary of named expressions,
        Alternately user can access dictionary directly via named_expression()
        
        TODO: Implement using PyAEDT
        """
        pass


class CalcObject(COMWrapper):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, stack, setup):
        """
        :type stack: [(str, str)]
        :type setup: HfssSetup
        
        TODO: Implement using PyAEDT
        """
        super(CalcObject, self).__init__()
        self.stack = stack
        self.setup = setup
        # self.calc_module = setup.parent._fields_calc

    def _bin_op(self, other, op):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _unary_op(self, op):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __add__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __radd__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __sub__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __rsub__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __mul__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __rmul__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __div__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __rdiv__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __pow__(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def dot(self, other):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __neg__(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __abs__(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def __mag__(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def mag(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def smooth(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def conj(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def scalar_x(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def scalar_y(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def scalar_z(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def norm_2(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def real(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def imag(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def complexmag(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _integrate(self, name, type):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def _maximum(self, name, type):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def getQty(self, name):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def integrate_line(self, name):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def normal2surface(self, name):
        """
        return the part normal to surface.
        Complex Vector.
        
        TODO: Implement using PyAEDT
        """
        pass

    def tangent2surface(self, name):
        """
        return the part tangent to surface.
        Complex Vector.
        
        TODO: Implement using PyAEDT
        """
        pass

    def integrate_line_tangent(self, name):
        """
        integrate line tangent to vector expression \n
        name = of line to integrate over
        
        TODO: Implement using PyAEDT
        """
        pass

    def line_tangent_coor(self, name, coordinate):
        """
        integrate line tangent to vector expression \n
        name = of line to integrate over
        
        TODO: Implement using PyAEDT
        """
        pass

    def integrate_surf(self, name="AllObjects"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def integrate_vol(self, name="AllObjects"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def maximum_vol(self, name="AllObjects"):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def times_eps(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def times_mu(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def write_stack(self):
        """
        TODO: Implement using PyAEDT
        """
        pass

    def save_as(self, name):
        """
        if the object already exists, try clearing your
        named expressions first with fields.clear_named_expressions
        
        TODO: Implement using PyAEDT
        """
        pass

    def evaluate(self, phase=0, lv=None, print_debug=False):  # , n_mode=1):
        """
        TODO: Implement using PyAEDT
        """
        pass


class NamedCalcObject(CalcObject):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, name, setup):
        """
        TODO: Implement using PyAEDT
        """
        self.name = name
        stack = [("CopyNamedExprToStack", name)]
        super(NamedCalcObject, self).__init__(stack, setup)


class ConstantCalcObject(CalcObject):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, num, setup):
        """
        TODO: Implement using PyAEDT
        """
        stack = [("EnterScalar", num)]
        super(ConstantCalcObject, self).__init__(stack, setup)


class ConstantVecCalcObject(CalcObject):
    """
    TODO: Implement using PyAEDT
    """
    def __init__(self, vec, setup):
        """
        TODO: Implement using PyAEDT
        """
        stack = [("EnterVector", vec)]
        super(ConstantVecCalcObject, self).__init__(stack, setup)


def get_active_project():
    """
    If you see the error:
    "The requested operation requires elevation."
    then you need to run your python as an admin.
    
    TODO: Implement using PyAEDT
    """
    import os

    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        # Windows-specific check
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore
        except (AttributeError, OSError):
            is_admin = False
    if not is_admin:
        print(
            "\033[93m WARNING: you are not running as an admin! \
            You need to run as an admin. You will probably get an error next.\
                 \033[0m"
        )

    # TODO: Initialize PyAEDT and get active project
    # app = HfssApp()
    # desktop = app.get_app_desktop()
    # return desktop.get_active_project()
    pass


def get_active_design():
    """
    TODO: Implement using PyAEDT
    """
    # project = get_active_project()
    # return project.get_active_design()
    pass


def get_report_arrays(name: str):
    """
    TODO: Implement using PyAEDT
    """
    # d = get_active_design()
    # r = HfssReport(d, name)
    # return r.get_arrays()
    pass


def load_ansys_project(
    proj_name: str, project_path: Optional[str] = None, extension: str = ".aedt"
):
    """
    Utility function to load an Ansys project.

    Args:
        proj_name : None  --> get active. (make sure 2 run as admin)
        extension : `aedt` is for 2016 version and newer
    
    TODO: Implement using PyAEDT
    """
    if project_path:
        # convert slashes correctly for system
        project_path_obj = Path(project_path)

        # Checks
        assert (
            project_path_obj.is_dir()
        ), "ERROR! project_path is not a valid directory \N{loudly crying face}.\
            Check the path, and especially \\ characters."

        project_file = Path(project_path_obj, proj_name).with_suffix(extension)

        if project_file.is_file():
            logger.info("\tFile path to HFSS project found.")
        else:
            raise Exception(
                "ERROR! Valid directory, but invalid project filename. \N{loudly crying face} Not found!\
                     Please check your filename.\n%s\n"
                % project_file
            )

        lock_file = project_file.parent / ".lock"
        if lock_file.is_file():
            logger.warning(
                "\t\tFile is locked. \N{fearful face} If connection fails, delete the .lock file."
            )

    # TODO: Initialize PyAEDT and load project
    # app = HfssApp()
    # logger.info("\tOpened Ansys App")
    #
    # desktop = app.get_app_desktop()
    # logger.info(f"\tOpened Ansys Desktop v{desktop.get_version()}")
    # # logger.debug(f"\tOpen projects: {desktop.get_project_names()}")
    #
    # if proj_name is not None:
    #     if proj_name in desktop.get_project_names():
    #         desktop.set_active_project(proj_name)
    #         project = desktop.get_active_project()
    #     else:
    #         project = desktop.open_project(str(project_path))
    # else:
    #     projects_in_app = desktop.get_projects()
    #     if projects_in_app:
    #         project = desktop.get_active_project()
    #     else:
    #         project = None
    #
    # if project:
    #     logger.info(
    #         f"\tOpened Ansys Project\n\tFolder:    {project.get_path()}\n\tProject:   {project.name}"
    #     )
    # else:
    #     logger.info(f"\tAnsys Project was not found.\n\t Project is None.")
    #
    # return app, desktop, project
    pass
