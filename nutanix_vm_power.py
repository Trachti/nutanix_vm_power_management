import http.client
import json
import argparse
import time
import ssl

NTNX_PRISMCENTRAL_IP = "YOUR_IP:9440"
PC_TOKEN = "YOUR GENERATED TOKEN FROM nutanix_auth.py"


def get_conn():
    context = ssl._create_unverified_context()
    return http.client.HTTPSConnection(NTNX_PRISMCENTRAL_IP, context=context)


def api_request(method, url, payload=None):
    conn = get_conn()
    headers = {
        "Accept": "application/json",
        "Authorization": PC_TOKEN,
        "Content-Type": "application/json"
    }

    body = None
    if payload is not None:
        body = payload if isinstance(payload, str) else json.dumps(payload)

    conn.request(method, url, body=body, headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8")

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {"raw": raw}

    if res.status >= 400:
        raise RuntimeError(f"API error {res.status} on {url}: {data}")

    return data


def get_task_uuid(response):
    return (
        response.get("status", {}).get("execution_context", {}).get("task_uuid")
        or response.get("task_uuid")
        or response.get("status", {}).get("task_uuid")
    )


def wait_for_task(task_uuid, timeout=300, interval=5):
    url = f"/api/nutanix/v3/tasks/{task_uuid}"
    start = time.time()

    while time.time() - start < timeout:
        data = api_request("GET", url)
        status = str(data.get("status", "")).upper()

        if status in {"SUCCEEDED", "FAILED", "ABORTED"}:
            return data

        time.sleep(interval)

    raise TimeoutError(f"Task {task_uuid} reached timeout after {timeout}s.")


def get_vm_by_name(vm_name):
    offset = 0
    page_size = 50

    while True:
        payload = {
            "kind": "vm",
            "length": page_size,
            "offset": offset
        }
        data = api_request("POST", "/api/nutanix/v3/vms/list", payload)
        entities = data.get("entities", [])

        for item in entities:
            if item.get("spec", {}).get("name") == vm_name:
                return item

        if not entities:
            break

        total_matches = data.get("metadata", {}).get("total_matches")
        offset += page_size

        if total_matches is not None and offset >= total_matches:
            break

    return None


def get_vm(vm_uuid):
    return api_request("GET", f"/api/nutanix/v3/vms/{vm_uuid}")


def get_vm_power_state(vm_data):
    return (
        vm_data.get("status", {}).get("resources", {}).get("power_state")
        or vm_data.get("spec", {}).get("resources", {}).get("power_state")
        or "UNKNOWN"
    )


def update_vm_power_state(vm_uuid, target_state, timeout=300, interval=5):
    vm_data = get_vm(vm_uuid)

    if "status" in vm_data:
        del vm_data["status"]

    vm_data["spec"]["resources"]["power_state"] = target_state.upper()

    response = api_request("PUT", f"/api/nutanix/v3/vms/{vm_uuid}", vm_data)
    task_uuid = get_task_uuid(response)

    if task_uuid:
        print(f"Power-{target_state.upper()} task started: {task_uuid}")
        task_result = wait_for_task(task_uuid, timeout=timeout, interval=interval)
        task_status = str(task_result.get("status", "")).upper()

        if task_status != "SUCCEEDED":
            error_detail = task_result.get("error_detail", "Unknown error")
            raise RuntimeError(f"Power-{target_state.upper()} failed: {error_detail}")

    return get_vm(vm_uuid)


def resolve_vm(vm_name):
    vm = get_vm_by_name(vm_name)
    if not vm:
        raise RuntimeError(f"VM '{vm_name}' was not found.")

    vm_uuid = vm.get("metadata", {}).get("uuid")
    if not vm_uuid:
        raise RuntimeError(f"Could not determine UUID for VM '{vm_name}'.")

    return vm_uuid, get_vm(vm_uuid)


def print_status(vm_name, vm_uuid, vm_data):
    print("VM Status")
    print("---------")
    print(f"Name: {vm_name}")
    print(f"UUID: {vm_uuid}")
    print(f"Power state: {get_vm_power_state(vm_data)}")


def main():
    parser = argparse.ArgumentParser(
        description="Power on, power off, reboot, or show the power state of a Nutanix VM through Prism Central."
    )
    parser.add_argument("--vm", required=True, type=str, help="VM name")
    parser.add_argument(
        "--action",
        required=True,
        choices=["status", "on", "off", "reboot"],
        help="Power action to perform"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Required for power off and reboot actions"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Task timeout in seconds"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Task polling interval in seconds"
    )

    args = parser.parse_args()

    vm_uuid, vm_data = resolve_vm(args.vm)
    current_state = get_vm_power_state(vm_data).upper()

    if args.action == "status":
        print_status(args.vm, vm_uuid, vm_data)
        return

    if args.action in {"off", "reboot"} and not args.force:
        raise RuntimeError("This action requires --force.")

    if args.action == "on":
        if current_state == "ON":
            print(f"VM '{args.vm}' is already powered on.")
            print_status(args.vm, vm_uuid, vm_data)
            return

        updated_vm = update_vm_power_state(vm_uuid, "ON", timeout=args.timeout, interval=args.interval)
        print_status(args.vm, vm_uuid, updated_vm)
        return

    if args.action == "off":
        if current_state == "OFF":
            print(f"VM '{args.vm}' is already powered off.")
            print_status(args.vm, vm_uuid, vm_data)
            return

        updated_vm = update_vm_power_state(vm_uuid, "OFF", timeout=args.timeout, interval=args.interval)
        print_status(args.vm, vm_uuid, updated_vm)
        return

    if args.action == "reboot":
        print(f"Rebooting VM '{args.vm}' ...")

        if current_state != "OFF":
            update_vm_power_state(vm_uuid, "OFF", timeout=args.timeout, interval=args.interval)

        updated_vm = update_vm_power_state(vm_uuid, "ON", timeout=args.timeout, interval=args.interval)
        print_status(args.vm, vm_uuid, updated_vm)
        return


if __name__ == "__main__":
    main()
