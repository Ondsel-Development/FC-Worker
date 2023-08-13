import os

from fc_worker import model_configurer_command, export_command
from fc_worker.api_utils import trace_log

print(f"Group id of the current process: {os.getuid()}")
print(f"Real user ID of the current process: {os.getgid()}")

HEALTH_CHECK_CMD = "health_check"
CONFIGURE_MODEL_CMD = "CONFIGURE_MODEL"
EXPORT_FCSTD_CMD = "EXPORT_FCSTD"
EXPORT_STEP_CMD = "EXPORT_STEP"
EXPORT_STL_CMD = "EXPORT_STL"
EXPORT_OBJ_CMD = "EXPORT_OBJ"
EXPORT_CMDS = [EXPORT_FCSTD_CMD, EXPORT_STEP_CMD, EXPORT_STL_CMD, EXPORT_OBJ_CMD]


@trace_log
def lambda_handler(event, context):
    print(f"Executing lambda")
    print(f"Event: {event}")
    print(f"Context: {context}")
    command = event.get("command", None)
    if command == HEALTH_CHECK_CMD:
        return {
            "Status": "OK"
        }
    elif command.upper() == CONFIGURE_MODEL_CMD:
        return model_configurer_command(event, command)
    elif command.upper() in EXPORT_CMDS:
        export_command(event, command)
    else:
        return f"Thank you strace, worker is running."
