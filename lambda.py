# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>
#
# SPDX-License-Identifier: LGPL-2.0-or-later

import os

from fc_worker import model_configurer_command, export_command
from fc_worker.api_utils import (
    HEALTH_CHECK_CMD,
    CONFIGURE_MODEL_CMD,
    EXPORT_CMDS,
    trace_log,
)
from fc_worker.config import VERSION

print(f"Group id of the current process: {os.getuid()}")
print(f"Real user ID of the current process: {os.getgid()}")


@trace_log
def lambda_handler(event, context):
    print(f"Executing lambda: {VERSION}")
    print(f"Event: {event}")
    print(f"Context: {context}")
    command = event.get("command", None)
    if command == HEALTH_CHECK_CMD:
        return {
            "Status": "OK"
        }
    elif command.upper() == CONFIGURE_MODEL_CMD:
        return model_configurer_command(event, context)
    elif command.upper() in EXPORT_CMDS:
        export_command(event, command)
    else:
        return f"Thank you strace, worker is running."
