---
title: Statistics API
description: Track repository downloads, likes, and trending models
icon: chart-bar
---

# Statistics API

Track repository statistics including downloads, likes, and discover trending repositories.

## Overview

KohakuHub provides comprehensive statistics tracking:

- **Download tracking**: Session-based downloads (not individual file downloads)
- **Daily aggregation**: Historical download data by day
- **Like/favorite counting**: Track repository popularity
- **Trending algorithm**: Discover popular repositories by recent activity
- **Lazy aggregation**: Historical stats aggregated on-demand for performance

---

## Endpoints

### Get Repository Stats

Get basic statistics for a repository (downloads and likes).

**Endpoint:** `GET /{repo_type}s/{namespace}/{name}/stats`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `repo_type` | string | path | Yes | Repository type: `model`, `dataset`, or `space` |
| `namespace` | string | path | Yes | Repository namespace |
| `name` | string | path | Yes | Repository name |

**Authentication:** Optional (required for private repositories)

**Response:**

```json
{
  "downloads": 1234567,
  "likes": 89
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `downloads` | integer | Total download sessions (all time) |
| `likes` | integer | Number of users who liked this repository |

**Notes:**

- Downloads are counted by **session**, not individual files
- A session includes all files downloaded within a short time window
- Statistics are automatically aggregated when accessed
- Today's stats are real-time; historical stats use lazy aggregation

**Example:**

```python
import requests

response = requests.get(
    "http://localhost:28080/models/myorg/mymodel/stats"
)
stats = response.json()

