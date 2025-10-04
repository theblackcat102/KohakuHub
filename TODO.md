# TODO

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
    - [ ] Move/Rename repository
    - [ ] Repository transfer between namespaces
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
    - [x] List user organizations
    - [ ] Organization deletion
    - [ ] Organization settings/metadata
- [ ] Advanced Features
    - [ ] Repository branches (beyond main)
    - [ ] Pull requests / merge requests
    - [ ] Discussion/comments
    - [ ] Repository stars/likes
    - [ ] Download statistics
    - [ ] Search functionality
    - [ ] Tags/categories

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
    - [ ] Commit history view
    - [ ] Branch management UI
    - [ ] Diff viewer
    - [ ] Repository settings
    - [ ] Repository deletion UI
- [x] User/Organization UI
    - [x] User profile view
    - [x] Organization pages
    - [ ] Organization member management UI
    - [ ] Organization settings UI
- [ ] Additional Features
    - [x] Theme support (dark/light)
    - [ ] Search interface
    - [ ] Notifications
    - [ ] Activity feed
    - [ ] File preview for images/media

## CLI Tool
- [x] Basic User Management
    - [x] User registration
    - [x] User login
    - [x] Token creation
- [x] Basic Organization Management
    - [x] Create organization
    - [x] Add/remove members
    - [x] Update member roles
- [ ] Repository Management
    - [ ] Create/delete repositories via CLI
    - [ ] Upload/download files
    - [ ] Manage branches
- [ ] Administrative Features
    - [ ] User administration
    - [ ] System statistics
    - [ ] Backup/restore utilities

## Documentation
- [x] API.md (comprehensive API documentation)
- [x] README.md (getting started guide)
- [x] TODO.md (this file)
- [x] config-example.toml
- [ ] Deployment guides
    - [ ] Production deployment best practices
    - [ ] Scaling guide
    - [ ] Migration guide
- [ ] Developer documentation
    - [ ] Architecture overview
    - [ ] Contributing guidelines
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