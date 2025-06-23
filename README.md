# MuleSoft Anypoint Exchange API Spec Exporter

A GitHub Action that downloads OpenAPI specifications, documentation, and metadata from MuleSoft Anypoint Exchange using the Platform API and automatically organizes them in your repository.

## Features

- Secure authentication using CLIENT_ID and CLIENT_SECRET
- Downloads OpenAPI/Swagger specifications from Exchange
- Downloads portal documentation and converts HTML to Markdown
- Exports categories, tags, and metadata as JSON
- Automatically extracts ZIP files containing specifications
- Filters to latest versions of each asset automatically
- Stores all files as GitHub Actions artifacts
- Commits downloaded files directly to repository with customizable organization
- **NEW:** Flexible file organization with custom paths for specs, docs, and metadata
- Simplified configuration using only organization ID
- Environment variable support for local development

## MuleSoft API Endpoints Used

This action uses the following MuleSoft Anypoint Platform API endpoints:

- **Authentication**: `POST /accounts/api/v2/oauth2/token` - OAuth2 client credentials flow
- **User Profile**: `GET /accounts/api/profile` - Get user organizations
- **Asset Search**: `GET /exchange/api/v2/assets` - Search for assets in Exchange
- **Asset Details**: `GET /exchange/api/v2/assets/{organizationId}/{assetId}/{version}` - Get asset metadata
- **Asset Files**: `GET /exchange/api/v2/assets/{organizationId}/{assetId}/{version}/files` - Get downloadable files
- **Portal Info**: `GET /exchange/api/v2/assets/{organizationId}/{assetId}/{version}/portal` - Get portal information
- **Portal Pages**: `GET /exchange/api/v2/assets/{organizationId}/{assetId}/{version}/portal/pages` - Get documentation pages

## Prerequisites

Before using this action, you need to:

1. **Set up MuleSoft Anypoint Platform credentials**:
   - Obtain a CLIENT_ID and CLIENT_SECRET from your Anypoint Platform
   - Add these as repository secrets in GitHub

2. **Get your Organization ID**:
   - Log into Anypoint Platform
   - Navigate to Access Management
   - Note your Organization ID

## Usage

### Basic Usage

```yaml
name: Export API Specs
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * 1' # Weekly on Monday at 2 AM

jobs:
  export:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Export API Specs
        uses: your-org/actions-export-api-spec@v1
        env:
          CLIENT_ID: ${{ secrets.CLIENT_ID }}
          CLIENT_SECRET: ${{ secrets.CLIENT_SECRET }}
        with:
          organization-id: 'your-organization-id'
```

### Advanced Usage with Custom Organization

```yaml
- name: Export API Specs with Custom Organization
  uses: your-org/actions-export-api-spec@v1
  env:
    CLIENT_ID: ${{ secrets.CLIENT_ID }}
    CLIENT_SECRET: ${{ secrets.CLIENT_SECRET }}
  with:
    organization-id: 'your-organization-id'
    asset-id: 'specific-api'                    # Optional: Download specific asset
    repository-destination: '.'                 # Repository root
    documentation-path: 'docs/api-guides'      # Custom docs location
    categories-path: 'metadata'                # Custom metadata location  
    specs-path: 'api-specifications'           # Custom specs location
    include-metadata: 'true'
```

## Input Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `organization-id` | MuleSoft Organization ID | Yes | - |
| `asset-id` | Specific Asset ID to download (optional) | No | - |
| `exchange-url` | MuleSoft Anypoint Exchange URL | No | `https://anypoint.mulesoft.com` |
| `output-directory` | Temporary directory for downloads | No | `api-specs` |
| `include-metadata` | Download categories and metadata | No | `true` |
| `repository-destination` | Repository directory for files | No | `.` |
| `documentation-path` | Custom path for documentation files | No | `''` |
| `categories-path` | Custom path for categories.json | No | `.` |
| `specs-path` | Custom path for OpenAPI specifications | No | `.` |

## Repository Organization

The action organizes downloaded files based on your configuration:

### Default Organization
```
repository-root/
├── documentation/           # Markdown documentation files
│   ├── Content Paged.md
│   ├── API Guide.md
│   └── User Manual.md
├── categories.json          # Categories and metadata
└── openapi-spec.yaml        # OpenAPI specifications
```

### Custom Organization Example
```yaml
# Configuration:
documentation-path: 'docs/api-guides'
categories-path: 'metadata'  
specs-path: 'api-specifications'
```

```
repository-root/
├── documentation/
│   └── docs/
│       └── api-guides/      # Custom documentation location
│           ├── Content Paged.md
│           └── API Guide.md
├── metadata/                # Custom metadata location
│   └── categories.json
└── api-specifications/      # Custom specifications location
    ├── customer-api.yaml
    └── order-api.yml
```

