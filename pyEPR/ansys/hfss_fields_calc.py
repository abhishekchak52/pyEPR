"""HfssFieldsCalc and CalcObject hierarchy for pyaedt backend."""

import numpy as np

from pyEPR import logger
from pyEPR.ansys._wrapper import COMWrapper
from pyEPR.ansys.hfss_setup import HfssDMSetup


class HfssFieldsCalc(COMWrapper):
    def __init__(self, setup):
        self.setup = setup
        super(HfssFieldsCalc, self).__init__()
        self.parent = setup
        self.Mag_E = NamedCalcObject("Mag_E", setup)
        self.Mag_H = NamedCalcObject("Mag_H", setup)
        self.Mag_Jsurf = NamedCalcObject("Mag_Jsurf", setup)
        self.Mag_Jvol = NamedCalcObject("Mag_Jvol", setup)
        self.Vector_E = NamedCalcObject("Vector_E", setup)
        self.Vector_H = NamedCalcObject("Vector_H", setup)
        self.Vector_Jsurf = NamedCalcObject("Vector_Jsurf", setup)
        self.Vector_Jvol = NamedCalcObject("Vector_Jvol", setup)
        self.ComplexMag_E = NamedCalcObject("ComplexMag_E", setup)
        self.ComplexMag_H = NamedCalcObject("ComplexMag_H", setup)
        self.ComplexMag_Jsurf = NamedCalcObject("ComplexMag_Jsurf", setup)
        self.ComplexMag_Jvol = NamedCalcObject("ComplexMag_Jvol", setup)
        self.P_J = NamedCalcObject("P_J", setup)
        self.named_expression = {}

    def clear_named_expressions(self):
        self.parent.parent._fields_calc.ClearAllNamedExpr()

    def declare_named_expression(self, name):
        self.named_expression[name] = NamedCalcObject(name, self.setup)

    def use_named_expression(self, name):
        return self.named_expression[name]


