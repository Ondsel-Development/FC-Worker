import logging

import requests
import FreeCAD

from .config import UPLOAD_ENDPOINT, MODEL_ENDPOINT, DIRECTORY_ENDPOINT
from .utils.multi_doc_utils import find_missing_links


logger = logging.getLogger(__name__)


def download_links_files(doc, model_id, directory_path, headers):
    def get_value(data, key_path, default=None):
        keys = key_path.split('.')
        val = data
        try:
            for key in keys:
                val = val[key]
            return val
        except (KeyError, TypeError):
            return default

    def get_file_data(files, file_name):
        for _file in files:
            if get_value(_file, 'custFileName') == file_name:
                return _file
        return None

    def download_file(file, output_file_path):
        _file_name = get_value(file, 'currentVersion.uniqueFileName')
        res = requests.get(
            url=f"{UPLOAD_ENDPOINT}/{_file_name}",
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

        with open(output_file_path, "wb") as f:
            f.write(file_data)

    files_available = []
    files_not_available = []
    linked_files = find_missing_links(doc)
    model_resp = requests.get(url=f"{MODEL_ENDPOINT}/{model_id}", headers=headers)
    if model_resp.ok:
        model = model_resp.json()
        directory_id = get_value(model, 'file.directory._id', None)
        if directory_id is None:
            logger.error("File parent directory not found")
            return linked_files, files_available, linked_files
        directory_resp = requests.get(url=f"{DIRECTORY_ENDPOINT}/{directory_id}", headers=headers)
        if directory_resp.ok:
            directory = directory_resp.json()
            for file_name in linked_files:
                file = get_file_data(get_value(directory, 'files'), file_name)
                if file is None:
                    logger.error("File not found in directory")
                    files_not_available.append(file_name)
                else:
                    file_output_path = f"{directory_path}/{file_name}"
                    download_file(file, file_output_path)
                    files_available.append(file_output_path)
        else:
            logger.error(f"Failed to fetch directory: {directory_id}")
            return linked_files, files_available, linked_files
    else:
        logger.error(f"Failed to fetch model: {model_id}")
        return linked_files, files_available, linked_files
    logger.debug(f"Linked files: {str(files_available)}")
    return linked_files, files_available, files_not_available


def download_assemblies(model_id, input_file, tmp_dir, headers):
    linked_files = []
    files_available = []
    files_not_available = []
    doc = None
    try:
        doc = FreeCAD.openDocument(str(input_file))
        FreeCAD.setActiveDocument(doc.Name)
        missing_file = find_missing_links(doc)
        if len(missing_file):
            linked_files, files_available, files_not_available = download_links_files(doc, model_id, str(tmp_dir), headers)
    except Exception as ex:
        logger.error(str(ex))
    finally:
        if doc:
            FreeCAD.closeDocument(doc.Name)
    return linked_files, files_available, files_not_available
