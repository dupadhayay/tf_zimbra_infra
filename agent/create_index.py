import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
)


endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
api_key = os.environ["AZURE_SEARCH_API_KEY"]

index_name = "terraform-policies"

credential = AzureKeyCredential(api_key)

index_client = SearchIndexClient(
    endpoint=endpoint,
    credential=credential
)

fields = [
    SimpleField(
        name="id",
        type=SearchFieldDataType.String,
        key=True
    ),

    SearchField(
        name="title",
        type=SearchFieldDataType.String,
        searchable=True
    ),

    SearchField(
        name="content",
        type=SearchFieldDataType.String,
        searchable=True
    ),

    SearchField(
        name="category",
        type=SearchFieldDataType.String,
        searchable=True,
        filterable=True
    )
]

index = SearchIndex(
    name=index_name,
    fields=fields
)

result = index_client.create_or_update_index(index)

print(f"Index created successfully: {result.name}")