print(f"Downloads: {stats['downloads']:,}")
print(f"Likes: {stats['likes']}")
```

---

### Get Recent Statistics

Get detailed download statistics for recent days.

**Endpoint:** `GET /{repo_type}s/{namespace}/{name}/stats/recent`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `repo_type` | string | path | Yes | Repository type: `model`, `dataset`, or `space` |
| `namespace` | string | path | Yes | Repository namespace |
| `name` | string | path | Yes | Repository name |
| `days` | integer | query | No | Number of days to retrieve (1-365, default: 30) |

**Authentication:** Optional (required for private repositories)

**Response:**

```json
{
  "stats": [
    {
      "date": "2025-01-15",
      "downloads": 123,
      "authenticated": 45,
      "anonymous": 78,
      "files": 456
    },
    {
      "date": "2025-01-16",
      "downloads": 145,
      "authenticated": 52,
      "anonymous": 93,
      "files": 512
    }
  ],
  "period": {
    "start": "2025-01-01",
    "end": "2025-01-30",
    "days": 30
  }
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | Date in YYYY-MM-DD format |
| `downloads` | integer | Download sessions for this day |
| `authenticated` | integer | Sessions from authenticated users |
| `anonymous` | integer | Sessions from anonymous users |
| `files` | integer | Total files downloaded |

**Use Cases:**

- Generate download charts
- Analyze usage patterns
- Track growth over time
- Compare weekday vs. weekend usage

**Example:**

```python
import requests
import matplotlib.pyplot as plt

# Get last 30 days
response = requests.get(
    "http://localhost:28080/models/myorg/mymodel/stats/recent",
    params={"days": 30}
)
data = response.json()

# Extract data for plotting
dates = [s["date"] for s in data["stats"]]
downloads = [s["downloads"] for s in data["stats"]]

# Plot
plt.figure(figsize=(12, 6))
plt.plot(dates, downloads, marker='o')
plt.xlabel("Date")
plt.ylabel("Downloads")
plt.title("Download Trend (Last 30 Days)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

---

### Get Trending Repositories

Discover trending repositories based on recent downloads.

**Endpoint:** `GET /api/trending`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `repo_type` | string | query | No | Filter by type: `model`, `dataset`, or `space` (default: `model`) |
| `days` | integer | query | No | Calculate trend based on last N days (1-90, default: 7) |
| `limit` | integer | query | No | Maximum repositories to return (1-100, default: 20) |

**Authentication:** Optional (affects private repository visibility)

**Response:**

```json
{
  "trending": [
    {
      "id": "openai/gpt-4",
      "type": "model",
      "downloads": 5678900,
      "likes": 1234,
      "recent_downloads": 12345,
      "private": false
    },
    {
      "id": "myorg/popular-dataset",
      "type": "dataset",
      "downloads": 234567,
      "likes": 89,
      "recent_downloads": 8901,
      "private": false
    }
  ],
  "period": {
    "start": "2025-01-09",
    "end": "2025-01-16",
    "days": 7
  }
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Repository full ID (`namespace/name`) |
| `type` | string | Repository type |
| `downloads` | integer | Total downloads (all time) |
| `likes` | integer | Total likes |
| `recent_downloads` | integer | Downloads in the specified period |
| `private` | boolean | Whether repository is private |

**Trending Algorithm:**

Repositories are ranked by `recent_downloads` (downloads in the last N days).

**Privacy:**

- Public repositories: Visible to everyone
- Private repositories: Only visible to users with read permission
- Anonymous users only see public trending repos

**Example:**

```python
# Get top 10 trending models (last 7 days)
response = requests.get(
    "http://localhost:28080/api/trending",
    params={
        "repo_type": "model",
        "days": 7,
        "limit": 10
    }
)
trending = response.json()

print("Top Trending Models:")
for i, repo in enumerate(trending["trending"], 1):
    print(f"{i}. {repo['id']}")
    print(f"   Recent downloads: {repo['recent_downloads']:,}")
    print(f"   Total downloads: {repo['downloads']:,}")
    print(f"   Likes: {repo['likes']}")
    print()

# Get trending datasets (last 30 days)
response = requests.get(
    "http://localhost:28080/api/trending",
    params={
        "repo_type": "dataset",
        "days": 30,
        "limit": 20
    }
)
```

---

## Usage Examples

### Comprehensive Statistics Dashboard

```python
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:28080"
TOKEN = "YOUR_TOKEN"

headers = {"Authorization": f"Bearer {TOKEN}"}

class StatsAnalyzer:
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def get_repo_stats(self, repo_type: str, namespace: str, name: str):
        """Get basic repository statistics."""
        response = requests.get(
            f"{self.base_url}/{repo_type}s/{namespace}/{name}/stats",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_recent_stats(self, repo_type: str, namespace: str, name: str, days: int = 30):
        """Get recent daily statistics."""
        response = requests.get(
            f"{self.base_url}/{repo_type}s/{namespace}/{name}/stats/recent",
            params={"days": days},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_trending(self, repo_type: str = "model", days: int = 7, limit: int = 20):
        """Get trending repositories."""
        response = requests.get(
            f"{self.base_url}/api/trending",
            params={
                "repo_type": repo_type,
                "days": days,
                "limit": limit
            },
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def analyze_growth(self, repo_type: str, namespace: str, name: str, days: int = 30):
        """Analyze repository growth trends."""
        data = self.get_recent_stats(repo_type, namespace, name, days)
        stats = data["stats"]

        if not stats:
            return None

        # Calculate growth metrics
        first_day = stats[0]["downloads"]
        last_day = stats[-1]["downloads"]
        total = sum(s["downloads"] for s in stats)
        avg_daily = total / len(stats)

        # Calculate week-over-week growth
        mid_point = len(stats) // 2
        first_half = sum(s["downloads"] for s in stats[:mid_point])
        second_half = sum(s["downloads"] for s in stats[mid_point:])

        growth_rate = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0

        return {
            "total_downloads": total,
            "avg_daily_downloads": avg_daily,
            "growth_rate_percent": growth_rate,
            "first_day": first_day,
            "last_day": last_day,
            "trend": "up" if last_day > first_day else "down" if last_day < first_day else "stable"
        }

    def compare_auth_vs_anon(self, repo_type: str, namespace: str, name: str, days: int = 30):
        """Compare authenticated vs anonymous downloads."""
        data = self.get_recent_stats(repo_type, namespace, name, days)
        stats = data["stats"]

        total_auth = sum(s["authenticated"] for s in stats)
        total_anon = sum(s["anonymous"] for s in stats)
        total = total_auth + total_anon

        return {
            "authenticated": total_auth,
            "anonymous": total_anon,
            "authenticated_percent": (total_auth / total * 100) if total > 0 else 0,
            "anonymous_percent": (total_anon / total * 100) if total > 0 else 0
        }

    def print_summary(self, repo_type: str, namespace: str, name: str):
        """Print comprehensive statistics summary."""
        repo_id = f"{namespace}/{name}"
        print(f"\n=== Statistics Summary: {repo_id} ===\n")

        # Basic stats
        basic = self.get_repo_stats(repo_type, namespace, name)
        print(f"Total Downloads: {basic['downloads']:,}")
        print(f"Likes: {basic['likes']:,}")

        # Growth analysis
        growth = self.analyze_growth(repo_type, namespace, name, 30)
        if growth:
            print(f"\n30-Day Trends:")
            print(f"  Average daily: {growth['avg_daily_downloads']:.1f}")
            print(f"  Growth rate: {growth['growth_rate_percent']:+.1f}%")
            print(f"  Trend: {growth['trend']}")

        # Auth vs Anon
        auth_data = self.compare_auth_vs_anon(repo_type, namespace, name, 30)
        print(f"\nUser Distribution (30 days):")
        print(f"  Authenticated: {auth_data['authenticated_percent']:.1f}%")
        print(f"  Anonymous: {auth_data['anonymous_percent']:.1f}%")

# Usage
analyzer = StatsAnalyzer(BASE_URL, TOKEN)

# Get comprehensive summary
analyzer.print_summary("model", "myorg", "mymodel")

# Analyze growth
growth = analyzer.analyze_growth("model", "myorg", "mymodel", 90)
print(f"90-day growth: {growth['growth_rate_percent']:+.1f}%")

# Get trending
trending = analyzer.get_trending("model", days=7, limit=10)
print(f"\nTop 10 trending models:")
for i, repo in enumerate(trending["trending"], 1):
    print(f"{i}. {repo['id']}: {repo['recent_downloads']:,} downloads")
```

### Export Statistics to CSV

```python
import csv
from datetime import datetime

def export_stats_to_csv(repo_type: str, namespace: str, name: str,
                       days: int = 30, filename: str = None):
    """Export repository statistics to CSV file."""

    response = requests.get(
        f"{BASE_URL}/{repo_type}s/{namespace}/{name}/stats/recent",
        params={"days": days},
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    data = response.json()

    if not filename:
        filename = f"{namespace}_{name}_stats_{datetime.now():%Y%m%d}.csv"

    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ["date", "downloads", "authenticated", "anonymous", "files"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for stat in data["stats"]:
            writer.writerow(stat)

    print(f"Exported statistics to {filename}")
    return filename

# Usage
export_stats_to_csv("model", "myorg", "mymodel", days=90)
```

### Monitor Trending Repositories

```python
def monitor_trending(repo_type: str = "model", top_n: int = 10):
    """Monitor and report trending repositories."""

    response = requests.get(
        f"{BASE_URL}/api/trending",
        params={
            "repo_type": repo_type,
            "days": 7,
            "limit": top_n
        }
    )
    trending = response.json()

    print(f"\n{'='*60}")
    print(f"Top {top_n} Trending {repo_type.title()}s (Last 7 Days)")
    print(f"{'='*60}\n")

    for i, repo in enumerate(trending["trending"], 1):
        print(f"{i:2d}. {repo['id']}")
        print(f"    Recent: {repo['recent_downloads']:>8,} downloads")
        print(f"    Total:  {repo['downloads']:>8,} downloads")
        print(f"    Likes:  {repo['likes']:>8,}")
        print()

# Usage
monitor_trending("model", top_n=10)
monitor_trending("dataset", top_n=5)
```

### Weekly Report Generator

```python
def generate_weekly_report(namespace: str, token: str):
    """Generate weekly statistics report for all repositories in namespace."""

    # Get all repositories
    from kohakuhub.api.repo import list_repositories  # Assuming you have this

    analyzer = StatsAnalyzer(BASE_URL, token)

    print(f"\n{'='*70}")
    print(f"Weekly Statistics Report - {namespace}")
    print(f"{'='*70}\n")

    # This would list all repos - simplified example
    repos = [
        ("model", "mymodel"),
        ("dataset", "mydataset")
    ]

    total_downloads = 0
    total_likes = 0

    for repo_type, name in repos:
        try:
            basic = analyzer.get_repo_stats(repo_type, namespace, name)
            growth = analyzer.analyze_growth(repo_type, namespace, name, 7)

            total_downloads += basic["downloads"]
            total_likes += basic["likes"]

            print(f"{repo_type}/{namespace}/{name}")
            print(f"  Downloads: {basic['downloads']:,} (7-day: {growth['total_downloads']:,})")
            print(f"  Likes: {basic['likes']:,}")
            print(f"  Trend: {growth['trend']} ({growth['growth_rate_percent']:+.1f}%)")
            print()

        except Exception as e:
            print(f"  Error: {e}\n")

    print(f"{'='*70}")
    print(f"Total Downloads: {total_downloads:,}")
    print(f"Total Likes: {total_likes:,}")
    print(f"{'='*70}\n")

# Usage
generate_weekly_report("myorg", TOKEN)
```

---

## JavaScript/TypeScript Example

```javascript
class StatsAPI {
  constructor(baseURL, token = null) {
    this.baseURL = baseURL;
    this.headers = token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  async getRepoStats(repoType, namespace, name) {
    const response = await fetch(
      `${this.baseURL}/${repoType}s/${namespace}/${name}/stats`,
      { headers: this.headers }
    );
    return await response.json();
  }

  async getRecentStats(repoType, namespace, name, days = 30) {
    const response = await fetch(
      `${this.baseURL}/${repoType}s/${namespace}/${name}/stats/recent?days=${days}`,
      { headers: this.headers }
    );
    return await response.json();
  }

  async getTrending(repoType = 'model', days = 7, limit = 20) {
    const response = await fetch(
      `${this.baseURL}/api/trending?repo_type=${repoType}&days=${days}&limit=${limit}`,
      { headers: this.headers }
    );
    return await response.json();
  }

  async analyzeGrowth(repoType, namespace, name, days = 30) {
    const data = await this.getRecentStats(repoType, namespace, name, days);
    const stats = data.stats;

    if (!stats.length) return null;

    const total = stats.reduce((sum, s) => sum + s.downloads, 0);
    const avgDaily = total / stats.length;

    const midPoint = Math.floor(stats.length / 2);
    const firstHalf = stats.slice(0, midPoint)
      .reduce((sum, s) => sum + s.downloads, 0);
    const secondHalf = stats.slice(midPoint)
      .reduce((sum, s) => sum + s.downloads, 0);

    const growthRate = firstHalf > 0
      ? ((secondHalf - firstHalf) / firstHalf * 100)
      : 0;

    return {
      totalDownloads: total,
      avgDailyDownloads: avgDaily,
      growthRatePercent: growthRate,
      trend: secondHalf > firstHalf ? 'up' : secondHalf < firstHalf ? 'down' : 'stable'
    };
  }
}

// Usage
const statsAPI = new StatsAPI('http://localhost:28080', 'YOUR_TOKEN');

// Get basic stats
const stats = await statsAPI.getRepoStats('model', 'myorg', 'mymodel');
console.log(`Downloads: ${stats.downloads.toLocaleString()}`);
console.log(`Likes: ${stats.likes}`);

// Get trending
const trending = await statsAPI.getTrending('model', 7, 10);
console.log('\nTop Trending Models:');
trending.trending.forEach((repo, i) => {
  console.log(`${i + 1}. ${repo.id}: ${repo.recent_downloads.toLocaleString()} downloads`);
});

// Analyze growth
const growth = await statsAPI.analyzeGrowth('model', 'myorg', 'mymodel', 30);
console.log(`\n30-day growth: ${growth.growthRatePercent.toFixed(1)}%`);
```

---

## CLI Usage

See [CLI Documentation](../CLI.md#statistics) for command-line interface:

```bash
# Get repository stats
kohub-cli stats get model myorg/mymodel

# Get recent statistics (last 30 days)
kohub-cli stats recent model myorg/mymodel --days 30

# Get trending models
kohub-cli trending --type model --days 7 --limit 10

# Export to CSV
kohub-cli stats export model myorg/mymodel --days 90 --output stats.csv
```

---

## Download Session Tracking

### How Sessions Work

- **Session window**: Downloads within a short time window (e.g., 30 minutes) count as one session
- **User-based**: Tracked by user ID (authenticated) or IP + User-Agent (anonymous)
- **Repository-level**: One session per repository, even if multiple files downloaded
- **Daily aggregation**: Sessions are aggregated daily for historical analysis

### What Counts as a Download?

- ✅ Successful file downloads (HTTP 200)
- ✅ Git clone operations
- ✅ LFS file downloads
- ❌ Failed downloads (HTTP 4xx/5xx)
- ❌ HEAD requests (metadata only)
- ❌ Tree browsing (no files downloaded)

---

## Next Steps

- [Quota Management API](./quota.md) - Monitor storage usage
- [Repository API](../API.md#repositories) - Repository management
- [Likes API](../API.md#likes) - Like/unlike repositories
- [File Tree API](./tree.md) - Browse repository contents
