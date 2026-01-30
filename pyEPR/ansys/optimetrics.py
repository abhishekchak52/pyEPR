"""Optimetrics for pyaedt backend."""

from collections.abc import Iterable

from pyEPR.ansys._wrapper import COMWrapper


class Optimetrics(COMWrapper):
    """Optimetrics script commands (pyaedt backend)."""
    def __init__(self, design):
        super(Optimetrics, self).__init__()
        self.design = design
        self._optimetrics = self.design._optimetrics
        self.setup_names = None

    def get_setup_names(self):
        self.setup_names = list(self._optimetrics.GetSetupNames())
        return self.setup_names.copy()

    def solve_setup(self, setup_name: str):
        return self._optimetrics.SolveSetup(setup_name)

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
        setup_name = setup_name or self.design.get_setup_names()[0]
        print("Inserting optimetrics setup `%s` for simulation setup: `%s`" % (name, setup_name))
        if setup_type == "parametric":
            type_map = {
                "linear_count": "LINC",
                "decade_count": "DEC",
                "octave_count": "OCT",
                "exponential_count": "ESTP",
            }
            valid_swp_types = {"single_value", "linear_step"} | set(type_map.keys())
            if isinstance(variable, Iterable) and not isinstance(variable, str):
                assert len(swp_params) == len(swp_type) == len(variable)
                synchronize = True
            else:
                swp_type = [swp_type]
                swp_params = [swp_params]
                variable = [variable]
                synchronize = False
            if any(e not in valid_swp_types for e in swp_type):
                raise NotImplementedError()
            swp_str = []
            for i, e in enumerate(swp_type):
                if e == "single_value":
                    swp_str.append("%s" % (swp_params[i],))
                else:
                    assert len(swp_params[i]) == 3
                    if e == "linear_step":
                        swp_type_name = "LIN"
                    else:
                        assert isinstance(swp_params[i][2], int)
                        swp_type_name = type_map[e]
                    swp_str.append(
                        "%s %s %s %s" % (swp_type_name, swp_params[i][0], swp_params[i][1], swp_params[i][2])
                    )
            self._optimetrics.InsertSetup(
                "OptiParametric",
                [
                    "NAME:" + name,
                    "IsEnabled:=", True,
                    ["NAME:ProdOptiSetupDataV2",
                     "SaveFields:=", save_fields,
                     "CopyMesh:=", copy_mesh,
                     "SolveWithCopiedMeshOnly:=", solve_with_copied_mesh_only],
                    ["NAME:StartingPoint"],
                    "Sim. Setups:=", [setup_name],
                    ["NAME:Sweeps"] + [
                        ["NAME:SweepDefinition", "Variable:=", var_name, "Data:=", swp,
                         "OffsetF1:=", False, "Synchronize:=", int(synchronize)]
                        for var_name, swp in zip(variable, swp_str)
                    ],
                    ["NAME:Sweep Operations"],
                    ["NAME:Goals"],
                ],
            )
        elif setup_type == "parametric_file":
            filename = swp_params
            self._optimetrics.ImportSetup("OptiParametric", ["NAME:" + name, filename])
            self._optimetrics.EditSetup(
                name,
                ["NAME:" + name, ["NAME:ProdOptiSetupDataV2",
                                  "SaveFields:=", save_fields,
                                  "CopyMesh:=", copy_mesh,
                                  "SolveWithCopiedMeshOnly:=", solve_with_copied_mesh_only]],
            )
        else:
            raise NotImplementedError()
