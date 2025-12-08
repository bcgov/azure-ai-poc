# Azure HTTP Client

This folder contains `.http` files for interacting with Azure services directly from VS Code using the [REST Client extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client).

## Prerequisites

1. Install the **REST Client** extension in VS Code:
   - Extension ID: `humao.rest-client`

2. Configure your environment variables in each service's `.env` file

## Folder Structure

```
http_client/
├── README.md
├── azure-openai/
│   ├── .env              # Azure OpenAI credentials
│   └── openai.http       # Chat completions, embeddings, models
├── azure-search/
│   ├── .env              # Azure AI Search credentials
│   └── search.http       # Search, vector search, indexing
├── cosmos-db/
│   ├── .env              # Cosmos DB credentials
│   └── cosmos.http       # Documents, queries
└── document-intelligence/
    ├── .env              # Document Intelligence credentials
    └── document.http     # Analyze documents
```

## Usage

1. Navigate to any `.http` file
2. Update the corresponding `.env` file with your credentials
3. Click "Send Request" above any request block
4. View the response in the split pane

## Security Notes

- All `.env` files in this folder are gitignored
- Never commit API keys or secrets
- Use Azure Key Vault for production environments

## API References

- [Azure OpenAI REST API](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference)
- [Azure AI Search REST API](https://learn.microsoft.com/en-us/rest/api/searchservice/)
- [Cosmos DB REST API](https://learn.microsoft.com/en-us/rest/api/cosmos-db/)
- [Document Intelligence REST API](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/reference/rest-api-guide)
