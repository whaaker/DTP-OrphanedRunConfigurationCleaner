#!/usr/bin/env python3
from __future__ import annotations
import argparse
import base64
import getpass
import json
import ssl
import sys
from typing import Any, Iterable
from urllib import error, parse, request

API_VERSION = "v1.13"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Remove orphaned run configurations from all filters in a DTP project. "
            "A run configuration is treated as orphaned when it does not include a lastRun object."
        )
    )
    parser.add_argument("--host", required=True, help="DTP host name, for example dtp.example.com")
    parser.add_argument("--port", type=int, required=True, help="DTP port, for example 8443")
    parser.add_argument("--project", required=True, help="Exact DTP project name")
    parser.add_argument("--username", required=True, help="DTP username")
    parser.add_argument(
        "--password",
        help="DTP password. If omitted, the script prompts for it so it is not stored in shell history.",
    )
    parser.add_argument("--scheme", default="https", choices=("http", "https"), help="DTP URL scheme")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for HTTPS connections",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the changes that would be made without sending any update requests",
    )
    return parser


class DtpClient:
    def __init__(self, scheme: str, host: str, port: int, username: str, password: str, insecure: bool = False):
        self.base_url = f"{scheme}://{host}:{port}/grs/api/{API_VERSION}"
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
        self.context = None
        if scheme == "https" and insecure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self.context = ctx

    def request_json(self, method: str, path: str, query: dict[str, Any] | None = None, payload: Any | None = None) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with request.urlopen(req, context=self.context) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {url} failed with status {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc

    def get_filters(self, project_name: str) -> list[dict[str, Any]]:
        result = self.request_json(
            "GET",
            "/filters",
            query={"projectName": project_name, "managedOnly": "false"},
        )
        if not isinstance(result, list):
            raise RuntimeError("Unexpected filters response: expected a JSON array")
        return result

    def get_filter_details(self, filter_id: int) -> dict[str, Any]:
        result = self.request_json("GET", f"/filters/{filter_id}", query={"fields": "runConfigurations.lastRun"})
        if not isinstance(result, dict):
            raise RuntimeError(f"Unexpected filter response for filter {filter_id}: expected a JSON object")
        return result

    def update_filter_run_configurations(self, filter_id: int, payload: Iterable[dict[str, int]]) -> None:
        self.request_json("PUT", f"/filters/{filter_id}/runConfigurations", payload=list(payload))


def keep_payload(run_configurations: list[dict[str, Any]]) -> list[dict[str, int]]:
    return [{"id": run_configuration["id"]} for run_configuration in run_configurations if run_configuration.get("lastRun")]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    password = args.password if args.password is not None else getpass.getpass("DTP password: ")
    client = DtpClient(args.scheme, args.host, args.port, args.username, password, insecure=args.insecure)

    filters = client.get_filters(args.project)
    print(f"Found {len(filters)} filter(s) for project '{args.project}'.")
    total_removed = 0

    for filter_summary in filters:
        filter_id = filter_summary["id"]
        filter_name = filter_summary.get("name", str(filter_id))
        filter_details = client.get_filter_details(filter_id)
        run_configurations = filter_details.get("runConfigurations") or []
        payload = keep_payload(run_configurations)
        removed_count = len(run_configurations) - len(payload)

        if removed_count == 0:
            print(f"- Filter {filter_name} ({filter_id}): no orphaned run configurations found.")
            continue

        total_removed += removed_count
        print(
            f"- Filter {filter_name} ({filter_id}): removing {removed_count} orphaned run configuration(s); "
            f"keeping {len(payload)}."
        )
        if args.dry_run:
            print(f"  Dry run payload: {json.dumps(payload)}")
            continue

        client.update_filter_run_configurations(filter_id, payload)
        print("  Update complete.")

    if total_removed == 0:
        print("No orphaned run configurations were found.")
    elif args.dry_run:
        print(f"Dry run complete. {total_removed} orphaned run configuration(s) would be removed.")
    else:
        print(f"Done. Removed {total_removed} orphaned run configuration(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
