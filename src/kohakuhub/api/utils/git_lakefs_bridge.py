"""Git-LakeFS bridge for translating Git operations to LakeFS REST API.

This module provides a bridge between Git protocol operations and LakeFS REST API,
allowing Git clients to interact with repositories stored in LakeFS.
"""

import asyncio
import fnmatch
import hashlib
import os
import struct
import tempfile
from datetime import datetime
from pathlib import Path

import pygit2

from kohakuhub.config import cfg
from kohakuhub.logger import get_logger
from kohakuhub.api.utils.git_server import create_empty_pack
from kohakuhub.api.utils.lakefs import get_lakefs_client, lakefs_repo_name

logger = get_logger("GIT_LAKEFS")


def create_lfs_pointer(sha256: str, size: int) -> bytes:
    """Create Git LFS pointer file content.

    Args:
        sha256: File SHA256 hash
        size: File size in bytes

    Returns:
        LFS pointer file content (text)
    """
    pointer = f"""version https://git-lfs.github.com/spec/v1
oid sha256:{sha256}
size {size}
"""
    return pointer.encode("utf-8")


def generate_gitattributes(lfs_paths: list[str]) -> bytes:
    """Generate .gitattributes file for Git LFS.

    Uses ONLY specific file paths (no wildcards) to avoid false positives.

    Args:
        lfs_paths: List of specific file paths that are LFS pointers

    Returns:
        .gitattributes content
    """
    lines = ["# Git LFS tracking (auto-generated)\n"]
    lines.append("# Only files above threshold are tracked\n\n")

    # Add each file individually (NO wildcards!)
    for file_path in sorted(lfs_paths):
        lines.append(f"{file_path} filter=lfs diff=lfs merge=lfs -text\n")

    return "".join(lines).encode("utf-8")


def compute_git_blob_sha(content: bytes) -> str:
    """Compute Git blob SHA-1.

    Args:
        content: File content

    Returns:
        SHA-1 hash in hex format
    """
    size = len(content)
    header = f"blob {size}\x00".encode()
    sha = hashlib.sha1()
    sha.update(header + content)
    return sha.hexdigest()


def compute_git_tree_sha(entries: list[tuple[str, str, str]]) -> str:
    """Compute Git tree SHA-1.

    Args:
        entries: List of (mode, name, sha) tuples

    Returns:
        SHA-1 hash in hex format
    """
    # Sort entries
    sorted_entries = sorted(entries, key=lambda x: x[1])

    # Build tree content
    tree_content = b""
    for mode, name, sha_hex in sorted_entries:
        sha_bytes = bytes.fromhex(sha_hex)
        tree_content += f"{mode} {name}\x00".encode() + sha_bytes

    # Compute hash
    size = len(tree_content)
    header = f"tree {size}\x00".encode()
    sha = hashlib.sha1()
    sha.update(header + tree_content)
    return sha.hexdigest()


