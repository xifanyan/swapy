# SwaClient - Search Web API Python Client

A Python client library for the Search Web API, generated using [Microsoft Kiota](https://github.com/microsoft/kiota).

## Table of Contents

- [Installation](#installation)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
  - [Authentication](#authentication)
  - [Working with Projects](#working-with-projects)
  - [Working with Collections](#working-with-collections)
  - [Searching Records](#searching-records)
  - [Managing Records](#managing-records)
  - [Logout](#logout)
- [API Structure](#api-structure)
- [Error Handling](#error-handling)
- [Advanced Usage](#advanced-usage)

## Installation

First, install the required dependencies:

```bash
pip install microsoft-kiota-abstractions
pip install microsoft-kiota-http
pip install microsoft-kiota-serialization-json
pip install microsoft-kiota-serialization-text
pip install httpx
```

Then, add the `SwaClient` folder to your Python path or install it as a local package.

## Prerequisites

- Python 3.8 or higher
- Access to a Search Web API endpoint
- Valid authentication credentials

## Quick Start

Here's a minimal example to get you started:

```python
import asyncio
import httpx
import base64
from kiota_abstractions.serialization import ParseNodeFactoryRegistry
from kiota_serialization_json.json_parse_node_factory import JsonParseNodeFactory
from kiota_http.httpx_request_adapter import HttpxRequestAdapter
from SwaClient.swa_client import SwaClient

# Basic Authentication Provider with Session Management
class BasicAuthProvider:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session_id = None
    
    def set_session(self, session_id: str):
        self.session_id = session_id
    
    async def authenticate_request(self, request, additional_authentication_context: dict = None):
        if hasattr(request, "headers"):
            if self.session_id:
                # Reuse session
                request.headers.try_add("SWA-SESSION", self.session_id)
            else:
                # Send credentials
                credentials = f"{self.username}:{self.password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                request.headers.try_add("Authorization", f"Basic {encoded}")
        return request

# HTTP Client that captures sessions
class SessionCapturingHttpClient(httpx.AsyncClient):
    def __init__(self, auth_provider=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_provider = auth_provider
    
    async def send(self, request, **kwargs):
        response = await super().send(request, **kwargs)
        if self.auth_provider and "swa-session" in response.headers:
            if hasattr(self.auth_provider, "set_session"):
                self.auth_provider.set_session(response.headers["swa-session"])
        return response

async def main():
    # Register JSON parser
    registry = ParseNodeFactoryRegistry()
    registry.CONTENT_TYPE_ASSOCIATED_FACTORIES["application/json"] = JsonParseNodeFactory()
    
    # Create authentication provider
    auth_provider = BasicAuthProvider(username="your_username", password="your_password")
    
    # Create HTTP client with session capture
    http_client = SessionCapturingHttpClient(
        auth_provider=auth_provider,
        verify=False,  # Set to True for production with valid SSL
        http2=False    # Use HTTP/1.1 for compatibility
    )
    
    # Create request adapter and client
    request_adapter = HttpxRequestAdapter(auth_provider, http_client=http_client)
    request_adapter.base_url = "https://your-api-endpoint.com/searchWebApi"
    client = SwaClient(request_adapter)
    
    try:
        # Login (captures session automatically)
        await client.login.post()
        print("Login successful!")
        
        # Get available projects (uses session)
        projects = await client.projects.get()
        print(f"Retrieved projects: {projects}")
    finally:
        await http_client.aclose()

# Run the async function
asyncio.run(main())
```

## Usage Examples

### Authentication

#### Basic Authentication (Recommended)

```python
import base64

class BasicAuthProvider:
    """Authentication provider with automatic session management"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session_id = None
    
    def set_session(self, session_id: str):
        """Store session ID for reuse"""
        self.session_id = session_id
    
    async def authenticate_request(self, request, additional_authentication_context: dict = None):
        """Add authentication headers to requests"""
        if hasattr(request, "headers"):
            if self.session_id:
                # Use existing session
                request.headers.try_add("SWA-SESSION", self.session_id)
            else:
                # Send Basic Auth credentials
                credentials = f"{self.username}:{self.password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                request.headers.try_add("Authorization", f"Basic {encoded}")
        return request

# Use it
auth_provider = BasicAuthProvider(username="your_user", password="your_pass")
```

**Important**: Use `request.headers.try_add()` not `request.request_headers` - the latter doesn't actually set headers!

#### Session Management

The API returns a session ID in the `SWA-SESSION` response header. Use `SessionCapturingHttpClient` to automatically capture and reuse it:

```python
import httpx

class SessionCapturingHttpClient(httpx.AsyncClient):
    """HTTP client that automatically captures SWA-SESSION"""
    
    def __init__(self, auth_provider=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_provider = auth_provider
    
    async def send(self, request, **kwargs):
        response = await super().send(request, **kwargs)
        
        # Auto-capture session from response
        if self.auth_provider and "swa-session" in response.headers:
            if hasattr(self.auth_provider, "set_session"):
                self.auth_provider.set_session(response.headers["swa-session"])
        
        return response

# Create client with session capture
http_client = SessionCapturingHttpClient(
    auth_provider=auth_provider,
    verify=False,  # Disable SSL verification for self-signed certs
    http2=False    # Use HTTP/1.1 to avoid protocol errors
)
```

**How it works:**
- First request: Sends credentials, receives and stores session
- Subsequent requests: Automatically sends SWA-SESSION header
- No manual session management needed!

#### Multiple Users/Sessions

Each client instance maintains its own session:

```python
# Admin client
admin_auth = BasicAuthProvider(username="admin", password="admin_pass")
admin_http = SessionCapturingHttpClient(auth_provider=admin_auth, verify=False, http2=False)
admin_adapter = HttpxRequestAdapter(admin_auth, http_client=admin_http)
admin_client = SwaClient(admin_adapter)

# User client  
user_auth = BasicAuthProvider(username="user123", password="user_pass")
user_http = SessionCapturingHttpClient(auth_provider=user_auth, verify=False, http2=False)
user_adapter = HttpxRequestAdapter(user_auth, http_client=user_http)
user_client = SwaClient(user_adapter)

# Both maintain separate sessions
await admin_client.login.post()  # Admin session
await user_client.login.post()   # User session
```

### Common Setup

For all examples below, assume this setup:

```python
import asyncio
import httpx
from kiota_abstractions.serialization import ParseNodeFactoryRegistry
from kiota_serialization_json.json_parse_node_factory import JsonParseNodeFactory
from kiota_http.httpx_request_adapter import HttpxRequestAdapter
from SwaClient.swa_client import SwaClient

# Use BasicAuthProvider and SessionCapturingHttpClient from Quick Start

async def main():
    # Register parsers
    registry = ParseNodeFactoryRegistry()
    registry.CONTENT_TYPE_ASSOCIATED_FACTORIES["application/json"] = JsonParseNodeFactory()
    
    # Setup auth and client
    auth_provider = BasicAuthProvider(username="your_user", password="your_pass")
    http_client = SessionCapturingHttpClient(
        auth_provider=auth_provider,
        verify=False,
        http2=False
    )
    request_adapter = HttpxRequestAdapter(auth_provider, http_client=http_client)
    request_adapter.base_url = "https://your-api.com/searchWebApi"
    client = SwaClient(request_adapter)
    
    try:
        # Login
        await client.login.post()
        
        # Your code here...
        
    finally:
        await http_client.aclose()

asyncio.run(main())
```

### Working with Projects

#### List All Projects
```python
# Discover all available projects
projects_response = await client.projects.get()
```

#### Access a Specific Project
```python
# Get a specific project by ID
project_id = "singleMindServer.ABCD"
project = client.projects.by_project_id(project_id)

# Get project-level resources
project_resources = await project.get()
```

#### Working with Project Collections
```python
# Access collections within a project
collections = project.collections

# Get all collections
collections_response = await collections.get()

# Access a specific collection
collection_id = "your-collection-id"
collection = collections.by_collection_id(collection_id)
```

### Working with Collections

#### Get Collection Details
```python
collection_id = "my-collection"
collection = client.projects.by_project_id(project_id).collections.by_collection_id(collection_id)

# Get collection resources
collection_resources = await collection.get()
```

#### Get Collection Fields
```python
# Get fields (schema) for a collection
fields_response = await collection.fields.get()
```

#### Get Collection Records
```python
# Get records from a collection
records_response = await collection.records.get()
```

### Searching Records

#### Basic Search
```python
from SwaClient.models.search_request import SearchRequest

# Create a search request
search_request = SearchRequest()
search_request.query = "your search query"
search_request.start = 0
search_request.rows = 10

# Execute the search
search_response = await collection.search.post(search_request)
```

#### Search with Filters
```python
from SwaClient.models.search_request import SearchRequest
from SwaClient.models.query_parameter import QueryParameter

# Create a search request with filters
search_request = SearchRequest()
search_request.query = "*:*"  # Match all
search_request.filter_queries = [
    QueryParameter(name="field1", value="value1"),
    QueryParameter(name="field2", value="value2")
]

search_response = await collection.search.post(search_request)
```

### Managing Records

#### Create/Update Records
```python
from SwaClient.models.change_request import ChangeRequest
from SwaClient.models.record import Record
from SwaClient.models.field import Field

# Start a transaction
start_transaction_request = StartTransactionRequest()
transaction_result = await collection.changes.start_transaction.post(start_transaction_request)

# Create a change request
change_request = ChangeRequest()
change_request.records = [
    Record(
        id="record-1",
        fields=[
            Field(name="title", value="My Title"),
            Field(name="description", value="My Description")
        ]
    )
]

# Apply the changes
change_result = await collection.changes.post(change_request)

# Finish the transaction
finish_transaction_request = FinishTransactionRequest()
finish_transaction_request.transaction_id = transaction_result.transaction_id
await collection.changes.finish_transaction.post(finish_transaction_request)
```

#### Delete Records
```python
from SwaClient.models.change_request import ChangeRequest
from SwaClient.models.change_request_type import ChangeRequestType

# Create a delete request
change_request = ChangeRequest()
change_request.type = ChangeRequestType.DELETE
change_request.record_ids = ["record-1", "record-2"]

# Execute the delete
change_result = await collection.changes.post(change_request)
```

### Logout

```python
# End the session (uses HTTP DELETE)
logout_response = await client.logout.delete()
print("Logged out successfully")

# Session is automatically cleared if using SessionCapturingHttpClient
```

## API Structure

The client follows a fluent API pattern that mirrors the REST API structure:

```
SwaClient
├── login              # Authentication
├── logout             # Session termination
└── projects           # Project operations
    └── {projectId}
        └── collections    # Collection operations
            └── {collectionId}
                ├── fields         # Schema/field definitions
                ├── records        # Record CRUD operations
                ├── search         # Search operations
                ├── changes        # Change management
                ├── measures       # Analytics/measures
                ├── filters        # Filter management
                └── cached_searches # Saved searches
```

## Error Handling

The client uses Kiota's error handling mechanisms. Wrap API calls in try-except blocks:

```python
try:
    projects = await client.projects.get()
except Exception as e:
    print(f"Error retrieving projects: {e}")
    # Handle error appropriately
```

### Common Error Scenarios

1. **401 Unauthorized**: 
   - ✅ **Fixed**: Use `request.headers.try_add()` not `request.request_headers`
   - Check your credentials are correct
   - Ensure session is being captured and reused

2. **HTTP/2 Protocol Errors** (`RemoteProtocolError`):
   - ✅ **Fixed**: Set `http2=False` in `httpx.AsyncClient`
   - The API may not fully support HTTP/2

3. **SSL Certificate Errors**:
   - ✅ **Fixed**: Set `verify=False` for self-signed certificates (dev only)
   - For production, provide path to certificate file

4. **JSON Parsing Error** ("Content type application/json does not have a factory registered"):
   - ✅ **Fixed**: Register `JsonParseNodeFactory()` at startup

5. **Not Found (404)**: Verify project/collection IDs are correct

6. **Bad Request (400)**: Validate your request payload

7. **Server Errors (5xx)**: Check API endpoint availability

## Advanced Usage

### Custom Request Configuration

```python
from kiota_abstractions.base_request_configuration import RequestConfiguration

# Create custom configuration
config = RequestConfiguration()
config.headers.try_add("Custom-Header", "value")

# Use with any request
response = await client.projects.get(config)
```

**Note**: Session management is automatic when using `SessionCapturingHttpClient`, so you don't need to manually add SWA-SESSION headers.

### Working with Transactions

```python
from SwaClient.models.start_transaction_request import StartTransactionRequest
from SwaClient.models.finish_transaction_request import FinishTransactionRequest

# Start a transaction
start_req = StartTransactionRequest()
transaction = await collection.changes.start_transaction.post(start_req)
transaction_id = transaction.transaction_id

try:
    # Perform multiple changes within the transaction
    # ... your changes here ...
    
    # Commit the transaction
    finish_req = FinishTransactionRequest()
    finish_req.transaction_id = transaction_id
    finish_req.commit = True
    await collection.changes.finish_transaction.post(finish_req)
    
except Exception as e:
    # Rollback on error
    finish_req = FinishTransactionRequest()
    finish_req.transaction_id = transaction_id
    finish_req.commit = False
    await collection.changes.finish_transaction.post(finish_req)
    raise
```

### Pagination

```python
# Fetch records with pagination
start = 0
rows = 100

while True:
    config = RequestConfiguration()
    config.query_parameters["start"] = start
    config.query_parameters["rows"] = rows
    
    response = await collection.records.get(config)
    
    # Process response
    # ... your processing logic ...
    
    # Check if there are more results
    if len(response.records) < rows:
        break
    
    start += rows
```

### Working with Binary Data

```python
# Upload binary data (e.g., attachments)
binary_data = b"your binary content"
await collection.binary.post(binary_data)

# Download binary data
binary_response = await collection.binary.get()
```

## Models

The library includes comprehensive model classes in the `SwaClient.models` package:

- **Authentication**: `LoginResult`, `LogoutResult`
- **Projects**: `Project`, `ProjectsResult`, `ProjectResource`
- **Collections**: `Collection`, `CollectionsResult`, `CollectionResource`
- **Records**: `Record`, `RecordData`, `Field`, `FieldValue`
- **Search**: `SearchRequest`, `SearchResult`, `SearchResultHighlight`
- **Changes**: `ChangeRequest`, `ChangeResult`, `TransactionRequest`
- **And many more...**

## Contributing

This library is auto-generated from an OpenAPI specification using Kiota. To regenerate or update:

1. Install Kiota CLI
2. Run the generation command with your OpenAPI spec
3. Review and test the generated code

## Troubleshooting

Running into issues? We've documented all the fixes:

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide
- **[AUTHENTICATION_FIX.md](AUTHENTICATION_FIX.md)** - How we fixed the authentication issue
- **[SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md)** - Automatic session capture and reuse
- **[FIXES_SUMMARY.md](FIXES_SUMMARY.md)** - Summary of all issues fixed

Common issues we've already fixed:
- ✅ HTTP/2 protocol errors → Use `http2=False`
- ✅ SSL certificate issues → Use `verify=False` (dev) or provide cert path
- ✅ Authentication (401) errors → Use `request.headers.try_add()`
- ✅ JSON parsing errors → Register `JsonParseNodeFactory`
- ✅ Session management → Use `SessionCapturingHttpClient`

## Support

For issues related to:
- **The generated client**: Check your OpenAPI specification
- **Kiota itself**: Visit [Kiota GitHub repository](https://github.com/microsoft/kiota)
- **The API**: Consult your Search Web API documentation

## License

This client library is generated based on your API specification. Check your organization's licensing requirements.

---

**Note**: This is a Kiota-generated client. All API calls are asynchronous and require the use of `async`/`await` patterns in Python.
