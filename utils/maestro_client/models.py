import base64
from datetime import datetime, timezone
from config import Config

## cluster_metadata = "YXBpVmVyc2lvbjogc2NoZWR1bGluZy5wMmNvZGUuZXUvdjFhbHBoYTEKa2luZDogUDJDb2RlU2NoZWR1bGluZ01hbmlmZXN0Cm1ldGFkYXRhOgogIG5hbWU6IHBvYwogIG5hbWVzcGFjZTogcDJjb2RlLXNjaGVkdWxlci1zeXN0ZW0Kc3BlYzoKICBnbG9iYWxBbm5vdGF0aW9uczoKICAgIC0gInAyY29kZS50YXJnZXQubWFuYWdlZENsdXN0ZXJTZXQ9ZGVmYXVsdCIKICAgIC0gInAyY29kZS50YXJnZXQuY2x1c3Rlcj1jbHVzdGVyLWs4cy0yIg=="
## cluster_metadata = "YXBpVmVyc2lvbjogc2NoZWR1bGluZy5wMmNvZGUuZXUvdjFhbHBoYTEKa2luZDogUDJDb2RlU2NoZWR1bGluZ01hbmlmZXN0Cm1ldGFkYXRhOgogIG5hbWU6IHBvYwogIG5hbWVzcGFjZTogcDJjb2RlLXNjaGVkdWxlci1zeXN0ZW0Kc3BlYzoKICB3b3JrbG9hZEFubm90YXRpb25zOgogICAgLSBuYW1lOiBwb2QtYS1ocGEKICAgICAgYW5ub3RhdGlvbnM6CiAgICAgICAgLSBwMmNvZGUudGFyZ2V0Lm1hbmFnZWRDbHVzdGVyU2V0PWRlZmF1bHQKICAgICAgICAtIHAyY29kZS50YXJnZXQuY2x1c3Rlcj1jbHVzdGVyLWs4cy0y"
## cluster_metadata = "YXBpVmVyc2lvbjogc2NoZWR1bGluZy5wMmNvZGUuZXUvdjFhbHBoYTEKa2luZDogUDJDb2RlU2NoZWR1bGluZ01hbmlmZXN0Cm1ldGFkYXRhOgogIG5hbWU6IHBvYwogIG5hbWVzcGFjZTogcDJjb2RlLXNjaGVkdWxlci1zeXN0ZW0Kc3BlYzoKICBnbG9iYWxBbm5vdGF0aW9uczoKICAgIC0gInAyY29kZS50YXJnZXQubWFuYWdlZENsdXN0ZXJTZXQ9ZGVmYXVsdCIKICAgIC0gInAyY29kZS5maWx0ZXIubG9jYXRpb249YXRoZW5zIg=="
cluster_metadata = Config.CLUSTER_METADATA
def get_base64_cluster_metadata() -> str:
    return cluster_metadata

def get_readable_cluster_metadata() -> str:
    return base64.b64decode(cluster_metadata).decode("utf-8")

def set_readable_cluster_metadata(yaml_txt : str):
    global cluster_metadata
    cluster_metadata = base64.b64encode(yaml_txt.encode("utf-8")).decode("utf-8")

