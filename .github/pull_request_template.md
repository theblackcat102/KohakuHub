# Pull Request

## Description

<!-- Provide a clear and concise description of your changes -->

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement
- [ ] Test coverage improvement
- [ ] Build/CI improvement

## Component

<!-- Mark all that apply -->

- [ ] Backend API
- [ ] Frontend UI
- [ ] CLI Tool
- [ ] Documentation
- [ ] Docker/Deployment
- [ ] Database
- [ ] Authentication
- [ ] LakeFS Integration
- [ ] S3/Storage

## Related Issues

<!-- Link any related issues. Use "Fixes #issue_number" or "Closes #issue_number" for automatic closing -->

- Fixes #
- Related to #

## Changes Made

<!-- List the main changes made in this PR -->

-
-
-

## Testing

<!-- Describe the tests you ran and how to reproduce them -->

### Test Environment
- [ ] Local development setup
- [ ] Docker deployment
- [ ] Both

### Test Scenarios
<!-- Describe what you tested -->

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] Tested in both light and dark mode (for UI changes)
- [ ] Tested on mobile viewport (for UI changes)

### Test Results
<!-- Paste test output or describe test results -->

```
# Paste relevant test output here
```

## Screenshots / Videos

<!-- If applicable, add screenshots or videos to demonstrate changes -->

### Before
<!-- Screenshots of the old behavior -->

### After
<!-- Screenshots of the new behavior -->

## Documentation

- [ ] Code is self-documenting and follows project conventions
- [ ] Docstrings/comments added for complex logic
- [ ] README.md updated (if needed)
- [ ] CLAUDE.md updated (if needed)
- [ ] API.md updated (if API changes)
- [ ] CLI.md updated (if CLI changes)
- [ ] CONTRIBUTING.md updated (if workflow changes)

## Code Quality

- [ ] Code follows the style guidelines (see [CLAUDE.md](../CLAUDE.md))
- [ ] Python code formatted with `black`
- [ ] Frontend code formatted with `prettier`
- [ ] Used `db_async` wrappers for all database operations
- [ ] Permission checks added for write operations
- [ ] Error handling follows HuggingFace-compatible format
- [ ] Import order follows convention (builtin → 3rd party → ours)
- [ ] No debug code or commented-out code left in
- [ ] Type hints added (Python) or JSDoc comments (JavaScript)

## Breaking Changes

<!-- If this PR introduces breaking changes, describe them and the migration path -->

- [ ] This PR includes breaking changes

### Migration Guide
<!-- Provide instructions for users to migrate from the old behavior to the new -->

## Security Considerations

<!-- Mark if applicable -->

- [ ] This PR introduces security-sensitive changes
- [ ] Authentication/authorization logic changed
- [ ] Input validation added/updated
- [ ] SQL injection prevention verified
- [ ] XSS prevention verified

## Performance Impact

<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Performance improved
- [ ] Performance may be impacted (explain below)

### Performance Details
<!-- Describe performance testing or considerations -->

## Deployment Notes

<!-- Any special deployment steps or configuration changes needed? -->

- [ ] No special deployment steps required
- [ ] Database migration required
- [ ] Environment variables changed
- [ ] Docker image rebuild required
- [ ] Configuration file updates needed

### Deployment Steps
<!-- If special steps are required, list them here -->

1.
2.

## Checklist

<!-- Final checks before submission -->

- [ ] I have read the [CONTRIBUTING.md](../CONTRIBUTING.md) guidelines
- [ ] I have read the [CLAUDE.md](../CLAUDE.md) developer guide
- [ ] My code follows the project's coding standards
- [ ] I have tested my changes thoroughly
- [ ] I have added/updated tests as necessary
- [ ] I have updated documentation as necessary
- [ ] My changes generate no new warnings or errors
- [ ] All existing tests pass
- [ ] I have checked my code for security issues
- [ ] I have added myself to CONTRIBUTORS.md (if applicable)

## Additional Notes

<!-- Any additional information reviewers should know -->

## Reviewer Notes

<!-- Optional: Specific areas you'd like reviewers to focus on -->

---

**For Maintainers:**

- [ ] Code review completed
- [ ] Tests pass
- [ ] Documentation is adequate
- [ ] Ready to merge
