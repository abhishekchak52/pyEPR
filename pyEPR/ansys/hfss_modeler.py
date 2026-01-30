"""HfssModeler for pyaedt backend."""

import numpy as np

from pyEPR import logger
from pyEPR.ansys._units import var
from pyEPR.ansys._wrapper import COMWrapper
from pyEPR.ansys.model_entity import Box, OpenPolyline, Polyline, Rect


class HfssModeler(COMWrapper):
    def __init__(self, design, modeler, boundaries, mesh):
        super(HfssModeler, self).__init__()
        self.parent = design
        self._modeler = modeler
        self._boundaries = boundaries
        self._mesh = mesh

    def set_units(self, units, rescale=True):
        self._modeler.SetModelUnits(
            ["NAME:Units Parameter", "Units:=", units, "Rescale:=", rescale]
        )

    def get_units(self):
        return str(self._modeler.GetModelUnits())

    def _attributes_array(
        self,
        name=None,
        nonmodel=False,
        wireframe=False,
        color=None,
        transparency=0.9,
        material=None,
        solve_inside=None,
        coordinate_system="Global",
    ):
        arr = ["NAME:Attributes", "PartCoordinateSystem:=", coordinate_system]
        if name is not None:
            arr.extend(["Name:=", name])
        if nonmodel or wireframe:
            flags = "NonModel" if nonmodel else ""
            if wireframe:
                flags += "#" if flags else "" + "Wireframe"
            arr.extend(["Flags:=", flags])
        if color is not None:
            arr.extend(["Color:=", "(%d %d %d)" % color])
        if transparency is not None:
            arr.extend(["Transparency:=", transparency])
        if material is not None:
            arr.extend(["MaterialName:=", material])
        if solve_inside is not None:
            arr.extend(["SolveInside:=", solve_inside])
        return arr

    def get_face_ids(self, obj):
        return self._modeler.GetFaceIDs(obj)

    def eval_expr(self, expr):
        return self._modeler.EvaluateExpression(expr) if hasattr(expr, "__str__") else expr

    def draw_box_corner(self, pos, size, **kwargs):
        name = self._modeler.CreateBox(
            [
                "NAME:BoxParameters",
                "XPosition:=", str(pos[0]), "YPosition:=", str(pos[1]), "ZPosition:=", str(pos[2]),
                "XSize:=", str(size[0]), "YSize:=", str(size[1]), "ZSize:=", str(size[2]),
            ],
            self._attributes_array(**kwargs),
        )
        return Box(name, self, pos, size)

    def draw_box_center(self, pos, size, **kwargs):
        corner_pos = [var(p) - var(s) / 2 for p, s in zip(pos, size)]
        return self.draw_box_corner(corner_pos, size, **kwargs)

    def draw_polyline(self, points, closed=True, **kwargs):
        pointsStr = ["NAME:PolylinePoints"]
        indexsStr = ["NAME:PolylineSegments"]
        for ii, point in enumerate(points):
            pointsStr.append(["NAME:PLPoint", "X:=", str(point[0]), "Y:=", str(point[1]), "Z:=", str(point[2])])
            indexsStr.append(["NAME:PLSegment", "SegmentType:=", "Line", "StartIndex:=", ii, "NoOfPoints:=", 2])
        if closed:
            pointsStr.append(["NAME:PLPoint", "X:=", str(points[0][0]), "Y:=", str(points[0][1]), "Z:=", str(points[0][2])])
            params_closed = ["IsPolylineCovered:=", True, "IsPolylineClosed:=", True]
        else:
            indexsStr = indexsStr[:-1]
            params_closed = ["IsPolylineCovered:=", True, "IsPolylineClosed:=", False]
        name = self._modeler.CreatePolyline(
            ["NAME:PolylineParameters", *params_closed, pointsStr, indexsStr],
            self._attributes_array(**kwargs),
        )
        return Polyline(name, self, points) if closed else OpenPolyline(name, self, points)

    def draw_rect_corner(self, pos, x_size=0, y_size=0, z_size=0, **kwargs):
        size = [x_size, y_size, z_size]
        assert 0 in size
        axis = "XYZ"[size.index(0)]
        w_idx, h_idx = {"X": (1, 2), "Y": (2, 0), "Z": (0, 1)}[axis]
        name = self._modeler.CreateRectangle(
            [
                "NAME:RectangleParameters",
                "XStart:=", str(pos[0]), "YStart:=", str(pos[1]), "ZStart:=", str(pos[2]),
                "Width:=", str(size[w_idx]), "Height:=", str(size[h_idx]),
            ],
            self._attributes_array(**kwargs),
        )
        return Rect(name, self, pos, [size[w_idx], size[h_idx], 0])

    def get_vertex_ids(self, obj):
        return self._modeler.GetVertexIDs(obj)

    def rename_obj(self, obj, new_name):
        self._modeler.ChangeProperty(["NAME:AllTabs", ["NAME:Geometry3DAttributeTab", ["NAME:PropServers", obj], ["NAME:ChangedProps", ["NAME:Name", "Value:=", new_name]]]])
        return new_name

    def copy(self, obj):
        return self._modeler.DuplicateAlongLine(obj, ["0mm", "0mm", "0mm"], "1mm", 1, ["NAME:DuplicateToAlongLineParameters", "CreateNewObjects:=", True])

    def get_objects_in_group(self, group):
        return self._modeler.GetObjectsInGroup(group)

    def get_object_name_by_face_id(self, face_id):
        return self._modeler.GetObjectNameByFaceID(face_id)

    def mesh_length(self, name_mesh, objects, MaxLength="0.1mm", **kwargs):
        assert isinstance(objects, list)
        arr = ["NAME:" + name_mesh, "Objects:=", objects, "MaxLength:=", MaxLength]
        for key, val in kwargs.items():
            if key in ["RefineInside", "Enabled", "RestrictElem", "NumMaxElem", "RestrictLength"]:
                arr += [key + ":=", str(val)]
        self._mesh.AssignLengthOp(arr)
