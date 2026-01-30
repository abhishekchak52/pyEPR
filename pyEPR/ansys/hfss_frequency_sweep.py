"""HfssFrequencySweep for pyaedt backend."""

import os
import tempfile

import numpy as np

from .. import logger
from ._units import increment_name
from ._wrapper import COMWrapper, make_float_prop, make_str_prop
from .hfss_report import HfssReport


class HfssFrequencySweep(COMWrapper):
    prop_tab = "HfssTab"
    start_freq = make_float_prop("Start")
    stop_freq = make_float_prop("Stop")
    step_size = make_float_prop("Step Size")
    count = make_float_prop("Count")
    sweep_type = make_str_prop("Type")

    def __init__(self, setup, name):
        super(HfssFrequencySweep, self).__init__()
        self.parent = setup
        self.name = name
        self.solution_name = self.parent.name + " : " + name
        self.prop_holder = self.parent.prop_holder
        self.prop_server = self.parent.prop_server + ":" + name
        self._ansys_version = self.parent._ansys_version

    def analyze_sweep(self):
        self.parent.analyze(self.solution_name)

    def get_network_data(self, formats):
        if isinstance(formats, str):
            formats = formats.split(",")
        formats = [f.upper() for f in formats]
        fmts_lists = {"S": [], "Y": [], "Z": []}
        for f in formats:
            fmts_lists[f[0]].append((int(f[1]), int(f[2])))
        ret = [None] * len(formats)
        freq = None
        design = self.parent.parent
        pyaedt_app = design._get_pyaedt_app()
        if pyaedt_app is not None:
            try:
                n_ports = getattr(pyaedt_app, "excitations", None)
                n_ports = len(n_ports) if n_ports else 2
                fn = tempfile.mktemp(suffix=".s%dp" % n_ports)
                touchstone_file = pyaedt_app.export_touchstone(
                    setup=self.parent.name, sweep=self.name, output_file=fn
                )
                actual_file = None
                if touchstone_file and isinstance(touchstone_file, str) and os.path.isfile(touchstone_file):
                    actual_file = touchstone_file
                elif os.path.isfile(fn):
                    actual_file = fn
                if actual_file:
                    from ansys.aedt.core.visualization.advanced.touchstone_parser import TouchstoneData
                    ts_data = TouchstoneData(touchstone_file=actual_file)
                    freq = ts_data.f
                    s_matrix = ts_data.s
                    y_matrix = ts_data.y if fmts_lists["Y"] else None
                    z_matrix = ts_data.z if fmts_lists["Z"] else None
                    for data_type, port_list in fmts_lists.items():
                        if port_list:
                            if data_type == "S":
                                matrix = s_matrix
                            elif data_type == "Y":
                                matrix = y_matrix
                            elif data_type == "Z":
                                matrix = z_matrix
                            else:
                                continue
                            for i, j in port_list:
                                c_arr = matrix[:, i - 1, j - 1]
                                ret[formats.index("%s%d%d" % (data_type, i, j))] = c_arr
                    try:
                        os.remove(actual_file)
                    except Exception:
                        pass
                    return freq, ret
            except Exception as e:
                logger.warning("PyAEDT get_network_data failed: %s", e)
        for data_type, port_list in fmts_lists.items():
            if port_list:
                fn = tempfile.mktemp()
                self.parent._solutions.ExportNetworkData(
                    [], self.parent.name + " : " + self.name, 2, fn,
                    ["all"], False, 0, data_type, -1, 1, 15,
                )
                with open(fn) as f:
                    f.readline()
                    colnames = f.readline().split()
                array = np.loadtxt(fn, skiprows=2)
                if freq is None:
                    freq = array[:, 0]
                for i, j in port_list:
                    real_idx = colnames.index("%s[%d,%d]_Re" % (data_type, i, j))
                    imag_idx = colnames.index("%s[%d,%d]_Im" % (data_type, i, j))
                    c_arr = array[:, real_idx] + 1j * array[:, imag_idx]
                    ret[formats.index("%s%d%d" % (data_type, i, j))] = c_arr
        return freq, ret

    def create_report(self, name, expr):
        existing = self.parent._reporter.GetAllReportNames()
        name = increment_name(name, existing)
        var_names = self.parent.parent.get_variable_names()
        var_args = sum([["%s:=" % v_name, ["Nominal"]] for v_name in var_names], [])
        self.parent._reporter.CreateReport(
            name, "Modal Solution Data", "Rectangular Plot",
            self.solution_name, ["Domain:=", "Sweep"],
            ["Freq:=", ["All"]] + var_args,
            ["X Component:=", "Freq", "Y Component:=", [expr]], [],
        )
        return HfssReport(self.parent.parent, name)

    def get_report_arrays(self, expr):
        r = self.create_report("Temp", expr)
        return r.get_arrays()
