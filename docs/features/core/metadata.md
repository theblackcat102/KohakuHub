---
title: YAML Metadata
description: Comprehensive metadata system using YAML frontmatter in README.md files
icon: i-carbon-information
---

# YAML Metadata & Repository Cards

Comprehensive metadata system using YAML frontmatter in README.md files.

---

## Overview

KohakuHub parses YAML frontmatter from README.md and displays it beautifully:

**Metadata Tab shows:**
- License with documentation links
- Languages (all languages, not just first 3)
- Framework & pipeline tags (models)
- Base models with clickable links
- Training datasets with clickable links
- Task categories (datasets)
- Size category (datasets)
- Evaluation metrics
- All other fields in individual cards

---

## Supported Fields

### All Repository Types

```yaml
---
license: mit                    # License identifier
language:                       # Language codes
  - en
  - zh
tags:                          # General tags
  - computer-vision
  - pytorch
---
```

### Models

```yaml
---
library_name: transformers     # Framework
pipeline_tag: text-classification  # Task type
base_model:                    # Parent model(s)
  - bert-base-uncased
datasets:                      # Training datasets
  - glue
  - imdb
metrics:                       # Evaluation metrics
  - accuracy
  - f1
eval_results:                  # Structured evaluation
  - task: text-classification
    dataset: sst2
    metrics:
      accuracy: 0.953
      f1: 0.948
---
```

### Datasets

```yaml
---
task_categories:               # Task types
  - image-classification
  - text-to-image
size_categories: 1M<n<10M     # Dataset size
multilinguality: monolingual   # Language type
annotations_creators:          # How annotated
  - expert-generated
source_datasets:               # Source
  - original
---
```

---

## Display System

### Metadata Header (Top Bar)

**Shows key info as badges:**
- License (e.g., MIT License)
- Languages (up to 3, then "+N more")
- Framework (models)
- Pipeline tag (models)
- Size (datasets - prominent red badge)
- Task categories (up to 2, then "+N more")

**Clicking "+N more"** → Navigates to Metadata tab

### Metadata Tab (Full Grid)

**Organized as individual cards:**

**Models:**
- License Card
- Languages Card (all languages)
- Framework Card (library + pipeline)
- Base Model Card (clickable links to models)
- Training Datasets Card (clickable links)
- Metrics Card (evaluation results table)

**Datasets:**
- License Card
- Languages Card
- Task Categories Card (all tasks as badges)
- Size Card (large badge)
- Multilinguality Card
- Annotations Card
- Source Card

**All types:**
- Additional fields shown as individual cards
- Arrays → Badge lists
- Objects → JSON code blocks
- Strings → Plain text

---

## Tag Filtering

**Metadata tags filtered out from "Tags" display:**

**Removed prefixes:**
- `dataset:*`, `license:*`, `region:*`
- `task_categories:*`, `size_categories:*`
- `format:*`, `modality:*`
- `diffusers:*`, `transformers:*`
- `endpoints_compatible`, `autotrain_compatible`

**Special handling:**
- `dataset:user/dataset-name` → Moved to "Referenced Datasets" card
- Clean tags show: "art", "anime", "stable-diffusion" (meaningful tags only)

---

## Referenced Datasets

**Extract from tags:**

Tags like `dataset:KBlueLeaf/danbooru2023` become:
- Sidebar card: "Referenced Datasets"
- Clickable links to each dataset
- Expandable (shows 3, then "Show N more")

---

## Examples

### Complete Model Card

```yaml
---
license: apache-2.0
language:
  - en
  - zh
library_name: transformers
pipeline_tag: text-classification
base_model: bert-base-uncased
datasets:
  - glue
  - imdb
metrics:
  - accuracy
tags:
  - sentiment-analysis
  - nlp
  - pytorch
---

# My Sentiment Classifier

This model classifies text sentiment...
```

### Complete Dataset Card

```yaml
---
license: cc-by-4.0
language: en
task_categories:
  - image-classification
  - text-to-image
size_categories: 1M<n<10M
multilinguality: monolingual
annotations_creators: expert-generated
source_datasets: original
tags:
  - art
  - anime
dataset:KBlueLeaf/danbooru2023-webp
---

# My Dataset

Contains 5M images...
```

---

## Frontend Components

**MarkdownViewer:**
- Strips YAML frontmatter before rendering
- Parses frontmatter separately
- Content displayed without metadata block

**MetadataHeader:**
- Horizontal badges above tabs
- Shows only most important fields
- Clickable "+N more" badges

**DetailedMetadataPanel:**
- Grid of individual cards
- Each field in its own card
- Clean, organized layout

**SidebarRelationshipsCard:**
- Author always shown
- Base models (if any)
- Training datasets (if any)
- Expandable lists (shows 2, then more)

---

## API Access

**Get parsed metadata:**

Metadata is returned in repo info responses:

```bash
# Get repo info (doesn't include metadata)
curl http://localhost:28080/api/models/username/repo

# Get tree (doesn't include metadata)
curl http://localhost:28080/api/models/username/repo/tree/main

# Download README to parse yourself
curl http://localhost:28080/models/username/repo/resolve/main/README.md
```

**Client-side parsing:**
- Frontend fetches README.md
- Parses YAML using js-yaml library
- Normalizes arrays (string|string[] → string[])
- Filters specialized vs general fields

---

See also: [Repository Management](../getting-started/first-repository.md), [Web UI](../getting-started/web-ui.md)
