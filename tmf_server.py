#!/usr/bin/env python3
"""
Simple TMF IntentManagement mock server.

Endpoints:
  GET  /intentSpecification
  POST /intentSpecification
  GET  /intentSpecification/<id>

  GET  /intent
  POST /intent
  GET  /intent/<id>

Minimal JSON Schema validation performed using jsonschema.
Generates manifests/<<intent-name>>-hpa.yaml and <<intent-name>>-adapter.yaml on Intent POST.
"""

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from jsonschema import Draft7Validator
import uuid
import os
import json
from datetime import datetime
import yaml
from utils.helm import helm
from pathlib import Path
from utils.maestro_client import models
from utils.maestro_client import MaestroTranslatorClient
from config import Config


# maestro_client = MaestroTranslatorClient(
#     host="https://maestro.euprojects.net",
#     host_keycloak="https://maestro-keycloak.euprojects.net"
# )


# maestro_client = MaestroTranslatorClient(
#     host="http://192.168.5.196:30088",
#     host_keycloak="http://192.168.5.196:30081"
# )

maestro_client = MaestroTranslatorClient(
    host=Config.MAESTRO_HOST,
    host_keycloak=Config.KEYCLOAK_HOST
)

app = Flask(__name__)
map_intent_to_so_ids : dict[str, str]= {}
## Allow Swagger UI origin(s) and others; adjust origin list if needed
CORS(app, resources={r"/*": {"origins": Config.CORS_ALLOWED_ORIGINS}},
     supports_credentials=True)

@app.after_request
def add_cors_headers(response):
    if Config.CORS_ALLOWED_ORIGINS and Config.CORS_ALLOWED_ORIGINS[0] != "*":
        response.headers["Access-Control-Allow-Origin"] = Config.CORS_ALLOWED_ORIGINS[0]
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"     
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


## In-memory stores
INTENT_SPEC_STORE = {}
INTENT_STORE = {}

## Minimal JSON Schemas used for validation (only required fields, extend as needed)
INTENT_SPEC_SCHEMA = {
    "type": "object",
    "required": ["@type", "name"],
    "properties": {
        "@type": {"type": "string"},
        "id": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"},
        "lifecycleStatus": {"type": "string"},
        "validFor": {"type": "object"},
        "characteristicSpecification": {"type": "array"},
        "expressionSpecification": {"type": "object"}
    },
    "additionalProperties": True
}

## Intent must have @type, name, and expression. expression must have iri
INTENT_SCHEMA = {
    "type": "object",
    "required": ["@type", "name", "intentSpecification", "expression"],
    "properties": {
        "@type": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "intentSpecification": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "href": {"type": "string"}
            }
        },
        "expression": {
            "type": "object",
            "required": ["iri"],
            "properties": {
                "iri": {"type": "string"},
                "@type": {"type": "string"},
                "expressionLanguage": {"type": "string"}
            }
        },
        "relatedParty": {"type": "array"},
        "target": {"type": "object"}
    },
    "additionalProperties": True
}


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def validation_errors_as_sl_violations(errors):
    """
    Convert jsonschema errors to a lightweight 'sl-violations' array similar to Prism.
    """
    violations = []
    for err in errors:
        path = list(err.absolute_path)
        location = ["request", "body"] + path
        violations.append({
            "location": location,
            "severity": "Error",
            "code": err.validator,
            "message": err.message
        })
    return violations


def json_response_with_violations(status_code, message, violations):
    body = {
        "@type": "Error",
        "code": str(status_code),
        "reason": "ValidationError" if status_code == 400 else "Error",
        "message": message,
    }
    resp = make_response(jsonify(body), status_code)
    resp.headers["sl-violations"] = json.dumps(violations)
    resp.headers["Content-Type"] = "application/json"
    return resp


# -------------------
# YAML generation
# -------------------
def sanitize_hpa_name(deployment_name: str) -> str:
    """
    Derive HPA name from deployment name:
    - prefer stripping trailing '-deployment' if present
    - otherwise use the deployment name and append '-hpa'
    """
    if not deployment_name:
        return "generated-hpa"
    if deployment_name.endswith("-deployment"):
        base = deployment_name[: -len("-deployment")]
    else:
        base = deployment_name
    return f"{base}-hpa"


