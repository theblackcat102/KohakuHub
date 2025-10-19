---
title: Likes & Trending
description: Repository popularity and discovery system
icon: i-carbon-favorite
---

# Likes & Trending

Discover popular repositories and track favorites.

## Likes

**Like a repository:**
- Click ❤️ on repo page
- View liked repos: `/users/{username}/likes`
- See likers: Repo page shows count

**API:**
\`\`\`bash
POST /{type}s/{namespace}/{name}/like
DELETE /{type}s/{namespace}/{name}/like
GET /users/{username}/likes
\`\`\`

## Trending Algorithm

**Based on:**
- Download sessions (7-day window)
- Likes count
- Time decay

**Formula:**
- Recent activity weighted higher
- Combines downloads + likes
- Recalculated daily

**View trending:**
- Homepage shows top trending
- API: `GET /api/trending?limit=50`

## Download Tracking

**Automatic tracking:**
- Each download session counted
- Deduplicated by 15-min window
- Anonymous + authenticated tracked
- Privacy-preserving (no user tracking)

**Stats available:**
- Repository download count
- Daily stats (DailyRepoStats table)
- Download trends over time
