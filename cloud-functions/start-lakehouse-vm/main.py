import json
import os
import urllib.request
import urllib.error

PROJECT = os.environ.get("GCP_PROJECT", "ftd2026")
ZONE = "us-west2-a"
INSTANCE = "data-ingest-vm"
TOKEN_URL = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
START_URL = f"https://compute.googleapis.com/compute/v1/projects/{PROJECT}/zones/{ZONE}/instances/{INSTANCE}/start"


def start_lakehouse_vm(request):
    req = urllib.request.Request(TOKEN_URL, headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(req, timeout=5) as r:
        token_data = json.loads(r.read().decode())
        token = token_data["access_token"]

    req = urllib.request.Request(START_URL, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode()[:200]
    except urllib.error.HTTPError as exc:
        return f"Error {exc.code}: {exc.read().decode()[:200]}"