class GitLakeFSBridge:
    """Bridge between Git operations and LakeFS REST API."""

    def __init__(self, repo_type: str, namespace: str, name: str):
        """Initialize Git-LakeFS bridge.

        Args:
            repo_type: Repository type (model/dataset/space)
            namespace: Repository namespace
            name: Repository name
        """
        self.repo_type = repo_type
        self.namespace = namespace
        self.name = name
        self.repo_id = f"{namespace}/{name}"
        self.lakefs_repo = lakefs_repo_name(repo_type, self.repo_id)
        self.lakefs_client = get_lakefs_client()

    def _parse_gitattributes_lfs_patterns(self, content: str) -> set[str]:
        """Parse LFS patterns from .gitattributes content.

        Args:
            content: .gitattributes file content

        Returns:
            Set of file patterns that use LFS (e.g., "*.bin", "model.safetensors")
        """
        patterns = set()

        for line in content.splitlines():
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Look for "filter=lfs" attribute
            if "filter=lfs" in line:
                # Extract pattern (first token before attributes)
                parts = line.split()
                if parts:
                    pattern = parts[0]
                    patterns.add(pattern)

        return patterns

    def _matches_lfs_pattern(self, path: str, patterns: set[str]) -> bool:
        """Check if file path matches any LFS pattern.

        Args:
            path: File path (e.g., "models/config.json")
            patterns: Set of patterns (e.g., {"*.json", "models/*.bin"})

        Returns:
            True if path matches any pattern
        """
        for pattern in patterns:
            # Handle wildcards with fnmatch
            if fnmatch.fnmatch(path, pattern):
                return True

            # Also check basename for simple patterns like "*.ext"
            if pattern.startswith("*."):
                basename = path.split("/")[-1]
                if fnmatch.fnmatch(basename, pattern):
                    return True

        return False

    async def get_refs(self, branch: str = "main") -> dict[str, str]:
        """Get Git refs from LakeFS branch.

        Args:
            branch: Branch name to get refs from

        Returns:
            Dictionary mapping ref names to commit SHAs (Git SHA-1 format)
        """
        refs = {}

        try:
            # Create temporary git repository to build commit
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo_path = Path(temp_dir) / "repo"
                temp_repo_path.mkdir()

                # Initialize bare repository (run in thread pool)
                repo = await asyncio.to_thread(
                    pygit2.init_repository, str(temp_repo_path), bare=True
                )

                # Fetch all objects from LakeFS and build Git tree
                commit_oid = await self._populate_git_repo(repo, branch)

                if commit_oid:
                    # Use the Git commit SHA we created
                    git_commit_sha = str(commit_oid)

                    # Map Git commit to refs
                    refs[f"refs/heads/{branch}"] = git_commit_sha
                    refs["HEAD"] = git_commit_sha

        except Exception as e:
            logger.exception(
                "Failed to get refs for {}/{}/{}".format(
                    self.repo_type, self.namespace, self.name
                ),
                e,
            )

        return refs

    async def build_pack_file(
        self, wants: list[str], haves: list[str], branch: str = "main"
    ) -> bytes:
        """Build Git pack file with requested objects.

        Args:
            wants: List of commit SHAs client wants
            haves: List of commit SHAs client already has
            branch: Branch name

        Returns:
            Pack file bytes
        """
        try:
            # Create temporary git repository
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo_path = Path(temp_dir) / "repo"
                temp_repo_path.mkdir()

                # Initialize bare repository (run in thread pool)
                repo = await asyncio.to_thread(
                    pygit2.init_repository, str(temp_repo_path), bare=True
                )

                # Fetch all objects from LakeFS and build Git tree
                commit_oid = await self._populate_git_repo(repo, branch)

                if not commit_oid:
                    logger.warning("No commit created, returning empty pack")
                    return create_empty_pack()

                # Create pack file (CPU-intensive, run in thread pool)
                pack_data = await asyncio.to_thread(
                    self._create_pack_file, repo, wants, haves
                )

                return pack_data

        except Exception as e:
            logger.exception("Failed to build pack file", e)
            return create_empty_pack()

    async def _populate_git_repo(
        self, repo: pygit2.Repository, branch: str
    ) -> pygit2.Oid | None:
        """Populate Git repository with objects from LakeFS.

        Args:
            repo: pygit2 Repository object
            branch: Branch name to fetch from

        Returns:
            Commit OID if successful, None otherwise
        """
        # List all objects in LakeFS branch
        try:
            all_objects = []
            after = ""
            has_more = True

            while has_more:
                result = await self.lakefs_client.list_objects(
                    repository=self.lakefs_repo,
                    ref=branch,
                    prefix="",
                    after=after,
                    amount=1000,
                )

                all_objects.extend(result.get("results", []))

                pagination = result.get("pagination", {})
                has_more = pagination.get("has_more", False)
                if has_more:
                    after = pagination.get("next_offset", "")

            logger.info(f"Found {len(all_objects)} objects in LakeFS")

            if not all_objects:
                logger.warning("No objects found in LakeFS repository")
                return None

            # Build nested tree structure
            tree_oid = await self._build_tree_from_objects(repo, all_objects, branch)

            if not tree_oid:
                return None

            # Get branch commit info
            branch_info = await self.lakefs_client.get_branch(
                repository=self.lakefs_repo, branch=branch
            )

            commit_id = branch_info.get("commit_id")

            # Get commit details
            try:
                if not commit_id:
                    logger.warning("No commit_id found, using default commit info")
                    author_name = "KohakuHub"
                    message = "Initial commit"
                    timestamp = 0
                else:
                    commit_info = await self.lakefs_client.get_commit(
                        repository=self.lakefs_repo, commit_id=commit_id
                    )

                    # Create commit
                    author_name = commit_info.get("committer", "KohakuHub")
                    message = commit_info.get("message", "Initial commit")
                    timestamp = commit_info.get("creation_date", 0)

                # Handle both integer timestamps and ISO date strings
                if isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        timestamp = int(dt.timestamp())
                    except:
                        timestamp = 0

                author = pygit2.Signature(
                    author_name, "noreply@kohakuhub.local", int(timestamp)
                )
                committer = author

                # Create commit (run in thread pool)
                commit_oid = await asyncio.to_thread(
                    repo.create_commit,
                    f"refs/heads/{branch}",
                    author,
                    committer,
                    message,
                    tree_oid,
                    [],  # No parents for now
                )

                logger.success(f"Created commit: {commit_oid}")
                return commit_oid

            except Exception as e:
                logger.exception("Failed to create commit", e)
                return None

        except Exception as e:
            logger.exception("Failed to populate git repo", e)
            return None

    async def _build_tree_from_objects(
        self, repo: pygit2.Repository, objects: list[dict], branch: str
    ) -> pygit2.Oid | None:
        """Build nested Git tree from flat list of LakeFS objects.

        Uses LFS pointers for large files to avoid downloading/storing massive files.

        Args:
            repo: pygit2 Repository
            objects: List of LakeFS object metadata
            branch: Branch name

        Returns:
            Tree OID if successful, None otherwise
        """
        # Build directory tree structure
        tree_entries = {}  # path -> (oid, mode)
        lfs_paths = []  # Track LFS files for .gitattributes

        # Filter to only file objects
        file_objects = [obj for obj in objects if obj.get("path_type") == "object"]

        # Check if repo has existing .gitattributes and parse LFS patterns
        existing_lfs_patterns = set()
        gitattributes_obj = None
        gitattributes_content = None

        for obj in file_objects:
            if obj["path"] == ".gitattributes":
                gitattributes_obj = obj
                # Download and parse it
                try:
                    gitattributes_content = await self.lakefs_client.get_object(
                        repository=self.lakefs_repo, ref=branch, path=".gitattributes"
                    )
                    # Parse LFS patterns
                    existing_lfs_patterns = self._parse_gitattributes_lfs_patterns(
                        gitattributes_content.decode("utf-8")
                    )
                    logger.info(
                        f"Found existing .gitattributes with {len(existing_lfs_patterns)} LFS patterns: {existing_lfs_patterns}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse .gitattributes: {e}")
                break

        # Separate files based on: size threshold OR existing LFS patterns
        small_files = []
        large_files = []

        for obj in file_objects:
            if obj["path"] == ".gitattributes":
                continue  # Handle separately

            path = obj["path"]
            size = obj.get("size_bytes", 0)

            # Check if file should be LFS based on:
            # 1. Size threshold, OR
            # 2. Existing .gitattributes patterns
            should_be_lfs = (
                size >= cfg.app.lfs_threshold_bytes
                or self._matches_lfs_pattern(path, existing_lfs_patterns)
            )

            if should_be_lfs:
                large_files.append(obj)
            else:
                small_files.append(obj)

        logger.info(
            f"Processing {len(small_files)} small files, "
            f"{len(large_files)} large files (LFS pointers)"
        )

        # Process small files normally (download content)
        async def process_small_file(obj):
            path = obj["path"]
            try:
                # Reuse .gitattributes content if already downloaded
                if path == ".gitattributes" and gitattributes_content is not None:
                    content = gitattributes_content
                else:
                    content = await self.lakefs_client.get_object(
                        repository=self.lakefs_repo, ref=branch, path=path
                    )

                blob_oid = await asyncio.to_thread(repo.create_blob, content)
                logger.debug(f"Created blob for {path}: {len(content)} bytes")
                return path, blob_oid, pygit2.GIT_FILEMODE_BLOB

            except Exception as e:
                logger.warning(f"Failed to download {path}: {e}")
                return None

        # Process large files as LFS pointers (NO full content download!)
        async def process_large_file(obj):
            path = obj["path"]
            try:
                # Get metadata only (stat instead of get_object)
                stat = await self.lakefs_client.stat_object(
                    repository=self.lakefs_repo, ref=branch, path=path
                )

                size = stat.get("size_bytes", 0)
                checksum = stat.get("checksum", "")

                # Extract SHA256 from checksum
                if checksum.startswith("sha256:"):
                    sha256 = checksum.replace("sha256:", "")
                else:
                    # Fallback: download to compute hash (should rarely happen)
                    logger.warning(
                        f"No checksum for {path}, downloading to compute hash"
                    )
                    content = await self.lakefs_client.get_object(
                        repository=self.lakefs_repo, ref=branch, path=path
                    )
                    sha256 = hashlib.sha256(content).hexdigest()

                # Create LFS pointer file
                pointer_content = create_lfs_pointer(sha256, size)
                blob_oid = await asyncio.to_thread(repo.create_blob, pointer_content)

                logger.debug(
                    f"Created LFS pointer for {path}: {size} bytes → "
                    f"{len(pointer_content)} bytes pointer"
                )

                return path, blob_oid, pygit2.GIT_FILEMODE_BLOB, True  # True = is_lfs

            except Exception as e:
                logger.warning(f"Failed to create LFS pointer for {path}: {e}")
                return None

        # Process files concurrently
        small_results = await asyncio.gather(
            *[process_small_file(obj) for obj in small_files]
        )
        large_results = await asyncio.gather(
            *[process_large_file(obj) for obj in large_files]
        )

        # Build tree_entries from results
        for result in small_results:
            if result is not None:
                path, blob_oid, mode = result
                tree_entries[path] = (blob_oid, mode)

        for result in large_results:
            if result is not None:
                path, blob_oid, mode, is_lfs = result
                tree_entries[path] = (blob_oid, mode)
                lfs_paths.append(path)

        # Handle .gitattributes
        # If repo doesn't have .gitattributes but we created LFS pointers, add one
        gitattributes_in_tree = ".gitattributes" in tree_entries

        if not gitattributes_in_tree and lfs_paths:
            # No existing .gitattributes, generate one for our LFS files
            logger.info(f"Generating .gitattributes for {len(lfs_paths)} LFS files")
            new_gitattributes = generate_gitattributes(lfs_paths)
            blob_oid = await asyncio.to_thread(repo.create_blob, new_gitattributes)
            tree_entries[".gitattributes"] = (blob_oid, pygit2.GIT_FILEMODE_BLOB)

        if not tree_entries:
            return None

        # Build nested tree structure from flat paths (run in thread pool)
        return await asyncio.to_thread(self._create_nested_tree, repo, tree_entries)

    def _create_nested_tree(
        self, repo: pygit2.Repository, entries: dict[str, tuple[pygit2.Oid, int]]
    ) -> pygit2.Oid:
        """Create nested Git tree from flat path entries.

        Args:
            repo: pygit2 Repository
            entries: Dict mapping paths to (oid, mode) tuples

        Returns:
            Root tree OID
        """
        # Organize entries by directory
        dir_contents = {}  # dir_path -> {name: (oid, mode)}

        for path, (oid, mode) in entries.items():
            parts = path.split("/")

            # Add entry to each parent directory
            for i in range(len(parts)):
                if i == len(parts) - 1:
                    # This is the file itself
                    dir_path = "/".join(parts[:i]) if i > 0 else ""
                    name = parts[i]
                    if dir_path not in dir_contents:
                        dir_contents[dir_path] = {}
                    dir_contents[dir_path][name] = (oid, mode)

        # Build trees bottom-up (deepest first)
        sorted_dirs = sorted(
            dir_contents.keys(), key=lambda x: x.count("/"), reverse=True
        )

        dir_oids = {}  # dir_path -> tree_oid

        for dir_path in sorted_dirs:
            tree_builder = repo.TreeBuilder()

            for name, (entry_oid, entry_mode) in dir_contents[dir_path].items():
                # Check if this is a subdirectory
                subdir_path = f"{dir_path}/{name}" if dir_path else name
                if subdir_path in dir_oids:
                    # This is a directory - use its tree OID
                    tree_builder.insert(
                        name, dir_oids[subdir_path], pygit2.GIT_FILEMODE_TREE
                    )
                else:
                    # This is a file - use the blob OID
                    tree_builder.insert(name, entry_oid, entry_mode)

            tree_oid = tree_builder.write()
            dir_oids[dir_path] = tree_oid

        # Return root tree - fallback to last directory if root is empty
        if "" in dir_oids:
            return dir_oids[""]
        elif sorted_dirs:
            return dir_oids[sorted_dirs[-1]]
        else:
            # Create an empty tree if no directories
            tree_builder = repo.TreeBuilder()
            return tree_builder.write()

    def _create_pack_file(
        self, repo: pygit2.Repository, wants: list[str], haves: list[str]
    ) -> bytes:
        """Create Git pack file.

        Args:
            repo: pygit2 Repository
            wants: List of wanted commit SHAs
            haves: List of existing commit SHAs

        Returns:
            Pack file bytes
        """
        try:
            # Get the branch ref (we use main)
            try:
                ref = repo.references["refs/heads/main"]
                head_commit_oid = ref.target
            except KeyError:
                # Fallback to first want if branch not found
                if wants:
                    head_commit_oid = pygit2.Oid(hex=wants[0])
                else:
                    logger.warning("No ref or wants found, returning empty pack")
                    return create_empty_pack()

            # Walk through all objects reachable from wanted commits
            # Use pygit2.SortMode.TOPOLOGICAL instead of the integer constant
            walker = repo.walk(head_commit_oid, pygit2.enums.SortMode.TOPOLOGICAL)

            # Collect all objects to pack
            oids_to_pack = set()

            for commit in walker:
                # Stop if we've reached a commit the client already has
                if str(commit.id) in haves:
                    break

                # Add commit
                oids_to_pack.add(commit.id)

                # Add tree and all blobs
                self._collect_tree_objects(repo, commit.tree_id, oids_to_pack)

            logger.info(f"Packing {len(oids_to_pack)} objects")

            # Use pygit2 PackBuilder to create pack
            # Write pack to a temporary directory, then read it back
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create pack builder and add all objects
                pack_builder = pygit2.PackBuilder(repo)

                for oid in oids_to_pack:
                    pack_builder.add(oid)

                # Write pack to directory (pygit2 will create pack file inside)
                pack_builder.write(temp_dir)

                # Find the generated pack file
                pack_files = [f for f in os.listdir(temp_dir) if f.endswith(".pack")]
                if not pack_files:
                    logger.error("No pack file generated")
                    return create_empty_pack()

                pack_path = os.path.join(temp_dir, pack_files[0])

                # Read pack file
                with open(pack_path, "rb") as f:
                    pack_bytes = f.read()

                logger.success(f"Created pack file: {len(pack_bytes)} bytes")
                return pack_bytes

        except Exception as e:
            logger.exception("Failed to create pack file", e)
            return create_empty_pack()

    def _collect_tree_objects(
        self, repo: pygit2.Repository, tree_oid: pygit2.Oid, oids: set
    ):
        """Recursively collect all objects in a tree.

        Args:
            repo: pygit2 Repository
            tree_oid: Tree OID to collect from
            oids: Set to add collected OIDs to
        """
        if tree_oid in oids:
            return

        oids.add(tree_oid)
        tree = repo[tree_oid]

        # Type assertion to help type checker - tree should be a Tree object
        if not isinstance(tree, pygit2.Tree):
            return

        for entry in tree:
            oids.add(entry.id)

            # Recursively collect subtrees
            if entry.filemode == pygit2.GIT_FILEMODE_TREE:
                self._collect_tree_objects(repo, entry.id, oids)

    async def unpack_and_push(
        self, pack_data: bytes, ref_updates: list[tuple[str, str, str]], branch: str
    ) -> bool:
        """Unpack Git pack file and push to LakeFS.

        Args:
            pack_data: Pack file bytes
            ref_updates: List of (old_sha, new_sha, ref_name) tuples
            branch: Target branch name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create temporary repository to unpack
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo_path = Path(temp_dir) / "repo"
                temp_repo_path.mkdir()

                repo = pygit2.init_repository(str(temp_repo_path), bare=True)

                # Write pack file
                pack_path = Path(temp_dir) / "incoming.pack"
                pack_path.write_bytes(pack_data)

                # Index pack (this extracts objects)
                # Note: pygit2 doesn't have direct pack indexing API
                # In production, we'd use git index-pack via subprocess
                logger.warning("Pack unpacking not fully implemented yet")

                # For each ref update, push objects to LakeFS
                for old_sha, new_sha, ref_name in ref_updates:
                    logger.info(
                        f"Processing ref update: {ref_name} {old_sha} -> {new_sha}"
                    )

                    # TODO: Extract objects from pack and upload to LakeFS
                    # 1. Walk commit tree from new_sha
                    # 2. Upload blobs to S3 or LakeFS
                    # 3. Update LakeFS branch

                return True

        except Exception as e:
            logger.exception("Failed to unpack and push", e)
            return False

    async def create_lakefs_commit(
        self, branch: str, message: str, author: str, tree_data: dict
    ) -> str:
        """Create commit in LakeFS from Git tree data.

        Args:
            branch: Branch name
            message: Commit message
            author: Author name
            tree_data: Dictionary of path -> content

        Returns:
            Commit ID
        """

        # Upload all files concurrently
        async def upload_file(path, content):
            if isinstance(content, str):
                content = content.encode("utf-8")

            await self.lakefs_client.upload_object(
                repository=self.lakefs_repo, branch=branch, path=path, content=content
            )

        await asyncio.gather(
            *[upload_file(path, content) for path, content in tree_data.items()]
        )

        # Create commit
        commit_result = await self.lakefs_client.commit(
            repository=self.lakefs_repo,
            branch=branch,
            message=message,
            metadata={"author": author},
        )

        return commit_result["id"]