class CalcObject(COMWrapper):
    def __init__(self, stack, setup):
        super(CalcObject, self).__init__()
        self.stack = stack
        self.setup = setup
        self.calc_module = setup.parent._fields_calc

    def _bin_op(self, other, op):
        if isinstance(other, (int, float)):
            other = ConstantCalcObject(other, self.setup)
        stack = self.stack + other.stack
        stack.append(("CalcOp", op))
        return CalcObject(stack, self.setup)

    def _unary_op(self, op):
        stack = self.stack[:]
        stack.append(("CalcOp", op))
        return CalcObject(stack, self.setup)

    def __add__(self, other):
        return self._bin_op(other, "+")
    def __radd__(self, other):
        return self + other
    def __sub__(self, other):
        return self._bin_op(other, "-")
    def __rsub__(self, other):
        return (-self) + other
    def __mul__(self, other):
        return self._bin_op(other, "*")
    def __rmul__(self, other):
        return self * other
    def __truediv__(self, other):
        return self._bin_op(other, "/")
    def __rtruediv__(self, other):
        other = ConstantCalcObject(other, self.setup)
        return other / self
    __div__ = __truediv__
    __rdiv__ = __rtruediv__
    def __pow__(self, other):
        return self._bin_op(other, "Pow")
    def dot(self, other):
        return self._bin_op(other, "Dot")
    def __neg__(self):
        return self._unary_op("Neg")
    def __abs__(self):
        return self._unary_op("Abs")
    def __mag__(self):
        return self._unary_op("Mag")
    def mag(self):
        return self._unary_op("Mag")
    def smooth(self):
        return self._unary_op("Smooth")
    def conj(self):
        return self._unary_op("Conj")
    def scalar_x(self):
        return self._unary_op("ScalarX")
    def scalar_y(self):
        return self._unary_op("ScalarY")
    def scalar_z(self):
        return self._unary_op("ScalarZ")
    def norm_2(self):
        return (self.__mag__()).__pow__(2)
    def real(self):
        return self._unary_op("Real")
    def imag(self):
        return self._unary_op("Imag")
    def complexmag(self):
        return self._unary_op("CmplxMag")
    def _integrate(self, name, type):
        stack = self.stack + [(type, name), ("CalcOp", "Integrate")]
        return CalcObject(stack, self.setup)
    def _maximum(self, name, type):
        stack = self.stack + [(type, name), ("CalcOp", "Maximum")]
        return CalcObject(stack, self.setup)
    def getQty(self, name):
        stack = self.stack + [("EnterQty", name)]
        return CalcObject(stack, self.setup)
    def integrate_line(self, name):
        return self._integrate(name, "EnterLine")
    def normal2surface(self, name):
        """Return the part normal to surface. Complex Vector."""
        stack = self.stack + [("EnterSurf", name), ("CalcOp", "Normal")]
        stack.append(("CalcOp", "Dot"))
        stack.append(("EnterSurf", name))
        stack.append(("CalcOp", "Normal"))
        stack.append(("CalcOp", "*"))
        return CalcObject(stack, self.setup)
    def tangent2surface(self, name):
        """Return the part tangent to surface. Complex Vector."""
        stack = self.stack + [("EnterSurf", name), ("CalcOp", "Normal")]
        stack.append(("CalcOp", "Dot"))
        stack.append(("EnterSurf", name))
        stack.append(("CalcOp", "Normal"))
        stack.append(("CalcOp", "*"))
        stack = self.stack + stack
        stack.append(("CalcOp", "-"))
        return CalcObject(stack, self.setup)
    def integrate_line_tangent(self, name):
        """Integrate line tangent to vector expression. name = of line to integrate over."""
        stack = self.stack + [
            ("EnterLine", name),
            ("CalcOp", "Tangent"),
            ("CalcOp", "Dot"),
        ]
        return CalcObject(stack, self.setup).integrate_line(name)
    def line_tangent_coor(self, name, coordinate):
        """Integrate line tangent coordinate. name = of line; coordinate in X, Y, Z."""
        if coordinate not in ["X", "Y", "Z"]:
            raise ValueError("coordinate must be one of X, Y, Z")
        stack = self.stack + [
            ("EnterLine", name),
            ("CalcOp", "Tangent"),
            ("CalcOp", "Scalar" + coordinate),
        ]
        return CalcObject(stack, self.setup).integrate_line(name)
    def integrate_surf(self, name="AllObjects"):
        return self._integrate(name, "EnterSurf")
    def integrate_vol(self, name="AllObjects"):
        return self._integrate(name, "EnterVol")
    def maximum_vol(self, name="AllObjects"):
        return self._maximum(name, "EnterVol")
    def times_eps(self):
        stack = self.stack + [("ClcMaterial", ("Permittivity (epsi)", "mult"))]
        return CalcObject(stack, self.setup)
    def times_mu(self):
        stack = self.stack + [("ClcMaterial", ("Permeability (mu)", "mult"))]
        return CalcObject(stack, self.setup)
    def write_stack(self):
        for fn, arg in self.stack:
            if np.size(arg) > 1 and fn not in ["EnterVector"]:
                getattr(self.calc_module, fn)(*arg)
            else:
                getattr(self.calc_module, fn)(arg)

    def save_as(self, name):
        self.write_stack()
        self.calc_module.AddNamedExpr(name)
        return NamedCalcObject(name, self.setup)

    def evaluate(self, phase=0, lv=None, print_debug=False):
        self.write_stack()
        if print_debug:
            print("---------------------")
            print("writing to stack: OK")
            print("-----------------")
        setup_name = self.setup.solution_name
        args = list(lv) if lv is not None else []
        args.append("Phase:=")
        args.append(str(int(phase)) + "deg")
        if isinstance(self.setup, HfssDMSetup):
            args.extend(["Freq:=", self.setup.solution_freq])
        self.calc_module.ClcEval(setup_name, args)
        result = self.calc_module.GetTopEntryValue(setup_name, args)
        if isinstance(result, dict):
            if 0 in result:
                return float(result[0])
            if "value" in result:
                return float(result["value"])
            first_val = next(iter(result.values()))
            if isinstance(first_val, (list, tuple)) and len(first_val) > 0:
                return float(first_val[0])
            return float(first_val)
        return float(result[0])


class NamedCalcObject(CalcObject):
    def __init__(self, name, setup):
        self.name = name
        stack = [("CopyNamedExprToStack", name)]
        super(NamedCalcObject, self).__init__(stack, setup)


class ConstantCalcObject(CalcObject):
    def __init__(self, num, setup):
        stack = [("EnterScalar", num)]
        super(ConstantCalcObject, self).__init__(stack, setup)


class ConstantVecCalcObject(CalcObject):
    def __init__(self, vec, setup):
        stack = [("EnterVector", vec)]
        super(ConstantVecCalcObject, self).__init__(stack, setup)
