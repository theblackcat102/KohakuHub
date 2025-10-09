"""Pure Python Git object construction - NO native dependencies, NO file I/O.

All operations are in-memory and deterministic.
"""

import hashlib
import struct
import zlib


def compute_git_object_sha1(obj_type: str, content: bytes) -> str:
    """Compute Git object SHA-1.

    Args:
        obj_type: Object type ("blob", "tree", "commit")
        content: Object content (without header)

    Returns:
        SHA-1 hex digest
    """
    header = f"{obj_type} {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def create_blob_object(content: bytes) -> tuple[str, bytes]:
    """Create Git blob object.

    Args:
        content: File content

    Returns:
        (sha1_hex, object_data_with_header)
    """
    header = f"blob {len(content)}\0".encode()
    obj_data = header + content
    sha1 = hashlib.sha1(obj_data).hexdigest()
    return sha1, obj_data


def create_tree_object(entries: list[tuple[str, str, str]]) -> tuple[str, bytes]:
    """Create Git tree object.

    Args:
        entries: List of (mode, name, sha1_hex)
                 mode: "100644" (file), "100755" (executable), "40000" (dir)

    Returns:
        (sha1_hex, object_data_with_header)
    """

    # Git requires special sorting: directories are sorted as if they have trailing "/"
    # This is critical for correct tree SHA-1!
    def sort_key(entry):
        mode, name, sha1 = entry
        # Directories (mode 40000 or 040000) get trailing "/" for sorting
        if mode in ("40000", "040000"):
            return name + "/"
        return name

    sorted_entries = sorted(entries, key=sort_key)

    # Build tree content
    tree_content = b""
    for mode, name, sha1_hex in sorted_entries:
        sha1_bytes = bytes.fromhex(sha1_hex)
        tree_content += f"{mode} {name}\0".encode() + sha1_bytes

    # Add header
    header = f"tree {len(tree_content)}\0".encode()
    obj_data = header + tree_content
    sha1 = hashlib.sha1(obj_data).hexdigest()

    return sha1, obj_data


def create_commit_object(
    tree_sha1: str,
    parent_sha1s: list[str],
    author_name: str,
    author_email: str,
    committer_name: str,
    committer_email: str,
    author_timestamp: int,
    committer_timestamp: int,
    timezone: str,
    message: str,
) -> tuple[str, bytes]:
    """Create Git commit object.

    Args:
        tree_sha1: Tree SHA-1
        parent_sha1s: List of parent commit SHA-1s (empty for initial commit)
        author_name: Author name
        author_email: Author email
        committer_name: Committer name
        committer_email: Committer email
        author_timestamp: Unix timestamp
        committer_timestamp: Unix timestamp
        timezone: Timezone offset (e.g., "+0000", "+0800")
        message: Commit message

    Returns:
        (sha1_hex, object_data_with_header)
    """
    lines = [f"tree {tree_sha1}"]

    # Add parents
    for parent_sha1 in parent_sha1s:
        lines.append(f"parent {parent_sha1}")

    # Add author and committer
    author_line = f"{author_name} <{author_email}> {author_timestamp} {timezone}"
    committer_line = (
        f"{committer_name} <{committer_email}> {committer_timestamp} {timezone}"
    )

    lines.append(f"author {author_line}")
    lines.append(f"committer {committer_line}")

    # Empty line before message
    lines.append("")

    # Add message
    lines.append(message)

    commit_content = "\n".join(lines).encode("utf-8")

    # Add header
    header = f"commit {len(commit_content)}\0".encode()
    obj_data = header + commit_content
    sha1 = hashlib.sha1(obj_data).hexdigest()

    return sha1, obj_data


def encode_pack_object_header(obj_type: int, size: int) -> bytes:
    """Encode pack object header (type + size in variable-length encoding).

    Args:
        obj_type: Git object type (1=commit, 2=tree, 3=blob, 4=tag)
        size: Uncompressed object size

    Returns:
        Variable-length encoded header bytes
    """
    # First byte: bits 4-6 = type, bits 0-3 = size low 4 bits, bit 7 = continuation
    first_byte = (obj_type << 4) | (size & 0x0F)
    size >>= 4

    result = []

    if size > 0:
        first_byte |= 0x80  # Set MSB to indicate more bytes
        result.append(first_byte)

        # Encode remaining size bytes
        while size > 0:
            byte = size & 0x7F
            size >>= 7
            if size > 0:
                byte |= 0x80  # More bytes follow
            result.append(byte)
    else:
        result.append(first_byte)

    return bytes(result)


def create_pack_file(objects: list[tuple[int, bytes]]) -> bytes:
    """Create Git pack file from objects.

    Args:
        objects: List of (type, object_data_with_header) tuples
                 Types: 1=commit, 2=tree, 3=blob

    Returns:
        Complete pack file bytes
    """
    # Pack header: "PACK" + version (2) + count
    pack_data = b"PACK"
    pack_data += struct.pack(">I", 2)  # Version 2
    pack_data += struct.pack(">I", len(objects))  # Object count

    # Add each object
    for obj_type, obj_data in objects:
        # Extract content (remove "type size\0" header)
        null_pos = obj_data.find(b"\0")
        if null_pos > 0:
            content = obj_data[null_pos + 1 :]
        else:
            # No header, use as-is
            content = obj_data

        # Encode object header (type + size)
        header_bytes = encode_pack_object_header(obj_type, len(content))

        # Compress content with zlib
        compressed = zlib.compress(content)

        # Add to pack
        pack_data += header_bytes + compressed

    # Add pack checksum (SHA-1 of everything above)
    checksum = hashlib.sha1(pack_data).digest()
    pack_data += checksum

    return pack_data


