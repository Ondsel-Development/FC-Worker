import pathlib

import FreeCAD

from .generic_utils import get_shape_objs


def export_model(doc: FreeCAD.ActiveDocument, export_file_path: pathlib.Path):
    suffix = export_file_path.suffix.upper()
    if suffix == ".FCSTD":
        doc.saveAs(str(export_file_path))
    elif suffix == ".STEP":
        import Import
        Import.export(get_shape_objs(doc), str(export_file_path))
    elif suffix == ".STL":
        import Mesh
        Mesh.export(get_shape_objs(doc), str(export_file_path))
    elif suffix == ".OBJ":
        import importOBJ
        importOBJ.export(get_shape_objs(doc), str(export_file_path))
    else:
        raise ValueError(f"Give export format {export_file_path} not implemented yet.")


