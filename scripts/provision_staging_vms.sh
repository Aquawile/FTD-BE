#!/usr/bin/env bash
# Provisions the staging Web VM (ftd-staging-web) and Backend VM (ftd-staging-api)
# as a split architecture replacing the monolithic ftd-staging VM.
# Run manually when ready to provision — not part of the pipeline.
set -euo pipefail

# =============================================================================
# CONFIGURATION - Review before running
# =============================================================================
: "${GCP_PROJECT:=ftd2026}"
: "${GCE_ZONE:=us-west2-a}"
: "${MACHINE_TYPE:=e2-medium}"
: "${IMAGE_FAMILY:=debian-12}"
: "${IMAGE_PROJECT:=debian-cloud}"
: "${BOOT_DISK_SIZE:=30GB}"
: "${SERVICE_ACCOUNT:=767713105-compute@developer.gserviceaccount.com}"
: "${SCOPES:=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/trace.append,https://www.googleapis.com/auth/secretmanager}"
: "${TAGS:=http-server,https-server}"
: "${OS_USER:=isabellabutera}"

WEB_VM_NAME="ftd-staging-web"
API_VM_NAME="ftd-staging-api"

# Database VM internal IP (for Backend VM startup script)
DB_INTERNAL_IP="10.168.0.3"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
log() { echo "[$(date -u +%H:%M:%S)] $*"; }

vm_exists() {
  gcloud compute instances describe "$1" --project="${GCP_PROJECT}" --zone="${GCE_ZONE}" >/dev/null 2>&1
}

wait_for_ssh() {
  local vm_name="$1"
  local max_attempts=24
  local attempt=1
  log "Waiting for SSH on ${vm_name}..."
  while [[ ${attempt} -le ${max_attempts} ]]; do
    if gcloud compute ssh "${OS_USER}@${vm_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="echo 'SSH ready'" --quiet 2>/dev/null; then
      log "SSH ready on ${vm_name} after ${attempt} attempt(s)"
      return 0
    fi
    log "SSH not ready yet on ${vm_name}, waiting 10s (attempt ${attempt}/${max_attempts})..."
    sleep 10
    ((attempt++))
  done
  log "ERROR: ${vm_name} did not become SSH-ready within 4 minutes"
  return 1
}

create_vm() {
  local vm_name="$1"
  local scopes="$2"
  local tags="$3"

  if vm_exists "${vm_name}"; then
    log "VM ${vm_name} already exists. Skipping creation."
    return 0
  fi

  log "Creating VM ${vm_name}..."
  gcloud compute instances create "${vm_name}" \
    --project="${GCP_PROJECT}" \
    --zone="${GCE_ZONE}" \
    --machine-type="${MACHINE_TYPE}" \
    --boot-disk-size="${BOOT_DISK_SIZE}" \
    --image-family="${IMAGE_FAMILY}" \
    --image-project="${IMAGE_PROJECT}" \
    --service-account="${SERVICE_ACCOUNT}" \
    --scopes="${scopes}" \
    --tags="${tags}" \
    --metadata=enable-osconfig=TRUE \
    --quiet

  log "VM ${vm_name} created successfully."
}