def produce_service_order_payload(applicationName :str, version :str) -> dict:
    service_current_iso_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        ## "id": str(uuid.uuid4()),
        "orderDate": service_current_iso_time,
        "completionDate": None,
        'expectedCompletionDate': Config.EXPECTED_COMPLETED_DATE,
        'requestedCompletionDate': Config.REQUESTED_COMPLETED_DATE,
        "requestedStartDate": service_current_iso_time,
        "startDate": service_current_iso_time,
        "@baseType": "BaseRootEntity",
        "state": "INITIAL",
        "@schemaLocation": None,
        "@type": "ServiceOrder",
        "href": None,
        "category": None,
        "description": f"A service order for {applicationName} service",
        "externalId": None,
        "notificationContact": None,
        "priority": None,
        "note": [],
        "serviceOrderItem": [
            {
                "@baseType": "BaseEntity",
                "@schemaLocation": None,
                "@type": None,
                "href": None,
                "action": "add",
                "orderItemRelationship": [],
                "state": "ACKNOWLEDGED",
                "service": {
                    "serviceSpecification": {
                        "@baseType": "BaseEntity",
                        "@schemaLocation": None,
                        "@type": None,
                        "href": None,
                        "name": "service-spec-end-user-cfs-ocm",
                        "version": "1.2.0",
                        "targetServiceSchema": None,
                        "@referredType": None,
                        "id": Config.SERVICE_SPEC_ID
                    },
                    "@baseType": "BaseEntity",
                    "@schemaLocation": None,
                    "@type": None,
                    "href": None,
                    "name": "service-spec-end-user-cfs-ocm",
                    "category": None,
                    "serviceType": None,
                    "place": [],
                    "relatedParty": [],
                    "serviceCharacteristic": [
                        {
                            "@baseType": "BaseRootEntity",
                            "@schemaLocation": None,
                            "@type": None,
                            "href": None,
                            "name": "Service name",
                            "valueType": "TEXT",
                            "value": {
                                "value": Config.SERVICE_NAME,
                                "alias": None
                            }
                        },
                        {
                            "@baseType": "BaseRootEntity",
                            "@schemaLocation": None,
                            "@type": None,
                            "href": None,
                            "name": "Service package manager",
                            "valueType": "ENUM",
                            "value": {
                                "value": "helm",
                                "alias": None
                            }
                        },
                        {
                            "@baseType": "BaseRootEntity",
                            "@schemaLocation": None,
                            "@type": None,
                            "href": None,
                            "name": "Base service registry/repository URL",
                            "valueType": "TEXT",
                            "value": {
                                "value": Config.HELM_REGISTRY,
                                "alias": None
                            }
                        },
                        {
                            "@baseType": "BaseRootEntity",
                            "@schemaLocation": None,
                            "@type": None,
                            "href": None,
                            "name": "Service artifact identifier in service registry/repository",
                            "valueType": "TEXT",
                            "value": {
                                "value": applicationName,
                                "alias": None
                            }
                        },
                        {
                            "@baseType": "BaseRootEntity",
                            "@schemaLocation": None,
                            "@type": None,
                            "href": None,
                            "name": "Service artifact version",
                            "valueType": "TEXT",
                            "value": {
                                "value": version,
                                "alias": None
                            }
                        },
                        {
                            "@baseType": "BaseRootEntity",
                            "@schemaLocation": None,
                            "@type": None,
                            "href": None,
                            "name": "Cluster Manager",
                            "valueType": "ENUM",
                            "value": {
                                "value": "ocm",
                                "alias": None
                            }
                        },
                        {
                        "@baseType": "BaseRootEntity",
                        "@schemaLocation": None,
                        "@type": None,
                        "href": None,
                        "name": "Kubernetes Service Id",
                        "valueType": "TEXT",
                        "value": {
                        "value": Config.K8S_SERVICE_ID,
                        "alias": None
                        }
                        },
                        {
                            "@baseType": "BaseRootEntity",
                            "@schemaLocation": None,
                            "@type": None,
                            "href": None,
                            "name": "Cluster Metadata",
                            "valueType": "TEXT",
                            "value": {
                                "value": cluster_metadata,
                                "alias": None
                            }
                        }
                    ],
                    "state": "feasibilityChecked",
                    "supportingResource": [],
                    "serviceRelationship": [],
                    "supportingService": []
                },
                "appointment": None
            },
        ],
        "orderRelationship": [],
        "relatedParty": [
            {
                "@baseType": "BaseRootEntity",
                "@schemaLocation": None,
                "@type": None,
                "href": None,
                "name": "UBITECH",
                "role": "REQUESTER",
                "@referredType": "SimpleUsername_Individual",
                "id": "2c034f2b-4ecc-44cc-9af3-6633aa96b217",
                "extendedInfo": None
            }
        ]
    }

def produce_response_get_service_order_by_id(res: dict) -> dict:
    return {
        "state": res["state"],
        "description": res["description"],
        "serviceOrderId": res["id"],
        "deploymentDetails": []
    }
