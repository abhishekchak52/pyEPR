"""HfssDesignSolutions and subclasses for pyaedt backend."""

import tempfile

import numpy as np

from .. import logger
from ._wrapper import COMWrapper


class HfssDesignSolutions(COMWrapper):
    def __init__(self, setup, solutions):
        super(HfssDesignSolutions, self).__init__()
        self.parent = setup
        self._solutions = solutions
        self._ansys_version = self.parent._ansys_version

    def get_valid_solution_list(self):
        return self._solutions.GetValidISolutionList()

    def list_variations(self, setup_name: str = None):
        if setup_name is None:
            setup_name = str(self.parent.solution_name)
        return self._solutions.ListVariations(setup_name)


class HfssEMDesignSolutions(HfssDesignSolutions):
    def eigenmodes(self, lv=""):
        fn = tempfile.mktemp()
        self._solutions.ExportEigenmodes(self.parent.solution_name, lv, fn)
        data = np.genfromtxt(fn, dtype="str")
        if np.size(np.shape(data)) == 1:
            data = np.array([data])
        if np.size(data[0, :]) == 6:
            kappa_over_2pis = [2 * float(ii) for ii in data[:, 3]]
        else:
            kappa_over_2pis = None
        freqs = [float(ii) for ii in data[:, 1]]
        return freqs, kappa_over_2pis

    def set_mode(self, n, phase=0, FieldType="EigenStoredEnergy"):
        n_modes = int(self.parent.n_modes)
        if n < 1:
            raise Exception("ERROR: You tried to set a mode < 1. %s/%s" % (n, n_modes))
        if n > n_modes:
            raise Exception("ERROR: You tried to set a mode > number of modes %s/%s" % (n, n_modes))
        if self._ansys_version >= "2019":
            self._solutions.EditSources(
                [
                    ["FieldType:=", "EigenPeakElectricField"],
                    ["Name:=", "Modes", "Magnitudes:=",
                     ["1" if i + 1 == n else "0" for i in range(n_modes)],
                     "Phases:=", [str(phase) if i + 1 == n else "0" for i in range(n_modes)]],
                ]
            )
        else:
            self._solutions.EditSources(
                "EigenStoredEnergy",
                ["NAME:SourceNames", "EigenMode"],
                ["NAME:Modes", n_modes],
                ["NAME:Magnitudes"] + [1 if i + 1 == n else 0 for i in range(n_modes)],
                ["NAME:Phases"] + [phase if i + 1 == n else 0 for i in range(n_modes)],
                ["NAME:Terminated"], ["NAME:Impedances"],
            )

    def has_fields(self, variation_string=None):
        if variation_string is None:
            variation_string = self.parent.parent.get_nominal_variation()
        return bool(self._solutions.HasFields(self.parent.solution_name, variation_string))

    def create_report(self, plot_name, xcomp, ycomp, params, pass_name="LastAdaptive"):
        setup = self.parent
        reporter = setup._reporter
        return reporter.CreateReport(
            plot_name, "Eigenmode Parameters", "Rectangular Plot",
            "%s : %s" % (setup.name, pass_name), [], params,
            ["X Component:=", xcomp, "Y Component:=", ycomp], [],
        )


class HfssDMDesignSolutions(HfssDesignSolutions):
    pass


class HfssDTDesignSolutions(HfssDesignSolutions):
    pass


class HfssQ3DDesignSolutions(HfssDesignSolutions):
    pass
