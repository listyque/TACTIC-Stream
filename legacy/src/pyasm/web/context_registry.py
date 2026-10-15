"""Resolve original TACTIC service contexts without implicit exec locals.

This is server configuration loading, not an HTTP class-path execution API.
Contexts keep the original <base>.<project>.context.<Name>:<Name> contract.
"""
import importlib
from pathlib import Path
import re


def route_segment(value, label="route"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", value) or value.startswith("__"):
        raise ValueError("Invalid %s segment: %r" % (label, value))
    return value


def get_project(root, project, site=None):
    route_segment(project, "project")
    if site:
        root = getattr(root, route_segment(site, "site"))
    return getattr(root, project)


def attach_project(root, project, factory, site=None, site_factory=None):
    route_segment(project, "project")
    if site:
        route_segment(site, "site")
        parent = getattr(root, site, None)
        if parent is None:
            parent = (site_factory or factory)()
            setattr(root, site, parent)
        root = parent
    page = factory()
    setattr(root, project, page)
    return page


def load_contexts(directory, base, project):
    route_segment(project, "project")
    if base not in ("sites", "tactic_sites"):
        raise ValueError("Unknown TACTIC context package")
    result = {}
    directory = Path(directory)
    if not directory.is_dir():
        return result
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.suffix != ".py" or path.name.startswith((".", "__")) or not path.is_file():
            continue
        context = route_segment(path.stem, "context")
        module_name = "%s.%s.context.%s" % (base, project, context)
        module = importlib.import_module(module_name)
        try:
            factory = getattr(module, context)
        except AttributeError as exc:
            raise ImportError("Context %s must export %s" % (module_name, context)) from exc
        if not callable(factory):
            raise TypeError("Context %s:%s is not callable" % (module_name, context))
        result[context] = factory()
    return result
