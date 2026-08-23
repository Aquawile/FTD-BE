#!/usr/bin/env bash
set -euo pipefail

# Provision staging VM (ftd-staging) as a replica of ftd-test
# Usage: bash scripts/provision_staging_vm.sh

PROJECT="ftd2026"
ZONE="us-west2-a"
VM_NAME="ftd-staging"
MACHINE_TYPE="e2-medium"
BOOT_DISK_SIZE="30GB"
BOOT_DISK_TYPE="pd-standard"
IMAGE_FAMILY="debian-12"
IMAGE_PROJECT="debian-cloud"
SERVICE_ACCOUNT="767713105-compute@developer.gserviceaccount.com"
SCOPES="https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/trace.append,https://www.googleapis.com/auth/secretmanager"
TAGS="http-server,https-server"
USER="isabellabutera"

echo "=== Provisioning staging VM: ${VM_NAME} ==="
echo "Project: ${PROJECT}"
echo "Zone: ${ZONE}"
echo "Machine type: ${MACHINE_TYPE}"
echo "Service account: ${SERVICE_ACCOUNT}"
echo "Tags: ${TAGS}"
echo ""

# Check if VM already exists
if gcloud compute instances describe "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --quiet 2>/dev/null; then
    echo "VM ${VM_NAME} already exists. Skipping creation."
else
    echo "Creating VM ${VM_NAME}..."
    gcloud compute instances create "${VM_NAME}" \
        --project="${PROJECT}" \
        --zone="${ZONE}" \
        --machine-type="${MACHINE_TYPE}" \
        --boot-disk-size="${BOOT_DISK_SIZE}" \
        --boot-disk-type="${BOOT_DISK_TYPE}" \
        --image-family="${IMAGE_FAMILY}" \
        --image-project="${IMAGE_PROJECT}" \
        --service-account="${SERVICE_ACCOUNT}" \
        --scopes="${SCOPES}" \
        --tags="${TAGS}" \
        --metadata=enable-osconfig=TRUE \
        --quiet
    
    echo "VM created successfully."
fi

# Wait for VM to be running
echo "Waiting for VM to reach RUNNING state..."
gcloud compute instances start "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --quiet

# Wait for SSH to be ready via IAP
echo "Waiting for SSH to be ready via IAP..."
READY=false
for i in $(seq 1 24); do
    if gcloud compute ssh "${USER}@${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --tunnel-through-iap --command="echo 'SSH ready'" --quiet 2>/dev/null; then
        echo "SSH ready after ${i} attempt(s)"
        READY=true
        break
    fi
    echo "SSH not ready yet, waiting 10s (attempt ${i}/24)..."
    sleep 10
done

if [ "${READY}" != "true" ]; then
    echo "ERROR: ${VM_NAME} did not become SSH-ready within 4 minutes"
    exit 1
fi

# Install base dependencies
echo "Installing base dependencies..."
gcloud compute ssh "${USER}@${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --tunnel-through-iap --command="
    sudo apt-get update -qq &&
    sudo apt-get install -y -qq python3 python3-venv python3-pip git curl &&
    python3 -m venv /home/${USER}/app/.venv || true
" --quiet

# Create directory structure
echo "Creating directory structure..."
gcloud compute ssh "${USER}@${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --tunnel-through-iap --command="
    mkdir -p /home/${USER}/app/app &&
    mkdir -p /home/${USER}/frontend/dist
" --quiet

# Deploy startup script
echo "Deploying startup script..."
gcloud compute scp scripts/start_app.sh "${USER}@${VM_NAME}:/home/${USER}/start_app.sh" --zone="${ZONE}" --project="${PROJECT}" --quiet
gcloud compute ssh "${USER}@${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --tunnel-through-iap --command="chmod +x /home/${USER}/start_app.sh" --quiet

# Verify VM can reach PostgreSQL
echo "Verifying PostgreSQL connectivity..."
gcloud compute ssh "${USER}@${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --tunnel-through-iap --command="
    nc -zv 10.168.0.3 5432
" --quiet || {
    echo "WARNING: Cannot reach PostgreSQL at 10.168.0.3:5432 from ${VM_NAME}"
    echo "This may be expected if the database is not yet created."
}

echo ""
echo "=== Staging VM ${VM_NAME} provisioned successfully ==="
echo "Internal IP: $(gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --project=${PROJECT} --format='value(networkInterfaces[0].networkIP)')"
echo "External IP: $(gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --project=${PROJECT} --format='value(networkInterfaces[0].accessConfigs[0].natIP)')"
echo ""
echo "Next steps:"
echo "1. Create ftd_lakehouse_staging database on ftd-postgres-vm"
echo "2. Run auth migrations (001-005) on the staging database"
echo "3. Add FTD_STAGING_PG_PASSWORD to GitHub Actions secrets"
echo "4. Test deployment with: git push origin staging"