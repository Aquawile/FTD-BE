"""GCP VM lifecycle helpers."""

from __future__ import annotations

import logging
import subprocess

from src.config import Settings

logger = logging.getLogger(__name__)

GCE_METADATA_URL = "http://metadata.google.internal/computeMetadata/v1"
METADATA_HEADERS = {"Metadata-Flavor": "Google"}


def is_running_on_gcp() -> bool:
    try:
        import requests

        response = requests.get(
            f"{GCE_METADATA_URL}/instance/id",
            headers=METADATA_HEADERS,
            timeout=2,
        )
        return response.status_code == 200
    except Exception:
        return False


def _metadata_value(path: str) -> str | None:
    try:
        import requests

        response = requests.get(
            f"{GCE_METADATA_URL}/{path}",
            headers=METADATA_HEADERS,
            timeout=2,
        )
        if response.status_code == 200:
            return response.text.strip()
    except Exception:
        return None
    return None


def resolve_instance_identity(settings: Settings) -> tuple[str, str, str]:
    project = settings.gcp_project or _metadata_value("project/project-id") or ""
    zone_path = _metadata_value("instance/zone")
    zone = settings.gce_zone
    if zone_path and not zone:
        zone = zone_path.rsplit("/", 1)[-1]
    instance_name = settings.gce_instance_name or _metadata_value("instance/name") or ""
    return project, zone, instance_name


def stop_vm(settings: Settings) -> None:
    project, zone, instance_name = resolve_instance_identity(settings)
    if not all([project, zone, instance_name]):
        logger.error(
            "Cannot stop VM: missing project/zone/instance "
            "(project=%r zone=%r instance=%r)",
            project,
            zone,
            instance_name,
        )
        return

    command = [
        "gcloud",
        "compute",
        "instances",
        "stop",
        instance_name,
        f"--zone={zone}",
        f"--project={project}",
        "--quiet",
    ]
    logger.info("Stopping VM with command: %s", " ".join(command))
    subprocess.run(command, check=False)
