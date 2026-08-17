import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
api_key = os.environ["AZURE_SEARCH_API_KEY"]
index_name = "terraform-policies"

credential = AzureKeyCredential(api_key)

client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=credential
)


query = "production SSH public internet"


results = client.search(
    search_text=query,
    top=3
)


print("\n===== Relevant Policies =====\n")

for result in results:

    print("Title:", result["title"])
    print("Category:", result["category"])
    print("Score:", result["@search.score"])
    print("Content:")
    print(result["content"])
    print("-" * 60)