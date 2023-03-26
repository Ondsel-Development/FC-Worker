import os

from fc_worker import model_configurer_command

print(f"Group id of the current process: {os.getuid()}")
print(f"Real user ID of the current process: {os.getgid()}")

HEALTH_CHECK_CMD = "health_check"
GENERATE_OBJ_CMD = "GENERATE_OBJ"
CONFIGURE_MODEL_CMD = "CONFIGURE_MODEL"


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
    else:
        return f"Thank you strace, worker is running."
