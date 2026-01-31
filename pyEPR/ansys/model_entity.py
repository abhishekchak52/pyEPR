"""ModelEntity and geometry classes for pyaedt backend."""

import numpy as np

from pyEPR.ansys._units import VariableString, increment_name
from pyEPR.ansys._wrapper import HfssPropertyObject, make_float_prop, make_prop, make_str_prop
from pyEPR.ansys._units import LENGTH_UNIT


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
        super(ModelEntity, self).__init__()
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
    """
    Assume closed polyline, which creates a polygon.
    """

    model_command = "CreatePolyline"

    def __init__(self, name, modeler, points=None):
        super(Polyline, self).__init__(name, modeler)
        self.prop_holder = modeler._modeler
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
        union = self.modeler.unite(self + list_other)
        return Polyline(union, self.modeler)

    def make_center_line(self, axis):  # Expects to act on a rectangle...
        # first : find center and size
        center = [0, 0, 0]

        for point in self.points:
            center = [
                center[0] + point[0] / self.n_points,
                center[1] + point[1] / self.n_points,
                center[2] + point[2] / self.n_points,
            ]
        size = [
            2 * (center[0] - self.points[0][0]),
            2 * (center[1] - self.points[0][1]),
            2 * (center[1] - self.points[0][2]),
        ]
        axis_idx = ["x", "y", "z"].index(axis.lower())
        start = [c for c in center]
        start[axis_idx] -= size[axis_idx] / 2
        start = [self.modeler.eval_var_str(s, unit=LENGTH_UNIT) for s in start]  # TODO
        end = [c for c in center]
        end[axis_idx] += size[axis_idx] / 2
        end = [self.modeler.eval_var_str(s, unit=LENGTH_UNIT) for s in end]
        return start, end

    def make_rlc_boundary(self, axis, r=0, l=0, c=0, name="LumpRLC"):
        name = str(self) + "_" + name
        start, end = self.make_center_line(axis)
        self.modeler._make_lumped_rlc(
            r, l, c, start, end, ["Objects:=", [self]], name=name
        )

    def fillet(self, radius, vertex_index):
        self.modeler._fillet(radius, vertex_index, self)

    def vertices(self):
        return self.modeler.get_vertex_ids(self)

    def rename(self, new_name):
        """
        Warning: The increment_name only works if the sheet has not been stracted or used as a tool elsewhere.
        These names are not checked; they require modifying get_objects_in_group.

        """
        new_name = increment_name(
            new_name, self.modeler.get_objects_in_group("Sheets")
        )  # this is for a closed polyline

        # check to get the actual new name in case there was a substracted object with that name
        face_ids = self.modeler.get_face_ids(str(self))
        self.modeler.rename_obj(self, new_name)  # now rename
        if len(face_ids) > 0:
            new_name = self.modeler.get_object_name_by_face_id(face_ids[0])
        return Polyline(str(new_name), self.modeler)


class OpenPolyline(ModelEntity):
    model_command = "CreatePolyline"
    show_direction = make_prop(
        "Show Direction",
        prop_tab="Geometry3DAttributeTab",
        prop_server=lambda self: self,
    )

    def __init__(self, name, modeler, points=None):
        super(OpenPolyline, self).__init__(name, modeler)
        self.prop_holder = modeler._modeler
        if points is not None:
            self.points = points
            self.n_points = len(points)
        else:
            self.points = []

    def vertices(self):
        return self.modeler.get_vertex_ids(self)

    def fillet(self, radius, vertex_index):
        self.modeler._fillet(radius, vertex_index, self)

    def fillets(self, radius, do_not_fillet=None):
        """do_not_fillet: Index list of vertices to not fillet (1-based)."""
        if do_not_fillet is None:
            do_not_fillet = []
        raw_list_vertices = self.modeler.get_vertex_ids(self)
        list_vertices = []
        for vertex in raw_list_vertices[1:-1]:
            list_vertices.append(int(vertex))
        list_vertices = list(
            map(int, np.delete(list_vertices, np.array(do_not_fillet, dtype=int) - 1))
        )
        if len(list_vertices) != 0:
            self.modeler._fillets(radius, list_vertices, self)

    def sweep_along_path(self, to_sweep):
        return self.modeler._sweep_along_path(to_sweep, self)

    def rename(self, new_name):
        new_name = increment_name(
            new_name, list(self.modeler.get_objects_in_group("Lines"))
        )
        self.modeler.rename_obj(self, new_name)
        return OpenPolyline(new_name, self.modeler)

    def copy(self, new_name):
        new_obj = OpenPolyline(self.modeler.copy(self), self.modeler)
        return new_obj.rename(new_name)
