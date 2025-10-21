---
title: Getting Started
description: Complete guide to using KohakuHub - from installation to advanced features
icon: i-carbon-rocket
---

# Getting Started with KohakuHub

Everything you need to start using KohakuHub.

---

## 🚀 Quick Setup

### 1. Create Account

1. Visit your KohakuHub instance
2. Click **Register**
3. Enter username, email, password
4. If invitation-only: Use invitation link
5. Log in

### 2. Create Access Token

1. Settings → Access Tokens
2. Create New Token
3. Name it (e.g., "Dev Machine")
4. Copy token (can't view again!)

### 3. Configure CLI

```bash
export HF_ENDPOINT=http://your-kohakuhub-instance:28080
export HF_TOKEN=your_token_here

# Permanent
echo 'export HF_ENDPOINT=http://localhost:28080' >> ~/.bashrc
```

---

## 📦 CLI Tools

### huggingface-cli

```bash
pip install -U huggingface_hub
huggingface-cli login
huggingface-cli download username/model-name
huggingface-cli upload username/model-name file.safetensors
```

### kohub-cli

```bash
pip install -e .  # From KohakuHub repo
kohub-cli interactive  # TUI mode
kohub-cli repo create username/model --type model
kohub-cli org create my-team
```

---

## 🐍 Python API

```python
import os
os.environ['HF_ENDPOINT'] = 'http://localhost:28080'
os.environ['HF_TOKEN'] = 'your_token'

from huggingface_hub import HfApi
api = HfApi()

# Upload
api.upload_file(
    path_or_fileobj="model.safetensors",
    path_in_repo="model.safetensors",
    repo_id="username/my-model"
)

# Download
from huggingface_hub import hf_hub_download
path = hf_hub_download(repo_id="username/model", filename="config.json")
```

---

## 🔄 Git Clone

```bash
git clone http://localhost:28080/username/repo.git
cd repo
git lfs install
git lfs pull  # Get large files
```

---

## 🌐 Web Features

- Create repos via UI
- Upload via drag-drop
- Browse files and commits
- View YAML metadata
- Like repositories
- Join organizations

See full details in [Features](/docs/features)
