import os
from dotenv import load_dotenv

# Initialize dotenv
load_dotenv()

class Config:
    ## Infrastructure URLs
    MAESTRO_HOST = os.getenv("MAESTRO_HOST")
    KEYCLOAK_HOST = os.getenv("KEYCLOAK_HOST")
    ## Credentials - SECRETS REMOVED
    KC_CLIENT_ID = os.getenv("KC_CLIENT_ID")
    KC_CLIENT_SECRET = os.getenv("KC_CLIENT_SECRET")
    KC_USER = os.getenv("KC_USER", "admin")
    KC_PASS = os.getenv("KC_PASS")
    ## Helm & Registry
    HELM_REGISTRY = os.getenv("HELM_REGISTRY")
    DEFAULT_VERSION = os.getenv("DEFAULT_VERSION", "0.1.0")
    
    ## Prometheus
    PROM_URL = os.getenv("PROM_URL", "http://prometheus-stack-kube-prom-prometheus.monitoring.svc")
    PROM_PORT = int(os.getenv("PROM_PORT", "9090"))

    ## Service Order Metadata
    EXPECTED_COMPLETED_DATE = os.getenv("EXPECTED_COMPLETED_DATE", "2026-11-15T16:30:53Z")
    REQUESTED_COMPLETED_DATE = os.getenv("REQUESTED_COMPLETED_DATE", "2026-11-15T16:30:53Z")
    CLUSTER_METADATA = os.getenv("CLUSTER_METADATA") 
    SERVICE_SPEC_ID = os.getenv("SERVICE_SPEC_ID")
    K8S_SERVICE_ID = os.getenv("K8S_SERVICE_ID")
    SERVICE_NAME = os.getenv("SERVICE_NAME", "HPA Test Application")

    ## Flask / CORS
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    ## Persistence (The missing var)
    # If not set in .env, this will be None, and tmf_server.py will skip saving
    INTENT_SAVE_DIR = os.getenv("INTENT_SAVE_DIR")

    @classmethod
    def validate_config(cls):
        """Check for mandatory environment variables."""
        required = ["KC_CLIENT_SECRET", "KC_PASS", "HELM_REGISTRY", "SERVICE_SPEC_ID", "K8S_SERVICE_ID"]
        missing = [var for var in required if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"CRITICAL: The following environment variables are missing from .env: {', '.join(missing)}")