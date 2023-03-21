from pathlib import Path
from typing import Union

import FreeCAD
import importOBJ


def get_shape_objs(doc: FreeCAD.ActiveDocument) -> list:
    """Return all objects which create shape in the document."""

    def _get_shape(obj) -> list:
        objs = []
        if (
            hasattr(obj, "Shape")
            and not obj.Shape.isNull()
            and not obj.isDerivedFrom("App::LinkGroup")
        ):
            objs.append(obj)
        elif obj.OutList:
            for child_obj in obj.OutList:
                objs += _get_shape(child_obj)
        return objs

    shape_objs = []
    for root_obj in doc.RootObjects:
        shape_objs += _get_shape(root_obj)
    return shape_objs


def export_to_obj(freecad_file_path: Union[str, Path], file_path: Union[str, Path]):
    try:
        doc = FreeCAD.openDocument(str(freecad_file_path))
        FreeCAD.setActiveDocument(doc.Name)
        objs = get_shape_objs(doc)
        importOBJ.export(objs, str(file_path))
    finally:
        FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)

