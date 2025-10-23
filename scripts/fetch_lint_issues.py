#!/usr/bin/env python3
"""
Fetch and categorize lint issues from Gitroll API.

Usage:
    python scripts/fetch_lint_issues.py
"""

import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path


API_BASE = "https://gitroll.io/api/repo-scan/BxVarI2zcjxJEzV2elTu/issues"
PAGE_SIZE = 25


def fetch_all_issues():
    """Fetch all issues from Gitroll API with pagination."""
    all_issues = []
    page = 1

    print(f"Fetching lint issues from Gitroll API...")

    while True:
        url = f"{API_BASE}?p={page}&ps={PAGE_SIZE}"
        print(f"  Fetching page {page}...")

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

        issues = data.get("issues", [])

        # Debug: print first issue to see structure
        if page == 1 and issues:
            print(f"  DEBUG: First issue keys: {list(issues[0].keys())}")

        if not issues:
            print(f"  No more issues on page {page}")
            break

        all_issues.extend(issues)
        print(f"  Found {len(issues)} issues on page {page}")

        # Check if there are more pages
        total = data.get("total", 0)
        if len(all_issues) >= total:
            break

        page += 1

    print(f"\nTotal issues fetched: {len(all_issues)}")
    return all_issues


def categorize_by_severity(issues):
    """Categorize issues by severity."""
    by_severity = defaultdict(list)

    for issue in issues:
        severity = issue.get("severity", "unknown").lower()
        by_severity[severity].append(issue)

    return dict(by_severity)


def categorize_by_type(issues):
    """Categorize issues by type/rule."""
    by_type = defaultdict(list)

    for issue in issues:
        rule = issue.get("type", "unknown")
        by_type[rule].append(issue)

    return dict(by_type)


def categorize_by_file(issues):
    """Categorize issues by file path."""
    by_file = defaultdict(list)

    for issue in issues:
        file_path = issue.get("component", "unknown")
        by_file[file_path].append(issue)

    return dict(by_file)


def print_summary(issues, by_severity, by_type, by_file):
    """Print summary of issues."""
    print("\n" + "=" * 80)
    print("LINT ISSUES SUMMARY")
    print("=" * 80)

    print(f"\nTotal Issues: {len(issues)}")

    # Severity breakdown
    print("\n--- By Severity ---")
    severity_order = ["critical", "error", "warning", "info", "hint"]
    for severity in severity_order:
        count = len(by_severity.get(severity, []))
        if count > 0:
            print(f"  {severity.upper()}: {count}")

    # Top 10 issue types
    print("\n--- Top 10 Issue Types ---")
    sorted_types = sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True)
    for i, (rule, rule_issues) in enumerate(sorted_types[:10], 1):
        print(f"  {i}. {rule}: {len(rule_issues)}")

    # Top 10 files with most issues
    print("\n--- Top 10 Files with Most Issues ---")
    sorted_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)
    for i, (file_path, file_issues) in enumerate(sorted_files[:10], 1):
        print(f"  {i}. {file_path}: {len(file_issues)} issues")


def get_code_context(file_path, start_line, end_line, context_lines=3):
    """Get code context from source file.

    Args:
        file_path: Path to file (with project prefix like "BxVarI2zcjxJEzV2elTu:src/...")
        start_line: Start line number
        end_line: End line number
        context_lines: Number of lines before/after to include

    Returns:
        Code snippet with line numbers, or None if file not found
    """
    # Remove project prefix
    if ":" in file_path:
        file_path = file_path.split(":", 1)[1]

    repo_root = Path(__file__).parent.parent
    full_path = repo_root / file_path

    if not full_path.exists():
        return None

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Get line range with context
        start_idx = max(0, start_line - context_lines - 1)
        end_idx = min(len(lines), end_line + context_lines)

        snippet_lines = []
        for i in range(start_idx, end_idx):
            line_num = i + 1
            line_content = lines[i].rstrip()

            # Mark the actual issue lines
            if start_line <= line_num <= end_line:
                snippet_lines.append(f"{line_num:4d} →│ {line_content}")
            else:
                snippet_lines.append(f"{line_num:4d}  │ {line_content}")

        return "\n".join(snippet_lines)
    except Exception as e:
        return f"Error reading file: {e}"


