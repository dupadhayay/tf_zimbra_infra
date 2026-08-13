import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
api_key = os.environ["AZURE_SEARCH_API_KEY"]
index_name = os.environ["AZURE_SEARCH_INDEX"]

credential = AzureKeyCredential(api_key)

client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=credential
)

print("Azure AI Search connection successful")