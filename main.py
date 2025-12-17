import asyncio
import httpx
from kiota_abstractions.authentication import BaseBearerTokenAuthenticationProvider
from kiota_abstractions.authentication import AnonymousAuthenticationProvider
from kiota_abstractions.serialization import ParseNodeFactoryRegistry
from kiota_serialization_json.json_parse_node_factory import JsonParseNodeFactory
from kiota_serialization_text.text_parse_node_factory import TextParseNodeFactory
from kiota_http.httpx_request_adapter import HttpxRequestAdapter
from SwaClient.swa_client import SwaClient
from typing import Set


class BasicAuthProvider:
    """Simple authentication provider that adds Basic Auth headers"""

    def __init__(self, username: str = None, password: str = None):
        self.username = username
        self.password = password

    async def authenticate_request(
        self, request, additional_authentication_context: dict = None
    ):
        """Add authentication to the request"""
        if self.username and self.password:
            import base64

            credentials = f"{self.username}:{self.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            if hasattr(request, "headers"):
                request.headers.try_add("Authorization", f"Basic {encoded}")
        return request


async def main():
    try:
        # Register serialization factories for parsing responses
        registry = ParseNodeFactoryRegistry()
        registry.CONTENT_TYPE_ASSOCIATED_FACTORIES["application/json"] = (
            JsonParseNodeFactory()
        )
        registry.CONTENT_TYPE_ASSOCIATED_FACTORIES["text/plain"] = (
            TextParseNodeFactory()
        )

        # Create an authentication provider
        # TODO: Replace with your actual credentials
        # Option 1: Use Basic Auth (uncomment and add your credentials)
        # auth_provider = BasicAuthProvider(username="your_username", password="your_password")

        # Option 2: Use Anonymous (no authentication) - currently causing 401 error
        auth_provider = AnonymousAuthenticationProvider()

        # Create a custom httpx client with SSL verification disabled and HTTP/1.1
        # This helps with self-signed certificates and protocol issues
        http_client = httpx.AsyncClient(
            verify=False,  # Disable SSL verification for self-signed certs
            http2=False,  # Use HTTP/1.1 instead of HTTP/2
            timeout=30.0,  # 30 second timeout
            follow_redirects=True,
        )

        # Create a request adapter with the custom client
        request_adapter = HttpxRequestAdapter(auth_provider, http_client=http_client)
        request_adapter.base_url = "https://vm-rhauswirth2.otxlab.net:8443/searchWebApi"

        # Create the client
        client = SwaClient(request_adapter)

        print("Attempting to login...")
        # Login to create a session
        login_response = await client.login.post()
        print(f"Login successful! Response: {login_response}")

        print("\nFetching projects...")
        # Get available projects
        projects = await client.projects.get()
        print(f"Retrieved projects: {projects}")

    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
    except httpx.ConnectError as e:
        print(f"Connection error: Cannot connect to the server. {e}")
    except httpx.TimeoutException as e:
        print(f"Request timed out: {e}")
    except Exception as e:
        print(f"An error occurred: {type(e).__name__}")
        print(f"Error details: {e}")
    finally:
        # Close the http client if it exists
        if "http_client" in locals():
            await http_client.aclose()


# Run the async function
asyncio.run(main())
