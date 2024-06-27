import pathlib
import json
import logging
import xml.etree.ElementTree as ET
import zipfile
import tempfile
import os

import requests
import FreeCAD
import Part

from .api_utils import trace_error_log, load_user
from .errors import MissingAssembliesError, UserNotAllowedToRecomputeAssembliesError
from .config import UPLOAD_ENDPOINT, MODEL_ENDPOINT
from .assemblies_handler import download_assemblies
from .utils.generic_utils import get_property_bag_obj, get_app_varset_obj, get_property_data, update_model, get_visible_objects, is_obj_have_part_file
from .utils.project_utility import createDocument

logger = logging.getLogger(__name__)


@trace_error_log
def model_configurer_command(event, context):
    attributes = event.get("attributes", {})

    # Getting signed url to download the file
    _id = event.get("id")
    access_token = event.get("accessToken")
    is_shared_model = event.get("isSharedModel", None)
    file_name = pathlib.Path(event.get("fileName"))
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    res = requests.get(
        url=f"{UPLOAD_ENDPOINT}/{file_name}",
        headers=headers
    )
    if not res.ok:
        raise Exception("Failed to generate signed url")

    # download file from signed url
    res = requests.get(
        url=res.json().get("url"),
    )
    if not res.ok:
        raise Exception("Failed to download file from signed url")
    file_data = b""
    for chunk in res.iter_content(chunk_size=1024):
        if chunk:
            file_data += chunk

    with tempfile.TemporaryDirectory() as tmp_dir:

        output_file = f"{tmp_dir}/{_id}_generated.FCSTD"
        file_suffix = file_name.suffix.upper()
        if file_suffix == ".OBJ":
            with open(output_file, "wb") as ff:
                ff.write(file_data)
        elif file_suffix == ".FCSTD":
            input_file = f"{tmp_dir}/{file_name}"
            with open(input_file, "wb") as f:
                f.write(file_data)

            linked_files, files_available, files_not_available = download_assemblies(_id, input_file, tmp_dir, headers)
            logger.debug(f"Linked Files: {str(linked_files)}")
            logger.debug(f"Files Available: {str(files_available)}")
            logger.debug(f"Files not available: {str(files_not_available)}")
            user = load_user(event)

            if linked_files:
                if not (user and user.get("tier") in ("Peer", "Enterprise")):
                    raise UserNotAllowedToRecomputeAssembliesError()

            if files_not_available:
                raise MissingAssembliesError({
                    "linkedFiles": linked_files,
                    "filesAvailable": [f.split("/").pop() for f in files_available],
                    "filesNotAvailable": files_not_available
                })
            attributes = model_configure(input_file, attributes, output_file, files_available)
        else:
            raise Exception("Give input file format not supported yet.")

        res = requests.post(
            url=UPLOAD_ENDPOINT,
            headers=headers,
            files={"file": open(output_file, "rb")}
        )
        if not res.ok:
            raise Exception("Failed to upload generated file")

        data = {
            "isObjGenerationInProgress": False,
            "isObjGenerated": True,
            "attributes": attributes,
        }

        headers["Content-Type"] = "application/json"
        logger.debug(json.dumps(data))
        r = requests.patch(
            url=f"{MODEL_ENDPOINT}/{_id}" if is_shared_model is None else f"{MODEL_ENDPOINT}/{_id}?isSharedModel={str(is_shared_model).lower()}",
            headers=headers,
            data=json.dumps(data),
        )
        if r.ok:
            logger.info(f"Data pushed for {_id}")

    return {"Status": "OK"}


def model_configure(freecad_file_path: str, attributes: dict, obj_file_path: str, link_files: list):
    initial_attributes = {}
    try:
        doc = FreeCAD.openDocument(str(freecad_file_path))
        FreeCAD.setActiveDocument(doc.Name)
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(freecad_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            xml_root_gui = ET.parse(f"{temp_dir}/GuiDocument.xml")
            xml_root = ET.parse(f"{temp_dir}/Document.xml")

            visible_objects_names = get_visible_objects(xml_root_gui)
            logger.debug(f"Visible objects: {visible_objects_names}")
            objs_without_brps = []
            for obj_name in visible_objects_names:
                obj = doc.getObject(obj_name)
                if hasattr(obj, "Shape") and is_obj_have_part_file(obj_name, xml_root) is False:
                    objs_without_brps.append(obj)

            logger.debug(f"Objects without brep: {[i.Name for i in objs_without_brps]}")

            # support Path objects
            # path_objs = get_path_main_object(doc)
            # create_path_shape_objects(path_objs)

            attribute_obj = get_app_varset_obj(doc) or get_property_bag_obj(doc)
            if attribute_obj:
                initial_attributes = get_property_data(attribute_obj)
                if attributes:
                    update_model(attribute_obj, initial_attributes, attributes)
            doc.save()

        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(freecad_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            brep_folder = os.path.join(temp_dir, "breps")
            os.mkdir(brep_folder)
            for obj in objs_without_brps:
                Part.export([Part.show(obj.Shape)], os.path.join(brep_folder, f"ondsel_{obj.Name}.brp"))

            for file in link_files:
                os.symlink(
                    file,
                    f"{temp_dir}/{file.rsplit('/')[-1]}"
                )

            createDocument(os.path.join(temp_dir, "Document.xml"), str(obj_file_path))
    finally:
        FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)

    return attributes if attributes else initial_attributes