def save_detailed_report(issues, by_severity, by_type, by_file):
    """Save detailed report to JSON files and enhanced markdown."""
    output_dir = Path(__file__).parent.parent / "lint-reports"
    output_dir.mkdir(exist_ok=True)

    # Save overall summary JSON
    summary = {
        "total_issues": len(issues),
        "by_severity": {k: len(v) for k, v in by_severity.items()},
        "by_type": {k: len(v) for k, v in by_type.items()},
        "by_file": {k: len(v) for k, v in by_file.items()},
    }

    summary_file = output_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nSummary saved to: {summary_file}")

    # Save separate JSON files by severity
    for severity, severity_issues in by_severity.items():
        severity_file = output_dir / f"{severity}.json"
        with open(severity_file, "w", encoding="utf-8") as f:
            json.dump(severity_issues, f, indent=2, ensure_ascii=False)
        print(
            f"  {severity.upper()}: {len(severity_issues)} issues -> {severity_file.name}"
        )

    # Save all issues
    all_file = output_dir / "all-issues.json"
    with open(all_file, "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)

    print(f"  All issues -> {all_file.name}")

    # Save enhanced markdown reports by severity
    print("\nGenerating enhanced markdown reports with code context...")

    for severity in ["critical", "error", "warning", "info", "hint"]:
        severity_issues = by_severity.get(severity, [])
        if not severity_issues:
            continue

        md_file = output_dir / f"{severity}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# {severity.upper()} Issues ({len(severity_issues)} total)\n\n")
            f.write(f"Generated from Gitroll API scan\n\n")
            f.write("---\n\n")

            # Group by file
            issues_by_file = defaultdict(list)
            for issue in severity_issues:
                file_path = issue.get("component", "unknown")
                issues_by_file[file_path].append(issue)

            # Sort files by number of issues
            sorted_files = sorted(
                issues_by_file.items(), key=lambda x: len(x[1]), reverse=True
            )

            for file_path, file_issues in sorted_files:
                # Clean file path
                clean_path = (
                    file_path.split(":", 1)[1] if ":" in file_path else file_path
                )

                f.write(f"## {clean_path} ({len(file_issues)} issues)\n\n")

                for issue in file_issues:
                    text_range = issue.get("textRange", {})
                    start_line = text_range.get("startLine", 0)
                    end_line = text_range.get("endLine", start_line)

                    f.write(f"### Line {start_line}")
                    if end_line != start_line:
                        f.write(f"-{end_line}")
                    f.write(f": {issue.get('type', 'UNKNOWN')}\n\n")

                    f.write(f"**Message**: {issue.get('message', 'No message')}\n\n")

                    # Add code context
                    if start_line > 0:
                        code_context = get_code_context(
                            file_path, start_line, end_line, context_lines=2
                        )
                        if code_context:
                            f.write("**Code Context**:\n```python\n")
                            f.write(code_context)
                            f.write("\n```\n\n")

                    f.write("---\n\n")

        print(f"  {severity.upper()}: {md_file.name}")

    # Save overall summary markdown
    summary_md = output_dir / "README.md"
    with open(summary_md, "w", encoding="utf-8") as f:
        f.write("# Lint Issues Report\n\n")
        f.write(f"**Total Issues**: {len(issues)}\n\n")

        f.write("## By Severity\n\n")
        f.write("| Severity | Count | Report |\n")
        f.write("|----------|-------|--------|\n")
        for severity in ["critical", "error", "warning", "info", "hint"]:
            count = len(by_severity.get(severity, []))
            if count > 0:
                f.write(
                    f"| {severity.upper()} | {count} | [{severity}.md](./{severity}.md) |\n"
                )

        f.write("\n## By Type\n\n")
        sorted_types = sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True)
        for rule, rule_issues in sorted_types[:20]:
            f.write(f"- `{rule}`: {len(rule_issues)}\n")

        f.write("\n## By File (Top 20)\n\n")
        sorted_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)
        for file_path, file_issues in sorted_files[:20]:
            clean_path = file_path.split(":", 1)[1] if ":" in file_path else file_path
            f.write(f"- `{clean_path}`: {len(file_issues)}\n")

    print(f"  Summary: {summary_md.name}")


def main():
    """Main function."""
    # Fetch all issues
    issues = fetch_all_issues()

    if not issues:
        print("\nNo issues found or API request failed.")
        return

    # Categorize
    by_severity = categorize_by_severity(issues)
    by_type = categorize_by_type(issues)
    by_file = categorize_by_file(issues)

    # Print summary
    print_summary(issues, by_severity, by_type, by_file)

    # Save detailed reports
    save_detailed_report(issues, by_severity, by_type, by_file)

    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