def create_empty_pack_file() -> bytes:
    """Create empty Git pack file (0 objects).

    Returns:
        Empty pack file bytes
    """
    pack_data = b"PACK"
    pack_data += struct.pack(">I", 2)  # Version 2
    pack_data += struct.pack(">I", 0)  # 0 objects
    checksum = hashlib.sha1(pack_data).digest()
    return pack_data + checksum


def build_nested_trees(
    flat_entries: list[tuple[str, str, str]],
) -> tuple[str, list[tuple[int, bytes]]]:
    """Build nested tree structure from flat file list.

    Args:
        flat_entries: List of (mode, path, blob_sha1)
                     e.g., [("100644", "models/config.json", "abc123...")]

    Returns:
        (root_tree_sha1, list_of_tree_objects)
        tree_objects: List of (type=2, tree_data_with_header)
    """
    # Organize entries by directory
    dir_contents = {}  # dir_path -> [(mode, name, sha1)]
    all_dirs = set()  # Track all directories we need to create

    for mode, path, blob_sha1 in flat_entries:
        parts = path.split("/")

        # Add file to its parent directory
        if len(parts) == 1:
            # Root-level file
            dir_path = ""
        else:
            # Nested file
            dir_path = "/".join(parts[:-1])

        if dir_path not in dir_contents:
            dir_contents[dir_path] = []

        file_name = parts[-1]
        dir_contents[dir_path].append((mode, file_name, blob_sha1))

        # Track all parent directories
        for i in range(1, len(parts)):
            parent_dir = "/".join(parts[:i])
            all_dirs.add(parent_dir)

    # Ensure all directories exist in dir_contents (even if empty)
    for dir_path in all_dirs:
        if dir_path not in dir_contents:
            dir_contents[dir_path] = []

    # Build trees bottom-up (deepest directories first, ROOT LAST!)
    def sort_dirs(dir_path):
        # Root ("") must be last, so give it LOWEST value (reverse=True → descending)
        if dir_path == "":
            return (-999, "")  # Lowest value, processed last
        else:
            return (dir_path.count("/"), dir_path)

    sorted_dirs = sorted(dir_contents.keys(), key=sort_dirs, reverse=True)

    dir_sha1s = {}  # dir_path -> tree_sha1
    tree_objects = []  # List of (type, tree_data)

    for dir_path in sorted_dirs:
        entries = []

        # Add files in this directory
        for mode, name, entry_sha1 in dir_contents[dir_path]:
            entries.append((mode, name, entry_sha1))

        # DEBUG: Log what we're adding to this directory
        print(
            f"DEBUG: Building tree for '{dir_path}', files: {len(dir_contents[dir_path])}"
        )

        # Add subdirectories that have been processed (bottom-up)
        # Find all direct children of this directory
        subdirs_added = 0
        for child_dir_path, child_tree_sha1 in dir_sha1s.items():
            # Check if child_dir_path is a direct child of dir_path
            if dir_path == "":
                # Root directory - find top-level dirs
                if "/" not in child_dir_path and child_dir_path:
                    # Top-level directory like "images"
                    dir_name = child_dir_path
                    # Check not already added as file
                    if not any(name == dir_name for _, name, _ in entries):
                        entries.append(("40000", dir_name, child_tree_sha1))
                        subdirs_added += 1
                        print(
                            f"  DEBUG: Added subdir to root: {dir_name} → {child_tree_sha1[:8]}"
                        )
            else:
                # Non-root directory - find direct children
                prefix = dir_path + "/"
                if child_dir_path.startswith(prefix):
                    remainder = child_dir_path[len(prefix) :]
                    if "/" not in remainder:
                        # Direct child (e.g., "images/samples" is child of "images")
                        dir_name = remainder
                        if not any(name == dir_name for _, name, _ in entries):
                            entries.append(("40000", dir_name, child_tree_sha1))
                            subdirs_added += 1
                            print(
                                f"  DEBUG: Added subdir to {dir_path}: {dir_name} → {child_tree_sha1[:8]}"
                            )

        print(
            f"  DEBUG: Total entries: {len(entries)} ({len(dir_contents[dir_path])} files + {subdirs_added} subdirs)"
        )

        # Create tree object for this directory
        if entries:
            tree_sha1, tree_data = create_tree_object(entries)
            dir_sha1s[dir_path] = tree_sha1
            tree_objects.append((2, tree_data))  # Type 2 = tree
            print(f"  DEBUG: Created tree {tree_sha1[:8]} with {len(entries)} entries")
        else:
            # Empty directory - create empty tree
            tree_sha1, tree_data = create_tree_object([])
            dir_sha1s[dir_path] = tree_sha1
            tree_objects.append((2, tree_data))
            print(f"  DEBUG: Created empty tree {tree_sha1[:8]}")

    # Return root tree SHA-1
    root_sha1 = dir_sha1s.get("")
    if not root_sha1 and sorted_dirs:
        # Fallback if no root (shouldn't happen)
        root_sha1 = dir_sha1s[sorted_dirs[-1]]

    return root_sha1, tree_objects
