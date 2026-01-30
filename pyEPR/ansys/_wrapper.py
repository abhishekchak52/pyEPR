"""
Base wrapper, property helpers, and release for pyEPR Ansys interface (pyaedt path).
"""

import atexit
import signal
import time
import types

from .. import logger

_release_fns = []
_pyaedt_sessions = []


def _unwrap_aedt_handle(obj, attr_name: str):
    """Best-effort unwrap for PyAEDT high-level wrapper objects (Desktop, Hfss, Q3d)."""
    if obj is None:
        return None
    obj_type_name = type(obj).__name__
    is_high_level = obj_type_name in [
        "Desktop", "Hfss", "Q3d", "Q2d", "Icepak",
        "Maxwell2d", "Maxwell3d", "Mechanical",
        "Rmxprt", "Circuit", "Emit", "TwinBuilder",
    ]
    if not is_high_level or not hasattr(obj, attr_name):
        return None
    val = getattr(obj, attr_name)
    if callable(val):
        try:
            return val()
        except (TypeError, Exception) as e:
            logger.debug(f"Could not call {attr_name}() on {obj_type_name}: {e}")
            return None
    return val


def _add_release_fn(fn):
    global _release_fns
    _release_fns.append(fn)
    atexit.register(fn)
    signal.signal(signal.SIGTERM, fn)
    signal.signal(signal.SIGABRT, fn)


def release():
    """Release connection to Ansys (pyaedt backend)."""
    global _release_fns, _pyaedt_sessions
    for fn in _release_fns:
        try:
            fn()
        except Exception as e:
            logger.debug(f"Error during release: {e}")
    time.sleep(0.1)
    for session in _pyaedt_sessions:
        try:
            if hasattr(session, "release_desktop"):
                session.release_desktop()
        except Exception as e:
            logger.debug(f"Error releasing pyaedt session: {e}")
    _pyaedt_sessions.clear()


class COMWrapper(object):
    """Base class for wrapping Ansys objects (pyaedt backend)."""
    def __init__(self):
        _add_release_fn(self.release)

    def release(self):
        for k, v in list(self.__dict__.items()):
            attr = getattr(type(self), k, None)
            if isinstance(attr, property):
                continue
            try:
                if hasattr(v, "release_desktop"):
                    try:
                        v.release_desktop()
                    except Exception:
                        pass
                    try:
                        setattr(self, k, None)
                    except (AttributeError, TypeError):
                        pass
            except (AttributeError, TypeError) as e:
                logger.debug(f"Could not release attribute {k}: {e}")


class HfssPropertyObject(COMWrapper):
    prop_holder = None
    prop_tab = None
    prop_server = None


def make_str_prop(name, prop_tab=None, prop_server=None):
    return make_prop(name, prop_tab=prop_tab, prop_server=prop_server)


def make_int_prop(name, prop_tab=None, prop_server=None):
    return make_prop(
        name,
        prop_tab=prop_tab,
        prop_server=prop_server,
        prop_args=["MustBeInt:=", True],
    )


def make_float_prop(name, prop_tab=None, prop_server=None):
    return make_prop(
        name,
        prop_tab=prop_tab,
        prop_server=prop_server,
        prop_args=["MustBeInt:=", False],
    )


def make_prop(name, prop_tab=None, prop_server=None, prop_args=None):
    def set_prop(self, value, prop_tab=prop_tab, prop_server=prop_server, prop_args=prop_args):
        pt = self.prop_tab if prop_tab is None else prop_tab
        ps = self.prop_server if prop_server is None else prop_server
        if isinstance(pt, types.FunctionType):
            pt = pt(self)
        if isinstance(ps, types.FunctionType):
            ps = ps(self)
        args = prop_args or []
        self.prop_holder.ChangeProperty([
            "NAME:AllTabs", [
                "NAME:" + pt,
                ["NAME:PropServers", ps],
                ["NAME:ChangedProps", ["NAME:" + name, "Value:=", value] + args],
            ],
        ])

    def get_prop(self, prop_tab=prop_tab, prop_server=prop_server):
        pt = self.prop_tab if prop_tab is None else prop_tab
        ps = self.prop_server if prop_server is None else prop_server
        if isinstance(pt, types.FunctionType):
            pt = pt(self)
        if isinstance(ps, types.FunctionType):
            ps = ps(self)
        return self.prop_holder.GetPropertyValue(pt, ps, name)
    return property(get_prop, set_prop)


def set_property(prop_holder, prop_tab, prop_server, name, value, prop_args=None):
    if not isinstance(prop_server, list):
        prop_server = [prop_server]
    return prop_holder.ChangeProperty([
        "NAME:AllTabs", [
            "NAME:" + prop_tab,
            ["NAME:PropServers", *prop_server],
            ["NAME:ChangedProps", ["NAME:" + name, "Value:=", value] + (prop_args or [])],
        ],
    ])
