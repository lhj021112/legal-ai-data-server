from __future__ import annotations

import argparse
from pathlib import Path

import requests


def collect_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(
        path
        for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in {".txt", ".json"}
    )


def upload_file(data_server_url: str, admin_api_key: str, file_path: Path) -> None:
    url = f"{data_server_url.rstrip('/')}/cases/import-file"
    headers = {"X-Admin-API-Key": admin_api_key}

    with file_path.open("rb") as file:
        response = requests.post(
            url,
            headers=headers,
            files={"file": (file_path.name, file)},
            timeout=60,
        )

    if response.ok:
        print(f"OK {file_path.name}: {response.json()}")
    else:
        print(f"FAIL {file_path.name}: {response.status_code} {response.text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload legal case files to the Data Server.")
    parser.add_argument("input_path", help="Path to a .txt/.json file or directory.")
    parser.add_argument(
        "--server-url",
        default="https://legal-ai-data-server.onrender.com",
        help="Data Server base URL.",
    )
    parser.add_argument("--admin-api-key", required=True, help="Admin API key for uploads.")
    args = parser.parse_args()

    files = collect_files(Path(args.input_path))
    if not files:
        print(f"No .txt or .json files found: {args.input_path}")
        return

    for file_path in files:
        upload_file(args.server_url, args.admin_api_key, file_path)


if __name__ == "__main__":
    main()
