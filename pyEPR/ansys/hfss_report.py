"""HfssReport for pyaedt backend."""

import os
import tempfile

import numpy as np

from pyEPR.ansys._wrapper import COMWrapper


class HfssReport(COMWrapper):
    def __init__(self, design, name):
        super(HfssReport, self).__init__()
        self.parent_design = design
        self.name = name

    def export_to_file(self, filename):
        filepath = os.path.abspath(filename)
        self.parent_design._reporter.ExportToFile(self.name, filepath)

    def get_arrays(self):
        fn = tempfile.mktemp(suffix=".csv")
        self.export_to_file(fn)
        return np.loadtxt(fn, skiprows=1, delimiter=",").transpose()