setup_web_vm() {
  local vm_name="$1"

  log "Setting up Web VM: ${vm_name}"

  # Install nginx and basic tools
  gcloud compute ssh "${OS_USER}@${vm_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="
    sudo apt-get update -qq &&
    sudo apt-get install -y -qq nginx python3 git curl &&
    sudo systemctl enable nginx &&
    sudo systemctl start nginx
  " --quiet

  # Create directory structure
  gcloud compute ssh "${OS_USER}@${vm_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="
    mkdir -p /home/${OS_USER}/frontend/dist
  " --quiet

  # Deploy nginx config for static serving + API proxy
  cat > /tmp/nginx_staging.conf << 'NGINX_EOF'
server {
    listen 8080;
    server_name _;

    root /home/isabellabutera/frontend/dist;
    index index.html index.htm;

    # Serve static files
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Proxy API requests to Backend VM
    location /api/ {
        proxy_pass http://ftd-staging-api:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
NGINX_EOF

  gcloud compute scp /tmp/nginx_staging.conf "${OS_USER}@${vm_name}:/tmp/nginx_staging.conf" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --quiet
  gcloud compute ssh "${OS_USER}@${vm_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="
    sudo mv /tmp/nginx_staging.conf /etc/nginx/sites-available/staging &&
    sudo ln -sf /etc/nginx/sites-available/staging /etc/nginx/sites-enabled/staging &&
    sudo rm -f /etc/nginx/sites-enabled/default &&
    sudo nginx -t &&
    sudo systemctl reload nginx
  " --quiet

  log "Web VM ${vm_name} setup complete."
}

setup_api_vm() {
  local vm_name="$1"

  log "Setting up Backend VM: ${vm_name}"

  # Install Python, venv, git, curl, postgresql-client
  gcloud compute ssh "${OS_USER}@${vm_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="
    sudo apt-get update -qq &&
    sudo apt-get install -y -qq python3 python3-venv python3-pip git curl postgresql-client &&
    python3 -m venv /home/${OS_USER}/app/.venv || true
  " --quiet

  # Create directory structure
  gcloud compute ssh "${OS_USER}@${vm_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="
    mkdir -p /home/${OS_USER}/app/app &&
    mkdir -p /home/${OS_USER}/frontend/dist
  " --quiet

  # Deploy startup script
  gcloud compute scp /Users/isabellabutera/gcloud-bucket-data/scripts/start_app.sh "${OS_USER}@${vm_name}:/home/${OS_USER}/start_app.sh" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --quiet
  gcloud compute ssh "${OS_USER}@${vm_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="chmod +x /home/${OS_USER}/start_app.sh" --quiet

  log "Backend VM ${vm_name} setup complete."
}

verify_connectivity() {
  local web_vm="$1"
  local api_vm="$2"

  log "Verifying internal connectivity..."

  # Test Web VM -> Backend VM connectivity
  log "Testing ${web_vm} -> ${api_vm}:8000..."
  gcloud compute ssh "${OS_USER}@${web_vm}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="
    nc -zv ${api_vm} 8000 || python3 -c \"import socket; s=socket.socket(); s.settimeout(5); s.connect(('${api_vm}', 8000)); print('Connected to ${api_vm}:8000'); s.close()\"
  " --quiet

  # Test Backend VM -> Database VM connectivity
  log "Testing ${api_vm} -> ${DB_INTERNAL_IP}:5432..."
  gcloud compute ssh "${OS_USER}@${api_vm}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="
    nc -zv ${DB_INTERNAL_IP} 5432 || python3 -c \"import socket; s=socket.socket(); s.settimeout(5); s.connect(('${DB_INTERNAL_IP}', 5432)); print('Connected to ${DB_INTERNAL_IP}:5432'); s.close()\"
  " --quiet

  log "Connectivity verification complete."
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================
log "=== Provisioning Staging Web VM (${WEB_VM_NAME}) and Backend VM (${API_VM_NAME}) ==="
log "Project: ${GCP_PROJECT}"
log "Zone: ${GCE_ZONE}"
log "Machine type: ${MACHINE_TYPE}"
log "Service account: ${SERVICE_ACCOUNT}"
log "Tags: ${TAGS}"
log ""

# Create Web VM
create_vm "${WEB_VM_NAME}" "${SCOPES}" "${TAGS}"

# Create Backend VM (needs secretmanager scope for database credentials)
create_vm "${API_VM_NAME}" "${SCOPES}" "${TAGS}"

# Start both VMs
log "Starting VMs..."
gcloud compute instances start "${WEB_VM_NAME}" "${API_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --quiet

# Wait for SSH readiness
wait_for_ssh "${WEB_VM_NAME}" || exit 1
wait_for_ssh "${API_VM_NAME}" || exit 1

# Setup Web VM
setup_web_vm "${WEB_VM_NAME}"

# Setup Backend VM
setup_api_vm "${API_VM_NAME}"

# Verify connectivity
verify_connectivity "${WEB_VM_NAME}" "${API_VM_NAME}"

# Print VM details
WEB_INT_IP=$(gcloud compute instances describe "${WEB_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --format='value(networkInterfaces[0].networkIP)')
WEB_EXT_IP=$(gcloud compute instances describe "${WEB_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')
API_INT_IP=$(gcloud compute instances describe "${API_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --format='value(networkInterfaces[0].networkIP)')
API_EXT_IP=$(gcloud compute instances describe "${API_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')

log ""
log "=== Provisioning Complete ==="
log "Web VM (${WEB_VM_NAME}):"
log "  Internal IP: ${WEB_INT_IP}"
log "  External IP: ${WEB_EXT_IP}"
log "  Serves: React frontend on port 8080, proxies /api/* to Backend VM"
log ""
log "Backend VM (${API_VM_NAME}):"
log "  Internal IP: ${API_INT_IP}"
log "  External IP: ${API_EXT_IP}"
log "  Runs: FastAPI on 127.0.0.1:8000"
log "  Connects to: PostgreSQL at ${DB_INTERNAL_IP}:5432"
log ""
log "Next steps:"
log "1. Add FTD_STAGING_PG_PASSWORD to GitHub Actions secrets (if not already present)"
log "2. Ensure ftd_lakehouse_staging database exists on ftd-postgres-vm with migrations applied"
log "3. Update deploy workflow to target these VMs"
log "4. Test deployment with: git push origin staging"