def create_or_update_hpa_chart(intent_data, base_dir="helm/hpa"):
    """
    Create or update a Helm chart for this intent's HPA.
    Each intent gets its own subchart in helm/hpa/<intent-name>/.
    """
    intent_name = intent_data.get("name", str(uuid.uuid4()))
    chart_dir = os.path.join(base_dir, intent_name)
    os.makedirs(chart_dir, exist_ok=True)

    chart_yaml_path = os.path.join(chart_dir, "Chart.yaml")
    values_yaml_path = os.path.join(chart_dir, "values.yaml")
    templates_dir = os.path.join(chart_dir, "templates")
    os.makedirs(templates_dir, exist_ok=True)
    template_path = os.path.join(templates_dir, "hpa.yaml")

    # Create Chart.yaml if missing
    if not os.path.exists(chart_yaml_path):
        with open(chart_yaml_path, "w") as f:
            f.write(f"""apiVersion: v2
name: {intent_name}-hpa
version: 0.1.0
description: Auto-generated HPA Helm chart for intent '{intent_name}'
""")

    target = intent_data.get("target", {})
    hpa_values = {
        "name": sanitize_hpa_name(target.get("deploymentName")),
        "namespace": target.get("namespace"),
        "deployment": target.get("deploymentName"),
        "metric": target.get("metric"),
        "minReplicas": target.get("minReplicas", 1),
        "maxReplicas": target.get("maxReplicas", 10),
        "value": str(target.get("targetAverageValue", "1")),
    }

    ## Write values.yaml
    with open(values_yaml_path, "w") as f:
        yaml.dump({"hpa": hpa_values}, f, sort_keys=False)

    ## Create template if missing
    if not os.path.exists(template_path):
        with open(template_path, "w") as f:
            f.write("""\
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ .Values.hpa.name }}
  namespace: {{ .Values.hpa.namespace }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ .Values.hpa.deployment }}
  minReplicas: {{ .Values.hpa.minReplicas }}
  maxReplicas: {{ .Values.hpa.maxReplicas }}
  metrics:
    - type: External
      external:
        metric:
          name: {{ .Values.hpa.metric }}
        target:
          type: Value
          value: {{ .Values.hpa.value }}
""")

    print(f"Created/updated Helm chart for HPA: {chart_dir}")
    return chart_dir

def update_adapter_values_yaml(intent_data, output_dir="manifests"):
    """
    Update (or create) a single shared Prometheus Adapter values.yaml file.
    This file is meant to be used with:
      helm upgrade --install prometheus-adapter prometheus-community/prometheus-adapter \
        --namespace monitoring -f manifests/prometheus-adapter-values.yaml
    """
    os.makedirs(output_dir, exist_ok=True)
    values_path = os.path.join(output_dir, "prometheus-adapter-values.yaml")

    ## Load existing file or start fresh
    if os.path.exists(values_path):
        with open(values_path) as f:
            values = yaml.safe_load(f) or {}
    else:
        values = {
            "prometheus": {
                "url": Config.PROM_URL,
                "port": Config.PROM_PORT
            },
            "rules": {
                "default": False,
                "external": []
            },
            "customMetrics": {"apiService": {"enabled": True}}
        }

    target = intent_data.get("target", {})
    metric_name = target.get("metric")
    source_namespace = target.get("sourceNamespace")
    source_job = target.get("sourceJob")

    ns_filter = f'namespace="{source_namespace}"' if source_namespace else ""
    job_filter = f',job="{source_job}"' if source_job else ""
    series_query = f'http_requests_total{{{ns_filter}{job_filter}}}'.replace("}{", ",")
    metrics_query = f'sum(rate(http_requests_total{{{ns_filter}{job_filter}}}[2m])) by (namespace)'.replace("}{", ",")

    new_rule = {
        "seriesQuery": series_query,
        "resources": {
            "overrides": {
                "namespace": {"resource": "namespace"}
            }
        },
        "name": {"as": metric_name},
        "metricsQuery": metrics_query
    }

    ## Ensure 'rules.external' exists
    if "rules" not in values:
        values["rules"] = {"external": []}
    if "external" not in values["rules"]:
        values["rules"]["external"] = []

    ## Append or update existing rule with same metric name
    external_rules = values["rules"]["external"]
    for rule in external_rules:
        if rule["name"]["as"] == metric_name:
            rule.update(new_rule)
            break
    else:
        external_rules.append(new_rule)

    values["rules"]["external"] = external_rules

    # Save back to file
    with open(values_path, "w") as f:
        yaml.dump(values, f, sort_keys=False)

    print(f"Updated {values_path} with rule for metric '{metric_name}'")
    return values_path


# -------------------
# Routes
# -------------------
@app.route("/intentSpecification", methods=["GET"])
def list_intent_specifications():
    arr = list(INTENT_SPEC_STORE.values())
    resp = jsonify(arr)
    resp.headers["x-result-count"] = str(len(arr))
    resp.headers["x-total-count"] = str(len(arr))
    return resp, 200


