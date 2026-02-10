# Policy Engine


## Getting started

This is an implementation of the Service Orchestrator Policy Engine aspect. Using TMF Intent Management 921 API, users can apply the preferable policies in an automatic and clean way.

## TMF Intent Management API Overview

TM Forum API: TMF921 - Intent Management

Specification: TM Forum TMF921 Intent Management API

**Purpose:**
This API allows intents to be expressed, reporting on and negotiated between the intent owner and the intent handler. The Intent API provides specifies the basic attributes and relationships that describe an Intent.

Key Resources:

-	**/intentSpecification**: Define what types of intents can be created.
-	**/intent**: Represent instances of those intent specifications, carrying specific goals or parameters.


| Resource           | Role                                                                       | Analogy
| --------           | -------                                                                    | -------
| IntentSpecification| Defines the schema or template of a particular kind of intent              | Like a “class definition”
| Intent             | An instance that expresses a particular goal, following a specification    |   Like an “object” instantiated from that class



[More](https://www.tmforum.org/oda/open-apis/directory/intent-management-api-TMF921/v5.0)


## Implementation Overview

Two outputs from the TMF server whenever a new Intent is created:


- **Prometheus Adapter Values:**

A single shared file manifests/prometheus-adapter-values.yaml
Used directly with:

```helm upgrade --install prometheus-adapter prometheus-community/prometheus-adapter --namespace monitoring -f manifests/prometheus-adapter-values.yaml```

The server appends new metric “rules” to this file every time a new intent arrives.

- **HPA Helm Chart**

A real Helm chart (not just an HPA manifest).
Automatically created/updated under something like:

```
helm/hpa/<intent-name>/
├── Chart.yaml
├── values.yaml
└── templates/
    └── hpa.yaml
```

Each Intent gets its own chart so you can install it with:

```helm upgrade --install my-hpa ./helm/hpa/frontend```


The chart’s values.yaml contains data derived from the Intent.
The template is generic (templates/hpa.yaml).


**Prometheus adapter → one shared values.yaml
HPA → a Helm chart per Intent**


## Test and Deploy

Create a virtual environment in python like:

``` 
    python3 -m venv .venv  
    source .venv/bin/activate 
```

and install the below packages:
``` 
    pip install --upgrade pip  
    pip install Flask flask-cors jsonschema PyYAML   
    pip install requests  
    pip install python-dotenv
```

Also, execute the swagger editor via docker:
``` sudo docker run -p 8080:8080 swaggerapi/swagger-editor ```


Then, via a browser you have access to the swagger editor. For example, if you run the swagger editor in a host with IP address 192.168.5.142, you can hit in
the browser the *http://192.168.5.142:8080/*

Define appropriately the .env file. Then, export these env variables.

There you have to create the IntentSpecification first.

**IntentSpecification example:**

```
{
  "@type": "IntentSpecification",
  "id": "HPAIntentSpec-v1",
  "name": "HPAIntentSpecification",
  "description": "Defines how to scale Kubernetes Deployments using metrics from another source (namespace/job)",
  "lifecycleStatus": "ACTIVE",
  "version": "1.1",
  "characteristicSpecification": [
    {
      "name": "deploymentName",
      "description": "Target Kubernetes Deployment to be scaled",
      "valueType": "string"
    },
    {
      "name": "namespace",
      "description": "Namespace where the target Deployment resides",
      "valueType": "string"
    },
    {
      "name": "sourceNamespace",
      "description": "Namespace of the source metric (e.g., where Prometheus scrapes the metric)",
      "valueType": "string"
    },
    {
      "name": "sourceJob",
      "description": "Job label for the metric’s origin service or workload",
      "valueType": "string"
    },
    {
      "name": "metric",
      "description": "External metric name used for scaling decisions",
      "valueType": "string"
    },
    {
      "name": "targetAverageValue",
      "description": "Threshold metric value to trigger scaling",
      "valueType": "number"
    },
    {
      "name": "minReplicas",
      "description": "Minimum replica count allowed",
      "valueType": "integer"
    },
    {
      "name": "maxReplicas",
      "description": "Maximum replica count allowed",
      "valueType": "integer"
    }
  ],
  "expressionSpecification": {
    "@type": "ExpressionSpecification",
    "expressionLanguage": "PromQL",
    "name": "ScaleExpression"
  }
}

```
Check the response to validate that it worked.

Afterwards you can apply the Intent.

**Intent example:**

```
{
  "@type": "Intent",
  "name": "poda-scale-intent",
  "description": "Scale pod-a based on pod-b HTTP traffic",
  "intentSpecification": {
    "id": "HPAIntentSpec-v1",
    "name": "HPAIntentSpecification"
  },
  "expression": {
    "iri": "http://example.org/metrics/pod-b-http"
  },
  "target": {
    "deploymentName": "pod-a-deployment",
    "namespace": "a-namespace",
    "metric": "pod_b_http_requests",
    "targetAverageValue": "1",
    "minReplicas": 1,
    "maxReplicas": 10,
    "sourceNamespace": "b-namespace",
    "sourceJob": "pod-b-service"
  }
}

```
There is restriction regarding the name of the helm package.
Chart names must be lowercase and follow the pattern: [a-z0-9]+([._-][a-z0-9]+)* .

Also, to create helm package you can use the below commands:

```
helm registry login registry.ubitech.eu
helm package <your-folder> (-> package.tgz, i.e. helm package helm/hpa/poda-scale-intent/)
helm push <package.tgz> oci://registry.ubitech.eu/nsit/eu-projects/p2code/tmf-server-hpa
```
