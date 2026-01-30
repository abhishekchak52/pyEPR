"""
pyEPR.ansys package.

Dispatches to COM backend (ansys_com) or pyaedt backend based on PYEPR_USE_PYAEDT.
Default (unset) = COM; when set truthy = pyaedt if available.
"""

from . import _backend

if _backend.get_backend() == "com":
    from .. import ansys_com
    for _name in dir(ansys_com):
        if not _name.startswith("_"):
            globals()[_name] = getattr(ansys_com, _name)
    globals()["get_available_backends"] = _backend.get_available_backends
    globals()["get_backend"] = _backend.get_backend
    globals()["set_backend"] = _backend.set_backend
    globals()["using_pyaedt"] = _backend.using_pyaedt
    globals()["using_com"] = _backend.using_com
    _all = [x for x in dir(ansys_com) if not x.startswith("_")]
    _all.extend(["get_available_backends", "get_backend", "set_backend", "using_pyaedt", "using_com"])
    __all__ = sorted(set(_all))
else:
    from ._backend import (
        get_available_backends,
        get_backend,
        set_backend,
        using_com,
        using_pyaedt,
    )
    from ._units import (
        BASIS_ORDER,
        LENGTH_UNIT,
        LENGTH_UNIT_ASSUMED,
        Q,
        ureg,
        extract_value_dim,
        extract_value_unit,
        fix_units,
        increment_name,
        parse_entry,
        parse_units,
        parse_units_user,
        simplify_arith_expr,
        unparse_units,
        var,
        VariableString,
    )
    from ._wrapper import (
        COMWrapper,
        HfssPropertyObject,
        _add_release_fn,
        _unwrap_aedt_handle,
        make_float_prop,
        make_int_prop,
        make_prop,
        make_str_prop,
        release,
        set_property,
    )
    from .hfss_app import HfssApp
    from .hfss_desktop import HfssDesktop
    from .hfss_project import HfssProject
    from .hfss_design import HfssDesign
    from .hfss_setup import (
        AnsysQ3DSetup,
        HfssDMSetup,
        HfssDTSetup,
        HfssEMSetup,
        HfssSetup,
    )
    from .hfss_design_solutions import (
        HfssDMDesignSolutions,
        HfssDTDesignSolutions,
        HfssEMDesignSolutions,
        HfssDesignSolutions,
        HfssQ3DDesignSolutions,
    )
    from .hfss_frequency_sweep import HfssFrequencySweep
    from .hfss_report import HfssReport
    from .optimetrics import Optimetrics
    from .hfss_modeler import HfssModeler
    from .model_entity import Box, ModelEntity, OpenPolyline, Polyline, Rect
    from .hfss_fields_calc import (
        CalcObject,
        ConstantCalcObject,
        ConstantVecCalcObject,
        HfssFieldsCalc,
        NamedCalcObject,
    )
    from .load import (
        get_active_design,
        get_active_project,
        get_report_arrays,
        load_ansys_project,
    )
    __all__ = [
        "get_available_backends", "get_backend", "set_backend", "using_pyaedt", "using_com",
        "BASIS_ORDER", "LENGTH_UNIT", "LENGTH_UNIT_ASSUMED", "ureg", "Q",
        "simplify_arith_expr", "increment_name", "extract_value_unit", "extract_value_dim",
        "parse_entry", "fix_units", "parse_units", "unparse_units", "parse_units_user",
        "VariableString", "var",
        "COMWrapper", "HfssPropertyObject", "_unwrap_aedt_handle", "_add_release_fn", "release",
        "make_str_prop", "make_int_prop", "make_float_prop", "make_prop", "set_property",
        "HfssApp", "HfssDesktop", "HfssProject", "HfssDesign",
        "HfssSetup", "HfssDMSetup", "HfssDTSetup", "HfssEMSetup", "AnsysQ3DSetup",
        "HfssDesignSolutions", "HfssEMDesignSolutions", "HfssDMDesignSolutions",
        "HfssDTDesignSolutions", "HfssQ3DDesignSolutions",
        "HfssFrequencySweep", "HfssReport", "Optimetrics",
        "HfssModeler", "ModelEntity", "Box", "Rect", "Polyline", "OpenPolyline",
        "HfssFieldsCalc", "CalcObject", "NamedCalcObject", "ConstantCalcObject", "ConstantVecCalcObject",
        "get_active_project", "get_active_design", "get_report_arrays", "load_ansys_project",
    ]
