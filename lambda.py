import os

print(f"Group id of the current process: {os.getuid()}")
print(f"Real user ID of the current process: {os.getgid()}")

HEALTH_CHECK_CMD = "health_check"


def lambda_handler(event, context):
    print(f"Executing lambda")
    print(f"Event: {event}")
    print(f"Context: {context}")
    command = event.get("command", None)
    if command == HEALTH_CHECK_CMD:
        return {
            "Status": "OK"
        }
    else:
        return f"Thank you strace, worker is running."
