import json
import os
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REGISTRY = "https://components.espressif.com"


def main(archive):
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    request = Request(
        f"{url}&{urlencode({'audience': REGISTRY})}",
        headers={"Authorization": f"Bearer {os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']}"},
    )
    with urlopen(request, timeout=10) as response:
        token = json.load(response)["value"]
    print(f"::add-mask::{token}", flush=True)
    subprocess.run(
        ["compote", "component", "upload", "--namespace", "openblink", "--name", "mrubyc-esp32",
         "--archive", archive, "--allow-existing"],
        env={**os.environ, "IDF_COMPONENT_API_TOKEN": token, "IDF_COMPONENT_REGISTRY_URL": REGISTRY},
        check=True,
    )


if __name__ == "__main__":
    main(*sys.argv[1:])
