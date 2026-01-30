"""ModelEntity and geometry classes for pyaedt backend."""

from pyEPR.ansys._units import VariableString
from pyEPR.ansys._wrapper import HfssPropertyObject, make_float_prop, make_str_prop


class ModelEntity(str, HfssPropertyObject):
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

    def __new__(cls, val, *args, **kwargs):
        return str.__new__(cls, val)

    def __init__(self, val, modeler):
        super(ModelEntity, cls).__init__()
        self.modeler = modeler
        self.prop_server = self + ":" + self.model_command + ":1"


class Box(ModelEntity):
    model_command = "CreateBox"
    position = make_float_prop("Position")
    x_size = make_float_prop("XSize")
    y_size = make_float_prop("YSize")
    z_size = make_float_prop("ZSize")

    def __init__(self, name, modeler, corner, size):
        super(Box, self).__init__(name, modeler)
        self.modeler = modeler
        self.prop_holder = modeler._modeler
        self.corner = corner
        self.size = size
        self.center = [c + s / 2 for c, s in zip(corner, size)]
        faces = modeler.get_face_ids(self)
        self.z_back_face, self.z_front_face = faces[0], faces[1]
        self.y_back_face, self.y_front_face = faces[2], faces[4]
        self.x_back_face, self.x_front_face = faces[3], faces[5]


class Rect(ModelEntity):
    model_command = "CreateRectangle"

    def __init__(self, name, modeler, corner, size):
        super(Rect, self).__init__(name, modeler)
        self.prop_holder = modeler._modeler
        self.corner = corner
        self.size = size
        self.center = [c + s / 2 if s else c for c, s in zip(corner, size)]

    def make_center_line(self, axis):
        axis_idx = ["x", "y", "z"].index(axis.lower())
        start = [c for c in self.center]
        start[axis_idx] -= self.size[axis_idx] / 2
        start = [self.modeler.eval_expr(s) for s in start]
        end = [c for c in self.center]
        end[axis_idx] += self.size[axis_idx] / 2
        end = [self.modeler.eval_expr(s) for s in end]
        return start, end

    def make_rlc_boundary(self, axis, r=0, l=0, c=0, name="LumpRLC"):
        start, end = self.make_center_line(axis)
        self.modeler._make_lumped_rlc(r, l, c, start, end, ["Objects:=", [self]], name=name)

    def make_lumped_port(self, axis, z0="50ohm", name="LumpPort"):
        start, end = self.make_center_line(axis)
        self.modeler._make_lumped_port(start, end, ["Objects:=", [self]], z0=z0, name=name)


class Polyline(ModelEntity):
    model_command = "CreatePolyline"

    def __init__(self, name, modeler, points=None):
        super(Polyline, self).__init__(name, modeler)
        self.prop_holder = modeler._modeler
        self.points = points

    def make_center_line(self, axis):
        axis_idx = ["x", "y", "z"].index(axis.lower())
        pts = self.points
        start = [pts[0][0], pts[0][1], pts[0][2]]
        end = [pts[-1][0], pts[-1][1], pts[-1][2]]
        start[axis_idx] = min(p[axis_idx] for p in pts)
        end[axis_idx] = max(p[axis_idx] for p in pts)
        return start, end


class OpenPolyline(ModelEntity):
    model_command = "CreatePolyline"

    def __init__(self, name, modeler, points=None):
        super(OpenPolyline, self).__init__(name, modeler)
        self.prop_holder = modeler._modeler
        self.points = points or []
