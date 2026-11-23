import argparse
import json
import os
import subprocess
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REGISTRY = "https://components.espressif.com"
STAGING_REGISTRY = "https://components-staging.espressif.com"


def main(archive, staging=False):
    registry = STAGING_REGISTRY if staging else REGISTRY
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    request = Request(
        f"{url}&{urlencode({'audience': registry})}",
        headers={"Authorization": f"Bearer {os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']}"},
    )
    with urlopen(request, timeout=10) as response:
        token = json.load(response)["value"]
    print(f"::add-mask::{token}", flush=True)
    command = ["compote", "component", "upload", "--namespace", "openblink", "--name", "mrubyc-esp32",
               "--archive", archive]
    subprocess.run(
        command,
        env={**os.environ, "IDF_COMPONENT_API_TOKEN": token, "IDF_COMPONENT_REGISTRY_URL": registry},
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", action="store_true")
    parser.add_argument("archive")
    args = parser.parse_args()
    main(args.archive, staging=args.staging)
