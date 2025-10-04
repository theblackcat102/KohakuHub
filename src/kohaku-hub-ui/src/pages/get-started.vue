<!-- src/pages/get-started.vue -->
<script setup>
import MarkdownPage from "@/components/common/MarkdownPage.vue";

const baseUrl = window.location.origin;

const content = `# Get Started with KohakuHub

Welcome to KohakuHub! This guide will help you get started with using KohakuHub to download and upload models, datasets, and spaces.

## Quick Start

### 1. Create an Account

First, you'll need to create an account on this KohakuHub instance:

1. Click the **Register** button in the navigation bar
2. Fill in your username, email, and password
3. Submit the registration form
4. Log in with your credentials

### 2. Get Your Access Token

Access tokens are required to interact with KohakuHub programmatically:

1. Log in to your account
2. Navigate to **Settings** (click your username in the top right, then **Settings**)
3. Go to the **Access Tokens** section
4. Click **Create New Token**
5. Give your token a name (e.g., "My Dev Machine")
6. Copy the token and save it securely - you won't be able to see it again!

### 3. Set Up Your Environment

Before using the CLI tools, set the endpoint to point to this KohakuHub instance:

\`\`\`bash
# Set the HuggingFace endpoint to this KohakuHub instance
export HF_ENDPOINT=${baseUrl}

# For persistent configuration, add it to your shell profile
echo 'export HF_ENDPOINT=${baseUrl}' >> ~/.bashrc  # or ~/.zshrc
\`\`\`

## Using CLI Tools

KohakuHub is compatible with HuggingFace ecosystem tools. Here's how to use them:

### Option 1: huggingface-cli (Recommended)

The official HuggingFace CLI tool works seamlessly with KohakuHub.

#### Installation

\`\`\`bash
pip install huggingface_hub
\`\`\`

#### Login

\`\`\`bash
huggingface-cli login
\`\`\`

When prompted, paste the access token you created earlier.

#### Download a Model

\`\`\`bash
# Download a complete repository
huggingface-cli download username/model-name

# Download a specific file
huggingface-cli download username/model-name config.json

# Download to a specific directory
huggingface-cli download username/model-name --local-dir ./my-model
\`\`\`

#### Upload Files

\`\`\`bash
# Upload a file
huggingface-cli upload username/model-name ./model.safetensors

# Upload a directory
huggingface-cli upload username/model-name ./my-model --repo-type model
\`\`\`

### Option 2: hfutils

A powerful alternative from [deepghs/hfutils](https://github.com/deepghs/hfutils) with advanced features.

#### Installation

\`\`\`bash
pip install hfutils
\`\`\`

#### Usage

\`\`\`bash
# Set your token for private repositories
export HF_TOKEN=your_access_token_here

# Download a single file
hfutils download -r username/model-name -o ./local-file.txt -f remote-file.txt

# Download entire directory
hfutils download -r username/model-name -o ./local-dir -d remote-dir

# Download archived directory
hfutils download -r username/model-name -o ./local-dir -a archive.zip

# Upload a single file
hfutils upload -r username/model-name -i ./local-file.txt -f remote-file.txt

# Upload directory as tree
hfutils upload -r username/model-name -i ./local-dir -d remote-dir

# Upload directory as archive
hfutils upload -r username/model-name -i ./local-dir -a archive.zip
\`\`\`

#### Advanced Options

\`\`\`bash
# Enable transfer acceleration
export HF_HUB_ENABLE_HF_TRANSFER=1

# Specify repository type
hfutils download -r username/dataset-name -t dataset -o ./output

# Custom temporary directory
export TMPDIR=/path/to/tmp
\`\`\`

### Option 3: kohub-cli (KohakuHub Native)

KohakuHub's native CLI tool for user and organization management.

#### Installation

Currently, you need to install from source:

\`\`\`bash
# Clone the repository
git clone https://github.com/KohakuBlueleaf/KohakuHub.git
cd KohakuHub

# Install dependencies and the CLI
pip install -r requirements.txt
pip install -e .
\`\`\`

#### Usage

The CLI provides an interactive menu for managing users and organizations:

\`\`\`bash
# Run the interactive CLI
kohub-cli

# Available operations:
# - User Management: Register, Login, Create Token
# - Organization Management: Create Organization, Manage Members
\`\`\`

For file operations, use huggingface-cli or hfutils instead.

## Using the Python API

You can also use the HuggingFace Hub library directly in your Python code:

### Setup

\`\`\`python
from huggingface_hub import HfApi, login
import os

# Set the endpoint
os.environ['HF_ENDPOINT'] = '${baseUrl}'

# Login with your token
login(token="your_access_token_here")
\`\`\`

### Download Files

\`\`\`python
from huggingface_hub import hf_hub_download, snapshot_download

# Download a specific file
file_path = hf_hub_download(
    repo_id="username/model-name",
    filename="model.safetensors"
)

# Download entire repository
repo_path = snapshot_download(
    repo_id="username/model-name",
    repo_type="model"
)
\`\`\`

### Upload Files

\`\`\`python
from huggingface_hub import HfApi

api = HfApi()

# Upload a single file
api.upload_file(
    path_or_fileobj="./model.safetensors",
    path_in_repo="model.safetensors",
    repo_id="username/model-name",
    repo_type="model"
)

# Upload a folder
api.upload_folder(
    folder_path="./my-model",
    repo_id="username/model-name",
    repo_type="model"
)
\`\`\`

## Using the Web Interface

### Browse Repositories

1. Navigate to **Models**, **Datasets**, or **Spaces** from the home page
2. Browse public repositories or search for specific ones
3. Click on a repository to view its contents

### Create a Repository

1. Click the **New** button in the navigation bar
2. Choose the repository type (Model, Dataset, or Space)
3. Fill in the repository name and description
4. Choose visibility (Public or Private)
5. Click **Create Repository**

### Upload Files via Web UI

1. Navigate to your repository
2. Click the **Files** tab
3. Click **Upload Files**
4. Drag and drop your files or click to browse
5. Click **Upload** to commit the files

### Download Files

1. Navigate to any repository
2. Click the **Clone** button to see download options
3. Use the provided commands to download via CLI
4. Or click **Download** to download as a zip file (coming soon)

## Repository Types

### Models

Models are ML model repositories containing:
- Model weights (PyTorch, TensorFlow, ONNX, etc.)
- Configuration files
- Tokenizer files
- Model cards (README.md)

### Datasets

Datasets contain training or evaluation data:
- Data files (CSV, JSON, Parquet, etc.)
- Dataset scripts
- Dataset cards (README.md)

### Spaces

Spaces are applications and demos:
- Application code
- Web interfaces
- Gradio/Streamlit apps
- API endpoints

## Best Practices

### Repository Naming

- Use lowercase letters and hyphens
- Format: \`username/repo-name\`
- Be descriptive: \`username/bert-sentiment-analysis\` not \`username/model1\`

### README Files

Always include a README.md with:
- Model/dataset description
- Usage examples
- Training details
- License information
- Citation information

### Large Files

For files larger than 10MB:
- Git LFS is automatically used
- Consider splitting very large files
- Use efficient formats (safetensors, parquet)

### Versioning

- Use semantic versioning for releases
- Tag important versions
- Document changes in your README

## Troubleshooting

### Authentication Errors

If you get authentication errors:
- Verify your token is correct
- Make sure HF_ENDPOINT is set correctly
- Check that your token hasn't expired

### Download Fails

If downloads fail:
- Check your internet connection
- Verify the repository exists and is accessible
- Ensure you have permission for private repositories
- Try downloading specific files instead of the whole repo

### Upload Fails

If uploads fail:
- Verify you have write access to the repository
- Check file size limits
- Ensure your token has write permissions
- Try uploading files one at a time

## Next Steps

- **Explore**: Browse public models and datasets
- **Create**: Upload your first model or dataset
- **Collaborate**: Create an organization and invite team members
- **Deploy**: Use Spaces to deploy ML applications

Need help? Check out our [GitHub repository](https://github.com/KohakuBlueleaf/Kohaku-Hub) or join our [Discord community](https://discord.gg/xWYrkyvJ2s).
`;
</script>

<template>
  <MarkdownPage :content="content" />
</template>
