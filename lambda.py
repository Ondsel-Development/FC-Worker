import enum
import os
import requests
import tempfile
import pathlib
import json

from fc_worker import export_to_obj

print(f"Group id of the current process: {os.getuid()}")
print(f"Real user ID of the current process: {os.getgid()}")

HEALTH_CHECK_CMD = "health_check"
GENERATE_OBJ_CMD = "GENERATE_OBJ"

BACKEND_URL = os.getenv("BACKEND_URL")
UPLOAD_ENDPOINT = f"{BACKEND_URL}/upload"
MODEL_ENDPOINT = f"{BACKEND_URL}/models"


class Status(enum.Enum):
    INPROGRESS = 1
    COMPLETED = 2


def generate_obj(event, context):

    def update_status_line(_id, status):
        if status == Status.INPROGRESS:
            status_data = {
                "isObjGenerationInProgress": True,
                "isObjGenerated": False,
            }
        else:
            status_data = {
                "isObjGenerationInProgress": False,
                "isObjGenerated": True,
            }
        h = headers.copy()
        h["Content-Type"] = "application/json"
        print(h)
        r = requests.patch(
            url=f"{MODEL_ENDPOINT}/{_id}",
            headers=h,
            data=json.dumps(status_data),
        )
        if r.ok:
            print("\n--- update status ---\n")
        return r.ok

    # Getting signed url to download the file
    _id = event.get("id")
    access_token = event.get("accessToken")
    file_name = pathlib.Path(event.get("fileName"))
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # update_status_line(_id, Status.INPROGRESS)

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

        output_file = f"{tmp_dir}/{file_name.stem}_generated.OBJ"
        file_suffix = file_name.suffix.upper()
        if file_suffix == ".OBJ":
            with open(output_file, "wb") as ff:
                ff.write(file_data)
        elif file_suffix == ".FCSTD":
            input_file = f"{tmp_dir}/{file_name}"
            with open(input_file, "wb") as f:
                f.write(file_data)

            export_to_obj(input_file, output_file)
        else:
            raise Exception("Give input file format not supported yet.")

        res = requests.post(
            url=UPLOAD_ENDPOINT,
            headers=headers,
            files={"file": open(output_file, "rb")}
        )
        if not res.ok:
            raise Exception("Failed to upload generated file")

    update_status_line(_id, Status.COMPLETED)
    return {"Status": "OK"}


def lambda_handler(event, context):
    print(f"Executing lambda")
    print(f"Event: {event}")
    print(f"Context: {context}")
    command = event.get("command", None)
    if command == HEALTH_CHECK_CMD:
        return {
            "Status": "OK"
        }
    elif command.upper() == GENERATE_OBJ_CMD:
        return generate_obj(event, context)
    else:
        return f"Thank you strace, worker is running."
