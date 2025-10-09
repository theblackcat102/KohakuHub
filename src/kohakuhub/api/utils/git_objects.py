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
                 mode: "100644" (file), "100755" (executable), "040000" (dir)

    Returns:
        (sha1_hex, object_data_with_header)
    """
    # Git requires entries sorted by name
    sorted_entries = sorted(entries, key=lambda x: x[1])

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

    for mode, path, blob_sha1 in flat_entries:
        parts = path.split("/")

        if len(parts) == 1:
            # Root-level file
            if "" not in dir_contents:
                dir_contents[""] = []
            dir_contents[""].append((mode, parts[0], blob_sha1))
        else:
            # Nested file - add to appropriate directory
            for i in range(len(parts)):
                if i == len(parts) - 1:
                    # File itself
                    dir_path = "/".join(parts[:i]) if i > 0 else ""
                    if dir_path not in dir_contents:
                        dir_contents[dir_path] = []
                    dir_contents[dir_path].append((mode, parts[i], blob_sha1))

    # Build trees bottom-up (deepest directories first)
    sorted_dirs = sorted(dir_contents.keys(), key=lambda x: x.count("/"), reverse=True)

    dir_sha1s = {}  # dir_path -> tree_sha1
    tree_objects = []  # List of (type, tree_data)

    for dir_path in sorted_dirs:
        entries = []

        for mode, name, entry_sha1 in dir_contents[dir_path]:
            # Check if this name is a subdirectory
            subdir_path = f"{dir_path}/{name}" if dir_path else name

            if subdir_path in dir_sha1s:
                # It's a directory - use tree mode and its tree SHA-1
                entries.append(("040000", name, dir_sha1s[subdir_path]))
            else:
                # It's a file - use provided mode and blob SHA-1
                entries.append((mode, name, entry_sha1))

        # Create tree object for this directory
        tree_sha1, tree_data = create_tree_object(entries)
        dir_sha1s[dir_path] = tree_sha1
        tree_objects.append((2, tree_data))  # Type 2 = tree

    # Return root tree SHA-1
    root_sha1 = dir_sha1s.get("")
    if not root_sha1 and sorted_dirs:
        # Fallback if no root (shouldn't happen)
        root_sha1 = dir_sha1s[sorted_dirs[-1]]

    return root_sha1, tree_objects
