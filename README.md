# DTP-OrphanedRunConfigurationCleaner

This repository provides a small cross-platform utility that calls the Parasoft DTP REST API to remove orphaned run configurations from every filter in a project.

The cleaner works like this:

1. It retrieves all filters for the supplied DTP project.
2. For each filter, it loads the filter's `runConfigurations`.
3. It keeps only run configurations that contain a `lastRun` object.
4. If any run configurations are missing `lastRun`, it updates the filter so only the kept run configurations remain.

## Files

- `/home/runner/work/DTP-OrphanedRunConfigurationCleaner/DTP-OrphanedRunConfigurationCleaner/clean_orphaned_run_configurations.py` - main implementation
- `/home/runner/work/DTP-OrphanedRunConfigurationCleaner/DTP-OrphanedRunConfigurationCleaner/clean-orphaned-run-configurations.sh` - Linux/macOS entry point
- `/home/runner/work/DTP-OrphanedRunConfigurationCleaner/DTP-OrphanedRunConfigurationCleaner/clean-orphaned-run-configurations.cmd` - Windows entry point

## Requirements

- Python 3 must be installed.
- The machine running the script must be able to reach your DTP server.
- You must know:
  - DTP host
  - DTP port
  - DTP project name
  - DTP username
  - DTP password

## Command-line options

The Python script accepts these arguments:

- `--host` - DTP host name, such as `dtp.example.com`
- `--port` - DTP port, such as `8443`
- `--project` - exact DTP project name
- `--username` - DTP user name
- `--password` - DTP password; if omitted, the script prompts for it
- `--scheme` - `https` or `http` (default: `https`)
- `--insecure` - disables TLS certificate validation for HTTPS connections
- `--dry-run` - reports what would be removed without sending the update request

## Linux usage

From the repository root:

```sh
chmod +x ./clean-orphaned-run-configurations.sh ./clean_orphaned_run_configurations.py
./clean-orphaned-run-configurations.sh \
  --host dtp.example.com \
  --port 8443 \
  --project "spring-petclinic-microservices-wilhelm" \
  --username admin \
  --dry-run
```

If you omit `--password`, the script prompts:

```sh
./clean-orphaned-run-configurations.sh \
  --host dtp.example.com \
  --port 8443 \
  --project "spring-petclinic-microservices-wilhelm" \
  --username admin
```

## Windows usage

From the repository root in Command Prompt:

```bat
clean-orphaned-run-configurations.cmd --host dtp.example.com --port 8443 --project "spring-petclinic-microservices-wilhelm" --username admin --dry-run
```

If Python is not registered through `py`, the wrapper falls back to `python`.

## What the script removes

For each filter returned by:

```text
GET /grs/api/v1.13/filters?projectName={project_name}&managedOnly=false
```

the script loads:

```text
GET /grs/api/v1.13/filters/{filterId}?fields=runConfigurations.lastRun
```

It then builds the keep payload from run configurations that contain `lastRun`, for example:

```json
[{"id":1}]
```

When orphaned run configurations are found, it sends:

```text
PUT /grs/api/v1.13/filters/{filterId}/runConfigurations
```

with the keep payload as the JSON request body.

## Recommended workflow

1. Run with `--dry-run` first to review the planned changes.
2. Run again without `--dry-run` to apply the updates.
3. Review the script output to confirm which filters were updated.
