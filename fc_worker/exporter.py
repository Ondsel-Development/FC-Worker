import pathlib
import tempfile
import json
import logging

import requests
import FreeCAD

from .config import UPLOAD_ENDPOINT, MODEL_ENDPOINT
from .utils.generic_utils import get_property_bag_obj, get_property_data, update_model
from .utils.import_utils import open_doc_in_freecad
from .utils.export_utils import export_model


logger = logging.getLogger(__name__)


COMMANDS_EXTENSION = {
    "EXPORT_FCSTD": "FCStd",
    "EXPORT_STEP": "STEP",
    "EXPORT_STL": "STL",
    "EXPORT_OBJ": "OBJ"
}


def export_command(event, command):

    logger.info('PT: 1')
    attributes = event.get("attributes", {})

    # Getting signed url to download the file
    _id = event.get("id")
    access_token = event.get("accessToken", None)
    is_shared_model = event.get("isSharedModel", None)
    file_name = pathlib.Path(event.get("fileName"))
    logger.info('PT: 2')

    headers = {}
    if access_token:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
    res = requests.get(
        url=f"{UPLOAD_ENDPOINT}/{file_name}" if access_token else f"{UPLOAD_ENDPOINT}/{file_name}?modelId={_id}",
        headers=headers
    )
    logger.info('PT: 3')

    if not res.ok:
        raise Exception("Failed to generate signed url")

    # download file from signed url
    res = requests.get(
        url=res.json().get("url"),
    )
    logger.info('PT: 4')
    if not res.ok:
        raise Exception("Failed to download file from signed url")
    file_data = b""
    for chunk in res.iter_content(chunk_size=1024):
        if chunk:
            file_data += chunk

    with tempfile.TemporaryDirectory() as tmp_dir:

        output_file = f"{tmp_dir}/{_id}_export.{COMMANDS_EXTENSION[command]}"
        input_file = f"{tmp_dir}/{file_name}"

        with open(input_file, "wb") as f:
            f.write(file_data)

        export_model_cmd(input_file, attributes, output_file)

        res = requests.post(
            url=UPLOAD_ENDPOINT if access_token else f"{UPLOAD_ENDPOINT}?modelId={_id}",
            headers=headers,
            files={"file": open(output_file, "rb")}
        )

        if not res.ok:
            raise Exception("Failed to upload generated file")

        data = dict()
        if command == "EXPORT_FCSTD":
            data["isExportFCStdGenerated"] = True
        elif command == "EXPORT_STEP":
            data["isExportSTEPGenerated"] = True
        elif command == "EXPORT_STL":
            data["isExportSTLGenerated"] = True
        else:
            data["isExportOBJGenerated"] = True

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


def export_model_cmd(input_file_path: str, attributes: dict, export_file_path: str):
    try:
        doc = open_doc_in_freecad(input_file_path)

        prp_bag = get_property_bag_obj(doc)
        if prp_bag:
            initial_attributes = get_property_data(prp_bag)
            if attributes:
                update_model(prp_bag, initial_attributes, attributes)

        export_model(doc, pathlib.Path(export_file_path))
    finally:
        FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)
