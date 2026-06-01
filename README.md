# Nutanix VM Power Management Script

A Python script for powering on, powering off, rebooting, or checking the power state of a Nutanix VM through Prism Central.

## Features

- Finds a VM by name
- Shows the current VM power state
- Powers on a VM
- Powers off a VM
- Reboots a VM by powering it off and then powering it on again
- Waits for Nutanix Prism Central tasks to finish
- Requires `--force` for power-off and reboot actions
- Uses only the Python standard library

## Requirements

- Python 3.8 or newer
- Network access to Nutanix Prism Central
- A valid Nutanix Prism Central API token
- Permission to read and update VMs

No external Python packages are required.

## Configuration

Before running the script, update these values in `nutanix_vm_power.py`:

```python
NTNX_PRISMCENTRAL_IP = "YOUR_IP:9440"
PC_TOKEN = "YOUR GENERATED TOKEN FROM nutanix_auth.py"
```

## Usage

Show VM power status:

```bash
python nutanix_vm_power.py --vm my-vm01 --action status
```

Power on a VM:

```bash
python nutanix_vm_power.py --vm my-vm01 --action on
```

Power off a VM:

```bash
python nutanix_vm_power.py --vm my-vm01 --action off --force
```

Reboot a VM:

```bash
python nutanix_vm_power.py --vm my-vm01 --action reboot --force
```

Use custom task polling settings:

```bash
python nutanix_vm_power.py \
  --vm my-vm01 \
  --action on \
  --timeout 600 \
  --interval 10
```

## Arguments

| Argument | Required | Description |
|---|---:|---|
| `--vm` | Yes | VM name |
| `--action` | Yes | `status`, `on`, `off`, or `reboot` |
| `--force` | No | Required for `off` and `reboot` |
| `--timeout` | No | Task timeout in seconds, default `300` |
| `--interval` | No | Task polling interval in seconds, default `5` |

## Safety Notes

Power-off and reboot actions require `--force` to reduce the chance of accidental shutdowns.

## Security Notes

Do not commit real API tokens, passwords, Prism Central addresses, or internal infrastructure details to a public GitHub repository.

The script currently disables SSL certificate verification by using:

```python
ssl._create_unverified_context()
```

This may be useful in lab environments, but it is not recommended for production. For production use, configure proper certificate validation.

## Disclaimer

This script is provided as an example. Test it in a safe environment before using it against production Nutanix infrastructure.