@app.route("/intentSpecification", methods=["POST"])
def create_intent_specification():
    payload = request.get_json(force=True, silent=True)
    if payload is None:
        return json_response_with_violations(400, "Invalid JSON body", [])
    validator = Draft7Validator(INTENT_SPEC_SCHEMA)
    errors = list(validator.iter_errors(payload))
    if errors:
        violations = validation_errors_as_sl_violations(errors)
        return json_response_with_violations(400, "IntentSpecification validation failed", violations)

    spec_id = payload.get("id") or str(uuid.uuid4())
    payload["id"] = spec_id
    payload.setdefault("@type", "IntentSpecification")
    payload.setdefault("lifecycleStatus", "ACTIVE")
    payload.setdefault("version", "1.0")
    payload.setdefault("lastUpdate", datetime.utcnow().isoformat() + "Z")
    INTENT_SPEC_STORE[spec_id] = payload

    resp = make_response(jsonify(payload), 201)
    resp.headers["Location"] = f"/intentSpecification/{spec_id}"
    return resp


@app.route("/intentSpecification/<spec_id>", methods=["GET"])
def get_intent_specification(spec_id):
    spec = INTENT_SPEC_STORE.get(spec_id)
    if not spec:
        return json_response_with_violations(404, f"IntentSpecification {spec_id} not found", [])
    return jsonify(spec), 200

@app.route("/intentSpecification/<spec_id>", methods=["DELETE"])
def delete_intent_specification(spec_id):
    spec = INTENT_SPEC_STORE.get(spec_id)
    if not spec:
        return json_response_with_violations(404, f"IntentSpecification {spec_id} not found", [])

    # Prevent deleting a spec in use
    for intent in INTENT_STORE.values():
        if intent.get("intentSpecification", {}).get("id") == spec_id:
            return json_response_with_violations(
                409,
                f"Cannot delete IntentSpecification {spec_id}: still referenced by an Intent",
                []
            )

    del INTENT_SPEC_STORE[spec_id]

    return jsonify({
        "message": f"IntentSpecification {spec_id} deleted successfully"
    }), 200

@app.route("/intent", methods=["GET"])
def list_intents():
    arr = list(INTENT_STORE.values())
    resp = jsonify(arr)
    resp.headers["x-result-count"] = str(len(arr))
    resp.headers["x-total-count"] = str(len(arr))
    return resp, 200

@app.route("/intent", methods=["POST"])
def create_intent():
    payload = request.get_json(force=True, silent=True)
    if payload is None:
        return json_response_with_violations(400, "Invalid JSON body", [])
    validator = Draft7Validator(INTENT_SCHEMA)
    errors = list(validator.iter_errors(payload))
    if errors:
        violations = validation_errors_as_sl_violations(errors)
        return json_response_with_violations(400, "Intent validation failed", violations)

    spec_ref = payload.get("intentSpecification", {})
    spec_id = spec_ref.get("id")
    if spec_id and spec_id not in INTENT_SPEC_STORE:
        violations = [{
            "location": ["request", "body", "intentSpecification", "id"],
            "severity": "Error",
            "code": "notFound",
            "message": f"IntentSpecification id {spec_id} not found"
        }]
        return json_response_with_violations(400, "Referenced IntentSpecification not found", violations)

    intent_id = payload.get("id") or str(uuid.uuid4())
    version_to_use = payload.get("version", Config.DEFAULT_VERSION)
    payload["id"] = intent_id
    payload.setdefault("@type", "Intent")
    payload.setdefault("creationDate", datetime.utcnow().isoformat() + "Z")
    payload.setdefault("lifecycleStatus", "PENDING")
    payload.setdefault("version", version_to_use)
    INTENT_STORE[intent_id] = payload

    try:
        adapter_values_path = update_adapter_values_yaml(payload)
        hpa_chart_dir = create_or_update_hpa_chart(payload)

        generated = {
            "adapter_values": adapter_values_path,
            "hpa_chart_dir": hpa_chart_dir
        }

    except Exception as e:
        print("Error generating Helm resources:", e)
        return json_response_with_violations(
            500, "Failed to generate Helm resources",
            [{"location": ["server"], "severity": "Error", "code": "server_error", "message": str(e)}]
        )

    resp_body = payload.copy()
    resp_body["generatedFiles"] = generated

    resp = make_response(jsonify(resp_body), 201)
    resp.headers["Location"] = f"/intent/{intent_id}"

    intent_name = payload.get("name", str(uuid.uuid4()))
    helm_pkg_name = f"{intent_name}-hpa"
    ## The creation of the Helm package
    try:
        push_successful = helm.helm_package_and_push(
            helm_pkg_name,
            version_to_use,
            chart_path=Path(hpa_chart_dir),
            registry_url=Config.HELM_REGISTRY
        )
    except Exception as e:
        return jsonify({"helm_error": str(e)}), 400

    if not push_successful:
        return jsonify({
            "status": "error",
            "message": "Helm push failed. See server logs for details."
        }), 500

    ## The logic of the service order creation
    try:
        maestro_client.get_access_token_keycloak()
        service_order_id = maestro_client.create_service_order(helm_pkg_name, version_to_use)

        map_intent_to_so_ids[service_order_id] = intent_id
        return jsonify({
            "message": "A new service order is being processed by Maestro.",
            "serviceOrderId": service_order_id
        }), 201

    except Exception as e:
        return jsonify({"client_error": e.args[0]}), 400

    return resp


