# TODO

*Last Updated: October 2025*

Kohaku-Hub is a pretty large project and really hard to say where to start is better, but I will try to list all the known TODOs here with brief priority note

## Infrastructure
- [x] Basic Infra Structure
    - [x] LakeFS + MinIO deployment
    - [x] MinIO presigned URL
    - [x] PostgreSQL database support
    - [x] SQLite database support
    - [x] Docker compose setup
    - [x] Environment configuration system

## API Layer
- [x] Core File Operations
    - [x] Upload small files (not LFS)
    - [x] Upload large files (LFS)
    - [x] Download with S3 presigned URLs
    - [x] File deletion
    - [x] File copy operations
    - [x] Content deduplication
- [x] Repository Management
    - [x] Create repository
    - [x] Delete repository
    - [x] List repositories
    - [x] Get repository info
    - [x] Tree list (recursive & non-recursive)
    - [x] Paths-info endpoint
    - [x] Move/Rename repository
    - [x] Update repository settings (private, gated)
    - [ ] Repository transfer between namespaces (different from move)
- [x] Authentication & Authorization
    - [x] User registration
    - [x] User login/logout
    - [x] Email verification (optional)
    - [x] Session management
    - [x] API token generation
    - [x] API token revocation
    - [x] Permission system (namespace-based)
    - [x] Repository access control (read/write/delete)
    - [ ] More granular permissions
    - [ ] Rate limiting
- [x] Organization Management
    - [x] Create organization
    - [x] Get organization details
    - [x] Add/remove members
    - [x] Update member roles
    - [x] List organization members
    - [x] List user organizations
    - [x] Organization settings/metadata (description, etc.)
    - [ ] Organization deletion
- [x] Version Control Features
    - [x] Repository branches (create/delete)
    - [x] Repository tags (create/delete)
    - [x] Commit history API
- [ ] Advanced Features
    - [ ] Pull requests / merge requests
    - [ ] Discussion/comments
    - [ ] Repository stars/likes
    - [ ] Download statistics
    - [ ] Search functionality
    - [ ] Repository metadata tags/categories

## Web UI (Vue 3 + Vite)
- [x] Core Pages
    - [x] Home/landing page
    - [x] User registration page
    - [x] User login page
    - [x] User settings page
    - [x] About/docs pages
- [x] Repository Features
    - [x] Repository list
    - [x] Repository creation
    - [x] Repository info page
    - [x] File browser/tree view
    - [x] File viewer with code highlighting
    - [x] File editor (Monaco Editor)
    - [x] File uploader
    - [x] Markdown renderer
    - [x] Commit history view
    - [x] Repository settings page
    - [ ] Branch management UI
    - [ ] Tag management UI
    - [ ] Diff viewer
    - [ ] Repository deletion UI confirmation
- [x] User/Organization UI
    - [x] User profile view
    - [x] Organization pages
    - [x] Organization settings page
    - [ ] Organization member management UI (add/remove members)
    - [ ] Organization creation UI
- [ ] Additional Features
    - [x] Theme support (dark/light)
    - [ ] Search interface
    - [ ] Notifications
    - [ ] Activity feed
    - [ ] File preview for images/media

## CLI Tool
- [x] User Management
    - [x] User registration
    - [x] User login/logout
    - [x] Token creation/listing/deletion
    - [x] Get current user info (whoami)
    - [x] Update user settings
- [x] Organization Management
    - [x] Create organization
    - [x] Get organization info
    - [x] List user organizations
    - [x] Add/remove members
    - [x] Update member roles
    - [x] List organization members
    - [x] Update organization settings
- [x] Repository Management
    - [x] Create/delete repositories via CLI
    - [x] List repositories
    - [x] Get repository info
    - [x] List repository files
    - [x] Update repository settings
    - [x] Move/rename repositories
    - [x] Create/delete branches
    - [x] Create/delete tags
    - [ ] Upload/download files (use hfutils for now)
- [x] Configuration Management
    - [x] Set/get configuration
    - [x] List all configuration
    - [x] Clear configuration
- [x] Interactive TUI Mode
    - [x] Menu-based interface
- [ ] Administrative Features
    - [ ] User administration (create/delete users)
    - [ ] System statistics
    - [ ] Backup/restore utilities
    - [ ] LFS garbage collection

## Documentation
- [x] API.md (comprehensive API documentation)
- [x] CLI.md (CLI design and usage documentation)
- [x] README.md (getting started guide)
- [x] TODO.md (this file)
- [x] CONTRIBUTING.md (contributing guidelines)
- [x] config-example.toml
- [x] Documentation pages in Web UI
    - [x] API documentation viewer
    - [x] CLI documentation viewer
    - [x] Roadmap viewer
    - [x] Contributing guide viewer
- [ ] Deployment guides
    - [ ] Production deployment best practices
    - [ ] Scaling guide
    - [ ] Migration guide from other hubs
    - [ ] Backup/restore procedures
- [ ] Developer documentation
    - [ ] Architecture overview document
    - [ ] Database schema documentation
    - [ ] API client development guide

## Testing & Quality
- [ ] Unit tests
    - [ ] API endpoint tests
    - [ ] Database model tests
    - [ ] Authentication/authorization tests
- [ ] Integration tests
    - [ ] E2E workflow tests
    - [ ] HuggingFace client compatibility tests
- [ ] Performance testing
    - [ ] Load testing
    - [ ] Large file handling
- [ ] Security auditing
    - [ ] Authentication security review
    - [ ] SQL injection prevention
    - [ ] XSS prevention in UI

## Future Enhancements
- [ ] Multi-region/CDN support
- [ ] Webhook system
- [ ] Model card/dataset card templates
- [ ] Integration with CI/CD pipelines
- [ ] Automated model evaluation
- [ ] Dataset versioning with lineage tracking
- [ ] Model registry with deployment tracking