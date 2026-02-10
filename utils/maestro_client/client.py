import requests
from . import models
from typing import Optional
from config import Config

class MaestroTranslatorClient:

    def __init__(
        self,
        host: Optional[str] = None,
        host_keycloak: Optional[str] = None
    ):
        ## Use Config as the default if host/host_keycloak aren't passed during init
        self.host = host or Config.MAESTRO_HOST
        self.host_keycloak = host_keycloak or Config.KEYCLOAK_HOST
        
        self.session = requests.Session()
        self.access_token: Optional[str] = None

    def get_access_token_keycloak(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> requests.Response:
        """
        Retrieves access token using credentials from Config or passed arguments.
        """
        url = f"{self.host_keycloak}/realms/tmf/protocol/openid-connect/token"
        
        # Pull dynamically from Config if not provided in the function call
        payload = {
            "client_id": Config.KC_CLIENT_ID,
            "client_secret": Config.KC_CLIENT_SECRET,
            "grant_type": "password",
            "username": username or Config.KC_USER,
            "password": password or Config.KC_PASS,
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = self.session.post(url, data=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"!!! Keycloak Auth Failed: {response.status_code} - {response.text}")
            response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data.get("access_token")
        
        if not self.access_token:
            raise ValueError("Failed to retrieve access_token from Keycloak response.")

        ## Update the session headers for future authenticated requests
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

        return response

    def create_service_order(self, applicationName: str, version: str) -> str:
        if self.access_token is None:
            raise PermissionError(
                "Access token not available. Please call 'get_access_token_keycloak' first."
            )

        url = f"{self.host}/tmf-api/serviceOrdering/v4/serviceOrder"
        
        payload_model = models.produce_service_order_payload(applicationName, version)

        headers = {
            'Content-Type': 'application/json'
        }

        response = self.session.post(url, json=payload_model, headers=headers)
        
        if response.status_code < 200 or response.status_code >= 300:
            error_detail = response.json().get("message", response.text)
            raise ConnectionError(f"Status {response.status_code}: {error_detail}")

        return response.json()["id"]

    def get_service_order(self, service_order_id: str, as_get_response: bool = True) -> dict:
        url = f"{self.host}/tmf-api/serviceOrdering/v4/serviceOrder/{service_order_id}"
        response = self.session.get(url)
        if response.status_code < 200 or response.status_code >= 300:
            raise ConnectionError(f"Error {response.status_code}: {response.text}")
        if as_get_response:
            return models.produce_response_get_service_order_by_id(response.json())
        return response.json()

    def delete_service_order(self, service_order_id: str):
        url = f"{self.host}/tmf-api/serviceOrdering/v4/serviceOrder/{service_order_id}"
        response = self.session.delete(url)
        if response.status_code < 200 or response.status_code >= 300:
            raise ConnectionError(f"Delete failed {response.status_code}: {response.text}")

    def get_service_inventory_item(self, service_id: str) -> dict:
        url = f"{self.host}/tmf-api/serviceInventory/v4/service/{service_id}"
        response = self.session.get(url)
        if response.status_code < 200 or response.status_code >= 300:
            raise ConnectionError(f"Inventory lookup failed: {response.text}")
        return response.json()

    def patch_service_inventory_item(self, service_id: str, service_order_item: dict):
        url = f"{self.host}/tmf-api/serviceInventory/v4/service/{service_id}"
        response = self.session.patch(url, json=service_order_item)
        if response.status_code < 200 or response.status_code >= 300:
            raise ConnectionError(f"Patch failed: {response.text}")