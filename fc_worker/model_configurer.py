import pathlib
import tempfile
import json
import logging

import requests
import FreeCAD
import Part

from .config import UPLOAD_ENDPOINT, MODEL_ENDPOINT
from .utils.generic_utils import get_property_bag_obj, get_property_data, get_shape_objs, update_model
from .utils.path_utils import create_path_shape_objects, get_path_main_object

logger = logging.getLogger(__name__)


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

        output_file = f"{tmp_dir}/{_id}_generated.BREP"
        file_suffix = file_name.suffix.upper()
        if file_suffix == ".OBJ":
            with open(output_file, "wb") as ff:
                ff.write(file_data)
        elif file_suffix == ".FCSTD":
            input_file = f"{tmp_dir}/{file_name}"
            with open(input_file, "wb") as f:
                f.write(file_data)
            attributes = model_configure(input_file, attributes, output_file)
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


def model_configure(freecad_file_path: str, attributes: dict, obj_file_path: str):
    initial_attributes = {}
    try:
        doc = FreeCAD.openDocument(str(freecad_file_path))
        FreeCAD.setActiveDocument(doc.Name)

        # support Path objects
        path_objs = get_path_main_object(doc)
        create_path_shape_objects(path_objs)

        prp_bag = get_property_bag_obj(doc)
        if prp_bag:
            initial_attributes = get_property_data(prp_bag)
            if attributes:
                update_model(prp_bag, initial_attributes, attributes)

        Part.export(get_shape_objs(doc, objects_to_skip=path_objs), str(obj_file_path))
    finally:
        FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)

    return attributes if attributes else initial_attributes
