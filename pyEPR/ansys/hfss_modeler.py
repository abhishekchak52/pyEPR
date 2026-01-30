"""HfssModeler for pyaedt backend."""

from copy import copy

import numpy as np

from pyEPR import logger
from pyEPR.ansys._units import LENGTH_UNIT, fix_units, increment_name, var
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

    def get_all_properties(self, obj_name, PropTab="Geometry3DAttributeTab"):
        PropServer = obj_name
        properties = {}
        for key in self._modeler.GetProperties(PropTab, PropServer):
            properties[key] = self._modeler.GetPropertyValue(
                PropTab, PropServer, key
            )
        return properties

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
                flags += "#" if len(flags) > 0 else ""
                flags += "Wireframe"
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

    def _selections_array(self, *names):
        return ["NAME:Selections", "Selections:=", ",".join(str(n) for n in names)]

    def get_face_ids(self, obj):
        return self._modeler.GetFaceIDs(obj)

    def eval_expr(self, expr, units="mm"):
        if not isinstance(expr, str):
            return expr
        if hasattr(self.parent, "eval_expr"):
            return self.parent.eval_expr(expr, units)
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
                "WhichAxis:=", axis,
            ],
            self._attributes_array(**kwargs),
        )
        return Rect(name, self, pos, [size[w_idx], size[h_idx], 0])

    def draw_rect_center(self, pos, x_size=0, y_size=0, z_size=0, **kwargs):
        corner_pos = [
            var(p) - var(s) / 2.0 for p, s in zip(pos, [x_size, y_size, z_size])
        ]
        return self.draw_rect_corner(corner_pos, x_size, y_size, z_size, **kwargs)

    def draw_cylinder(self, pos, radius, height, axis, **kwargs):
        assert axis in "XYZ"
        return self._modeler.CreateCylinder(
            [
                "NAME:CylinderParameters",
                "XCenter:=", pos[0],
                "YCenter:=", pos[1],
                "ZCenter:=", pos[2],
                "Radius:=", radius,
                "Height:=", height,
                "WhichAxis:=", axis,
                "NumSides:=", 0,
            ],
            self._attributes_array(**kwargs),
        )

    def draw_cylinder_center(self, pos, radius, height, axis, **kwargs):
        axis_idx = ["X", "Y", "Z"].index(axis)
        edge_pos = copy(pos) if isinstance(pos, list) else list(pos)
        edge_pos[axis_idx] = var(pos[axis_idx]) - var(height) / 2
        return self.draw_cylinder(edge_pos, radius, height, axis, **kwargs)

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
        p = np.array(pos)
        o = np.array(ori)
        pad1 = p - o * width / 2.0
        name = self._modeler.CreateBondwire(
            [
                "NAME:BondwireParameters",
                "WireType:=", "Low",
                "WireDiameter:=", wire_diameter,
                "NumSides:=", NumSides,
                "XPadPos:=", pad1[0],
                "YPadPos:=", pad1[1],
                "ZPadPos:=", z,
                "XDir:=", ori[0],
                "YDir:=", ori[1],
                "ZDir:=", 0,
                "Distance:=", width,
                "h1:=", height,
                "h2:=", "0mm",
                "alpha:=", "80deg",
                "beta:=", "80deg",
                "WhichAxis:=", "Z",
            ],
            self._attributes_array(**kwargs),
        )
        return name

    def draw_region(
        self,
        Padding,
        PaddingType="Percentage Offset",
        name="Region",
        material='"vacuum"',
    ):
        RegionAttributes = [
            "NAME:Attributes",
            "Name:=", name,
            "Flags:=", "Wireframe#",
            "Color:=", "(255 0 0)",
            "Transparency:=", 1,
            "PartCoordinateSystem:=", "Global",
            "UDMId:=", "",
            "IsAlwaysHiden:=", False,
            "MaterialValue:=", material,
            "SolveInside:=", True,
        ]
        self._modeler.CreateRegion(
            [
                "NAME:RegionParameters",
                "+XPaddingType:=", PaddingType,
                "+XPadding:=", Padding[0][0],
                "-XPaddingType:=", PaddingType,
                "-XPadding:=", Padding[0][1],
                "+YPaddingType:=", PaddingType,
                "+YPadding:=", Padding[1][0],
                "-YPaddingType:=", PaddingType,
                "-YPadding:=", Padding[1][1],
                "+ZPaddingType:=", PaddingType,
                "+ZPadding:=", Padding[2][0],
                "-ZPaddingType:=", PaddingType,
                "-ZPadding:=", Padding[2][1],
            ],
            RegionAttributes,
        )

    def subtract(self, blank_name, tool_names, keep_originals=False):
        selection_array = [
            "NAME:Selections",
            "Blank Parts:=", blank_name,
            "Tool Parts:=", ",".join(tool_names),
        ]
        self._modeler.Subtract(
            selection_array,
            ["NAME:UniteParameters", "KeepOriginals:=", keep_originals],
        )
        return blank_name

    def unite(self, names, keep_originals=False):
        self._modeler.Unite(
            self._selections_array(*names),
            ["NAME:UniteParameters", "KeepOriginals:=", keep_originals],
        )
        return names[0]

    def assign_perfect_E(self, obj, name="PerfE"):
        if not isinstance(obj, list):
            obj = [obj]
            if name == "PerfE":
                name = str(obj[0]) + "_" + name
        name = increment_name(name, self._boundaries.GetBoundaries())
        self._boundaries.AssignPerfectE(
            ["NAME:" + name, "Objects:=", obj, "InfGroundPlane:=", False]
        )

    def translate(self, name, vector):
        self._modeler.Move(
            self._selections_array(name),
            [
                "NAME:TranslateParameters",
                "TranslateVectorX:=", vector[0],
                "TranslateVectorY:=", vector[1],
                "TranslateVectorZ:=", vector[2],
            ],
        )

    def intersect(self, names, keep_originals=False):
        self._modeler.Intersect(
            self._selections_array(*names),
            ["NAME:IntersectParameters", "KeepOriginals:=", keep_originals],
        )
        return names[0]

    def get_boundary_assignment(self, boundary_name):
        objects = self._boundaries.GetBoundaryAssignment(boundary_name)
        return [self._modeler.GetObjectNameByFaceID(k) for k in objects]

    def append_PerfE_assignment(self, boundary_name, object_names):
        boundary_name = str(boundary_name)
        if isinstance(object_names, str):
            object_names = [object_names]
        object_names = list(object_names)
        if boundary_name not in self._boundaries.GetBoundaries():
            self.assign_perfect_E(object_names, name=boundary_name)
        else:
            objects = list(self.get_boundary_assignment(boundary_name))
            self._boundaries.ReassignBoundary(
                [
                    "NAME:" + boundary_name,
                    "Objects:=",
                    list(set(objects + object_names)),
                ]
            )

    def _make_lumped_rlc(self, r, l, c, start, end, obj_arr, name="LumpRLC"):
        name = increment_name(name, self._boundaries.GetBoundaries())
        params = ["NAME:" + name]
        params += obj_arr
        params.append(
            [
                "NAME:CurrentLine",
                "Start:=", fix_units(start, unit_assumed=LENGTH_UNIT),
                "End:=", fix_units(end, unit_assumed=LENGTH_UNIT),
            ]
        )
        params += [
            "UseResist:=", r != 0,
            "Resistance:=", r,
            "UseInduct:=", l != 0,
            "Inductance:=", l,
            "UseCap:=", c != 0,
            "Capacitance:=", c,
        ]
        self._boundaries.AssignLumpedRLC(params)

    def _make_lumped_port(self, start, end, obj_arr, z0="50ohm", name="LumpPort"):
        start = fix_units(start, unit_assumed=LENGTH_UNIT)
        end = fix_units(end, unit_assumed=LENGTH_UNIT)
        name = increment_name(name, self._boundaries.GetBoundaries())
        params = ["NAME:" + name]
        params += obj_arr
        params += [
            "RenormalizeAllTerminals:=", True,
            "DoDeembed:=", False,
            [
                "NAME:Modes",
                [
                    "NAME:Mode1",
                    "ModeNum:=", 1,
                    "UseIntLine:=", True,
                    ["NAME:IntLine", "Start:=", start, "End:=", end],
                    "CharImp:=", "Zpi",
                    "AlignmentGroup:=", 0,
                    "RenormImp:=", "50ohm",
                ],
            ],
            "ShowReporterFilter:=", False,
            "ReporterFilter:=", [True],
            "FullResistance:=", z0,
            "FullReactance:=", "0ohm",
        ]
        self._boundaries.AssignLumpedPort(params)

    def get_vertex_ids(self, obj):
        get_from_obj = getattr(self._modeler, "GetVertexIDsFromObject", None)
        if get_from_obj is not None:
            return get_from_obj(obj)
        return self._modeler.GetVertexIDs(obj)

    def _fillet(self, radius, vertex_index, obj):
        vertices = self.get_vertex_ids(obj)
        if isinstance(vertex_index, list):
            to_fillet = [int(vertices[v]) for v in vertex_index]
        else:
            to_fillet = [int(vertices[vertex_index])]
        self._modeler.Fillet(
            ["NAME:Selections", "Selections:=", obj],
            [
                "NAME:Parameters",
                [
                    "NAME:FilletParameters",
                    "Edges:=",
                    [],
                    "Vertices:=",
                    to_fillet,
                    "Radius:=",
                    radius,
                    "Setback:=",
                    "0mm",
                ],
            ],
        )

    def _fillets(self, radius, vertices, obj):
        self._modeler.Fillet(
            ["NAME:Selections", "Selections:=", obj],
            [
                "NAME:Parameters",
                [
                    "NAME:FilletParameters",
                    "Edges:=",
                    [],
                    "Vertices:=",
                    vertices,
                    "Radius:=",
                    radius,
                    "Setback:=",
                    "0mm",
                ],
            ],
        )

    def _fillet_edges(self, radius, edge_index, obj):
        get_edges = getattr(self._modeler, "GetEdgeIDsFromObject", None)
        if get_edges is None:
            raise AttributeError("GetEdgeIDsFromObject not available")
        edges = get_edges(obj)
        if isinstance(edge_index, list):
            to_fillet = [int(edges[e]) for e in edge_index]
        else:
            to_fillet = [int(edges[edge_index])]
        self._modeler.Fillet(
            ["NAME:Selections", "Selections:=", obj],
            [
                "NAME:Parameters",
                [
                    "NAME:FilletParameters",
                    "Edges:=", to_fillet,
                    "Vertices:=", [],
                    "Radius:=", radius,
                    "Setback:=", "0mm",
                ],
            ],
        )

    def _sweep_along_path(self, to_sweep, path_obj):
        self.rename_obj(path_obj, str(path_obj) + "_path")
        new_name = self.rename_obj(to_sweep, path_obj)
        names = [path_obj, str(path_obj) + "_path"]
        self._modeler.SweepAlongPath(
            self._selections_array(*names),
            [
                "NAME:PathSweepParameters",
                "DraftAngle:=",
                "0deg",
                "DraftType:=",
                "Round",
                "CheckFaceFaceIntersection:=",
                False,
                "TwistAngle:=",
                "0deg",
            ],
        )
        return Polyline(new_name, self)

    def sweep_along_vector(self, names, vector):
        self._modeler.SweepAlongVector(
            self._selections_array(*names),
            [
                "NAME:VectorSweepParameters",
                "DraftAngle:=", "0deg",
                "DraftType:=", "Round",
                "CheckFaceFaceIntersection:=", False,
                "SweepVectorX:=", vector[0],
                "SweepVectorY:=", vector[1],
                "SweepVectorZ:=", vector[2],
            ],
        )

    def rename_obj(self, obj, new_name):
        self._modeler.ChangeProperty(["NAME:AllTabs", ["NAME:Geometry3DAttributeTab", ["NAME:PropServers", obj], ["NAME:ChangedProps", ["NAME:Name", "Value:=", new_name]]]])
        return new_name

    def copy(self, obj):
        result = self._modeler.DuplicateAlongLine(
            obj, ["0mm", "0mm", "0mm"], "1mm", 1,
            ["NAME:DuplicateToAlongLineParameters", "CreateNewObjects:=", True],
        )
        if isinstance(result, (list, tuple)) and result:
            return result[0]
        return result

    def get_objects_in_group(self, group):
        if self._modeler:
            return list(self._modeler.GetObjectsInGroup(group))
        return list()

    def set_working_coordinate_system(self, cs_name="Global"):
        self._modeler.SetWCS(
            [
                "NAME:SetWCS Parameter",
                "Working Coordinate System:=", cs_name,
                "RegionDepCSOk:=", False,
            ]
        )

    def create_relative_coorinate_system_both(
        self,
        cs_name,
        origin=("0um", "0um", "0um"),
        XAxisVec=("1um", "0um", "0um"),
        YAxisVec=("0um", "1um", "0um"),
    ):
        self._modeler.CreateRelativeCS(
            [
                "NAME:RelativeCSParameters",
                "Mode:=", "Axis/Position",
                "OriginX:=", origin[0],
                "OriginY:=", origin[1],
                "OriginZ:=", origin[2],
                "XAxisXvec:=", XAxisVec[0],
                "XAxisYvec:=", XAxisVec[1],
                "XAxisZvec:=", XAxisVec[2],
                "YAxisXvec:=", YAxisVec[0],
                "YAxisYvec:=", YAxisVec[1],
                "YAxisZvec:=", YAxisVec[1],
            ],
            ["NAME:Attributes", "Name:=", cs_name],
        )

    def get_object_name_by_face_id(self, face_id):
        return self._modeler.GetObjectNameByFaceID(face_id)

    def mesh_length(self, name_mesh, objects, MaxLength="0.1mm", **kwargs):
        assert isinstance(objects, list)
        arr = ["NAME:" + name_mesh, "Objects:=", objects, "MaxLength:=", MaxLength]
        ops = ["RefineInside", "Enabled", "RestrictElem", "NumMaxElem", "RestrictLength"]
        for key, val in kwargs.items():
            if key in ops:
                arr += [key + ":=", str(val)]
            else:
                logger.error("KEY `%s` NOT IN ops!", key)
        self._mesh.AssignLengthOp(arr)

    def mesh_reassign(self, name_mesh, objects):
        assert isinstance(objects, list)
        self._mesh.ReassignOp(name_mesh, ["Objects:=", objects])

    def mesh_get_names(self, kind="Length Based"):
        return list(self._mesh.GetOperationNames(kind))

    def mesh_get_all_props(self, mesh_name):
        prop_tab = "MeshSetupTab"
        prop_server = "MeshSetup:{}".format(mesh_name)
        prop_names = self.parent._design.GetProperties(prop_tab, prop_server)
        dic = {}
        for name in prop_names:
            dic[name] = self._modeler.GetPropertyValue(
                prop_tab, prop_server, name
            )
        return dic

    def append_mesh(self, mesh_name, object_names, old_objs, **kwargs):
        mesh_name = str(mesh_name)
        if isinstance(object_names, str):
            object_names = [object_names]
        object_names = list(object_names)
        if mesh_name not in self.mesh_get_names():
            objs = object_names
            self.mesh_length(mesh_name, object_names, **kwargs)
        else:
            objs = list(set(old_objs + object_names))
            self.mesh_reassign(mesh_name, objs)
        return objs