@app.route("/intent/<intent_id>", methods=["GET"])
def get_intent(intent_id):
    it = INTENT_STORE.get(intent_id)
    if not it:
        return json_response_with_violations(404, f"Intent {intent_id} not found", [])
    return jsonify(it), 200


## Optional: persist store to file (called on shutdown)
PERSIST_FILE = Config.INTENT_SAVE_DIR and os.path.join(Config.INTENT_SAVE_DIR, "intents.json") if Config.INTENT_SAVE_DIR else None

@app.route("/intent/<intent_id>", methods=["DELETE"])
def delete_intent(intent_id):
    intent = INTENT_STORE.get(intent_id)
    if not intent:
        return json_response_with_violations(404, f"Intent {intent_id} not found", [])

    ## Remove from runtime store
    del INTENT_STORE[intent_id]

    ## Remove generated Helm chart directory
    intent_name = intent.get("name")
    chart_dir = os.path.join("helm", "hpa", intent_name)
    if os.path.exists(chart_dir):
        import shutil
        shutil.rmtree(chart_dir, ignore_errors=True)

    ## Remove Prometheus Adapter rule from values.yaml
    adapter_file = "manifests/prometheus-adapter-values.yaml"
    if os.path.exists(adapter_file):
        with open(adapter_file) as f:
            values = yaml.safe_load(f) or {}

        rules = values.get("rules", {}).get("external", [])
        metric_name = intent.get("target", {}).get("metric")

        new_rules = [r for r in rules if r.get("name", {}).get("as") != metric_name]

        values["rules"]["external"] = new_rules

        with open(adapter_file, "w") as f:
            yaml.dump(values, f, sort_keys=False)

    ## Remove service order mapping (if created) ---

    res = None
    try:
        maestro_client.get_access_token_keycloak()
        if intent_id in map_intent_to_so_ids.values():
            id = [so_id for so_id, name in map_intent_to_so_ids.items() if name == intent_id][0]
        res = maestro_client.get_service_order(id, False)
    except Exception as e:
        return jsonify({"client_error": e.args[0]}), 400

    service_item_id = ""
    for order_item in res["serviceOrderItem"]:
        if order_item["service"]["name"] == "service-spec-end-user-cfs-ocm":
            service_item_id = order_item["service"]["id"]
            break

    if service_item_id == "":
        return jsonify({404: f"Service order with id '{id}', has no valid 'OCM' order item"}), 404

    try:
        service_item_body = maestro_client.get_service_inventory_item(service_item_id)

        service_item_body["state"] = "TERMINATED"
        maestro_client.patch_service_inventory_item(service_item_id, service_item_body)

        maestro_client.delete_service_order(id)
    except Exception as e:
        return jsonify({"client_error": e.args[0]}), 400

    if id in map_intent_to_so_ids:
        del map_intent_to_so_ids[id]
        print(f"    the serviceOrderId '{id}' is been cleaned from cache", flush=True)

    return jsonify({"status": 'OK'}), 200


def persist_to_file():
    if not PERSIST_FILE:
        return
    data = {
        "intentSpecification": INTENT_SPEC_STORE,
        "intent": INTENT_STORE
    }
    with open(PERSIST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_from_file():
    if not PERSIST_FILE:
        return
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE) as f:
            data = json.load(f)
        INTENT_SPEC_STORE.update(data.get("intentSpecification", {}))
        INTENT_STORE.update(data.get("intent", {}))


if __name__ == "__main__":
    load_from_file()
    port = int(os.environ.get("PORT", "4000"))
    try:
        app.run(host="0.0.0.0", port=port, debug=True)
    finally:
        persist_to_file()