## Environment Variables

For local development, create a `.env` file:

```bash
# Required
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
ORGANIZATION_ID=your-org-id

# Optional
EXCHANGE_URL=https://anypoint.mulesoft.com
ASSET_ID=specific-asset-id
OUTPUT_DIR=api-specs
INCLUDE_DOCS=true
INCLUDE_METADATA=true
```

## Outputs

| Output | Description |
|--------|-------------|
| `specs-count` | Number of OpenAPI specifications downloaded |
| `docs-count` | Number of documentation items downloaded |
| `categories-count` | Number of unique categories extracted |
| `output-path` | Path where files were saved |

## Setting up Repository Secrets

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add the following secrets:
   - Name: `CLIENT_ID`, Value: Your MuleSoft Client ID
   - Name: `CLIENT_SECRET`, Value: Your MuleSoft Client Secret

## Getting MuleSoft Credentials

1. Log into [Anypoint Platform](https://anypoint.mulesoft.com)
2. Go to Access Management
3. Navigate to Connected Apps
4. Create a new Connected App or use an existing one
5. Note the Client ID and Client Secret
6. Ensure the app has the necessary scopes for Exchange access

## Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your credentials
4. Run the script: `python download_specs.py`

## File Processing Features

### Automatic ZIP Extraction
- Detects ZIP files by magic bytes (PK headers)
- Automatically extracts contents to `{filename}_extracted/` directory
- Removes original ZIP file after successful extraction

### Documentation Conversion
- Downloads HTML portal pages from MuleSoft Exchange
- Converts HTML content to clean Markdown format
- Preserves original spacing and formatting
- Saves both JSON metadata and Markdown files

### Categories Extraction
- Automatically extracts categories from asset metadata
- Consolidates unique categories across all assets
- Outputs structured JSON with `tagKey` and `value` properties

## Troubleshooting

### Authentication Issues
- Verify your CLIENT_ID and CLIENT_SECRET are correct
- Ensure your Connected App has the right permissions
- Check that your organization ID is correct

### No Assets Found
- Verify the organization ID is correct
- Check if you have access to the specified assets
- Try removing asset-id filter to see all available assets

### Download Failures
- Check network connectivity
- Verify the Exchange URL is accessible
- Look for rate limiting issues in the logs

### Path Configuration Issues
- Ensure custom paths don't conflict with existing repository structure
- Use `.` for root-level placement
- Documentation files are always placed under `documentation/` folder

## Complete Example Workflow

Here's a comprehensive example that demonstrates all features:

```yaml
name: Weekly API Spec Export

on:
  schedule:
    - cron: '0 2 * * 1' # Every Monday at 2 AM
  workflow_dispatch:
    inputs:
      organization_id:
        description: 'Organization ID'
        required: true
        type: string
      asset_id:
        description: 'Specific Asset (optional)'
        required: false
        type: string

jobs:
  export-api-specs:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Export API Specs from MuleSoft Exchange
        uses: your-org/actions-export-api-spec@v1
        id: export
        env:
          CLIENT_ID: ${{ secrets.CLIENT_ID }}
          CLIENT_SECRET: ${{ secrets.CLIENT_SECRET }}
        with:
          organization-id: ${{ github.event.inputs.organization_id || vars.MULESOFT_ORG_ID }}
          asset-id: ${{ github.event.inputs.asset_id }}
          repository-destination: '.'
          documentation-path: 'docs/mulesoft-apis'
          categories-path: 'metadata'
          specs-path: 'api-specifications'
          include-metadata: 'true'
      
      - name: Display results
        run: |
          echo "Export completed successfully!"
          echo "Downloaded ${{ steps.export.outputs.specs-count }} API specifications"
          echo "Downloaded ${{ steps.export.outputs.docs-count }} documentation items"
          echo "Extracted ${{ steps.export.outputs.categories-count }} categories"
          echo "Files organized in repository"
          echo ""
          echo "Repository structure:"
          find . -name "*.yaml" -o -name "*.yml" -o -name "*.md" -o -name "categories.json" | head -10
```

## Migration from Previous Versions

### Removed Parameters
- `group-id`: No longer needed, uses `organization-id` directly
- `include-documentation`: Documentation is now always downloaded

### New Parameters
- `documentation-path`: Customize documentation location
- `categories-path`: Customize categories.json location  
- `specs-path`: Customize OpenAPI specifications location

### Updated Environment Variables
- `GROUP_ID`: Removed (use `ORGANIZATION_ID`)
- `INCLUDE_DOCS`: Always `true` (documentation always downloaded)

## License

This action is available under the MIT License. See LICENSE file for details.
