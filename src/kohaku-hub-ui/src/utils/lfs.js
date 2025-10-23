// src/kohaku-hub-ui/src/utils/lfs.js
import axios from "axios";
import { sha256 } from "js-sha256";
import api from "./api";

// Create a clean axios instance for S3 uploads (no interceptors, no extra headers)
// No timeout for S3 uploads - they can take a long time for large files
const s3Client = axios.create({
  timeout: 0, // No timeout for S3 uploads
});

/**
 * Calculate SHA256 hash of file using incremental hashing (memory efficient for large files)
 * Uses js-sha256 library which supports incremental hashing
 * @param {File} file - File object
 * @param {Function} onProgress - Progress callback (0.0 to 1.0)
 * @returns {Promise<string>} - SHA256 hex string
 */
export async function calculateSHA256(file, onProgress) {
  console.log(
    `Calculating SHA256 for ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)...`,
  );

  // Use incremental hashing with js-sha256
  // Process file in chunks to avoid memory issues
  const CHUNK_SIZE = 64 * 1024 * 1024; // 64MB chunks
  const chunkCount = Math.ceil(file.size / CHUNK_SIZE);

  console.log(
    `Using incremental hashing: ${chunkCount} chunks of ${CHUNK_SIZE / 1024 / 1024}MB`,
  );

  // Create hash instance for incremental updates
  const hash = sha256.create();
  let offset = 0;

  for (let i = 0; i < chunkCount; i++) {
    const end = Math.min(offset + CHUNK_SIZE, file.size);
    const chunk = file.slice(offset, end);

    // Read chunk as ArrayBuffer
    const buffer = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = () => reject(new Error("Failed to read file chunk"));
      reader.readAsArrayBuffer(chunk);
    });

    // Update hash with this chunk (incremental)
    hash.update(new Uint8Array(buffer));

    // Report progress
    const progress = end / file.size;
    if (onProgress) {
      onProgress(progress);
    }

    // Log progress (less frequent to reduce console spam)
    if ((i + 1) % 5 === 0 || i === chunkCount - 1) {
      const progressPct = (progress * 100).toFixed(1);
      console.log(
        `  Hashing progress: ${i + 1}/${chunkCount} chunks (${progressPct}%)`,
      );
    }

    offset = end;
  }

  // Finalize hash
  const hashHex = hash.hex();

  console.log("SHA256 calculation completed:", {
    fileName: file.name,
    fileSize: file.size,
    sha256: hashHex,
  });

  return hashHex;
}

/**
 * Verify file content matches expected SHA256
 * @param {File} file - File object
 * @param {string} expectedSHA256 - Expected SHA256 hash
 * @returns {Promise<boolean>} - True if match
 */
export async function verifyFileSHA256(file, expectedSHA256) {
  const actualSHA256 = await calculateSHA256(file);
  return actualSHA256 === expectedSHA256;
}

/**
 * Slice file into parts for multipart upload
 * @param {File} file - File to slice
 * @param {number} chunkSize - Size of each chunk in bytes
 * @returns {Array<{partNumber: number, blob: Blob, start: number, end: number}>}
 */
function sliceFileIntoParts(file, chunkSize) {
  const parts = [];
  const totalSize = file.size;
  let partNumber = 1;

  for (let start = 0; start < totalSize; start += chunkSize) {
    const end = Math.min(start + chunkSize, totalSize);
    const blob = file.slice(start, end);

    parts.push({
      partNumber,
      blob,
      start,
      end,
      size: end - start,
    });

    partNumber++;
  }

  return parts;
}

/**
 * Upload a single part with retry logic using native fetch (no preflight)
 * @param {Blob} partBlob - Part data
 * @param {string} partUrl - Presigned URL for this part
 * @param {number} partNumber - Part number (1-indexed)
 * @param {Function} onProgress - Progress callback for this part
 * @param {number} maxRetries - Maximum retry attempts
 * @returns {Promise<{PartNumber: number, ETag: string}>}
 */
async function uploadPartWithRetry(
  partBlob,
  partUrl,
  partNumber,
  onProgress,
  maxRetries = 3,
) {
  let lastError = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(
        `Uploading part ${partNumber} (attempt ${attempt}/${maxRetries})`,
      );

      // Use native fetch instead of axios to avoid automatic headers and preflight
      const xhr = new XMLHttpRequest();

      const uploadPromise = new Promise((resolve, reject) => {
        xhr.open("PUT", partUrl);

        // Track upload progress
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable && onProgress) {
            onProgress(e.loaded / e.total);
          }
        });

        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(xhr);
          } else {
            reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
          }
        });

        xhr.addEventListener("error", () => {
          reject(new Error("Network error during upload"));
        });

        xhr.addEventListener("abort", () => {
          reject(new Error("Upload aborted"));
        });

        // Send the blob directly - no extra headers added
        xhr.send(partBlob);
      });

      const response = await uploadPromise;

      // Extract ETag from response header (S3 returns it with quotes)
      const etag = response.getResponseHeader("ETag");
      if (!etag) {
        throw new Error(`No ETag returned for part ${partNumber}`);
      }

      // Remove quotes from ETag if present
      const cleanEtag = etag.replace(/^"(.*)"$/, "$1");

      console.log(
        `Part ${partNumber} uploaded successfully, ETag: ${cleanEtag}`,
      );

      return {
        PartNumber: partNumber,
        ETag: cleanEtag,
      };
    } catch (error) {
      lastError = error;
      console.error(
        `Part ${partNumber} upload failed (attempt ${attempt}):`,
        error,
      );

      // Don't retry on certain errors (403/404 are permission issues)
      if (
        error.message &&
        (error.message.includes("403") || error.message.includes("404"))
      ) {
        throw error;
      }

      // Wait before retry (exponential backoff)
      if (attempt < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw new Error(
    `Failed to upload part ${partNumber} after ${maxRetries} attempts: ${lastError?.message}`,
  );
}

/**
 * Upload parts in parallel with concurrency control
 * @param {Array} parts - Array of part objects from sliceFileIntoParts
 * @param {Object} partUrls - Map of part number to presigned URL
 * @param {number} concurrency - Maximum concurrent uploads
 * @param {Function} onProgress - Overall progress callback
 * @returns {Promise<Array<{PartNumber: number, ETag: string}>>}
 */
async function uploadPartsInParallel(parts, partUrls, concurrency, onProgress) {
  const totalParts = parts.length;
  const totalSize = parts.reduce((sum, part) => sum + part.size, 0);
  const partProgress = {}; // Track progress per part
  const completedParts = []; // Collect completed parts with ETags

  // Calculate overall progress
  const updateProgress = () => {
    const loadedBytes = parts.reduce((sum, part) => {
      const progress = partProgress[part.partNumber] || 0;
      return sum + part.size * progress;
    }, 0);
    const overallProgress = loadedBytes / totalSize;
    if (onProgress) {
      onProgress(overallProgress);
    }
  };

  // Create upload tasks
  const uploadTasks = parts.map((part) => async () => {
    const partUrl = partUrls[part.partNumber];
    if (!partUrl) {
      throw new Error(`No URL found for part ${part.partNumber}`);
    }

    const partResult = await uploadPartWithRetry(
      part.blob,
      partUrl,
      part.partNumber,
      (progress) => {
        partProgress[part.partNumber] = progress;
        updateProgress();
      },
    );

    completedParts.push(partResult);
    return partResult;
  });

  // Execute with concurrency control
  const results = [];
  const executing = [];

  for (const task of uploadTasks) {
    const promise = task().then((result) => {
      executing.splice(executing.indexOf(promise), 1);
      return result;
    });

    results.push(promise);
    executing.push(promise);

    if (executing.length >= concurrency) {
      await Promise.race(executing);
    }
  }

  // Wait for all uploads to complete
  await Promise.all(results);

  // Sort parts by PartNumber for completion request
  completedParts.sort((a, b) => a.PartNumber - b.PartNumber);

  return completedParts;
}

/**
 * Upload large file using multipart upload
 * @param {string} repoId - Repository ID (namespace/name)
 * @param {File} file - File to upload
 * @param {string} sha256 - Pre-calculated SHA256 hash
 * @param {Object} lfsObject - LFS batch response object with multipart info
 * @param {Function} onProgress - Progress callback
 * @returns {Promise<Object>} - { oid: string, size: number }
 */
async function uploadLFSFileMultipart(
  repoId,
  file,
  sha256,
  lfsObject,
  onProgress,
) {
  const uploadAction = lfsObject.actions.upload;
  const header = uploadAction.header;

  // Extract multipart configuration from header
  const chunkSize = parseInt(header.chunk_size);
  const uploadId = header.upload_id;
  const completionUrl = uploadAction.href;

  console.log("Starting multipart upload:", {
    oid: sha256.substring(0, 8),
    fileSize: file.size,
    chunkSize,
    uploadId,
  });

  // Extract part URLs from header (numeric keys "1", "2", "3", ...)
  const partUrls = {};
  for (const key in header) {
    if (/^\d+$/.test(key)) {
      // Check if key is numeric
      partUrls[parseInt(key)] = header[key];
    }
  }

  console.log(`Found ${Object.keys(partUrls).length} part URLs`);

  // Slice file into parts
  const parts = sliceFileIntoParts(file, chunkSize);
  console.log(`File sliced into ${parts.length} parts`);

  if (parts.length !== Object.keys(partUrls).length) {
    console.warn(
      `Part count mismatch: file has ${parts.length} parts, but backend provided ${Object.keys(partUrls).length} URLs`,
    );
  }

  // Upload parts in parallel (4 concurrent)
  const completedParts = await uploadPartsInParallel(
    parts,
    partUrls,
    4, // Concurrency limit
    onProgress,
  );

  console.log(
    `All ${completedParts.length} parts uploaded, completing multipart upload`,
  );

  // Complete multipart upload
  try {
    await s3Client.post(completionUrl, {
      oid: sha256,
      size: file.size,
      parts: completedParts,
    });

    console.log("Multipart upload completed successfully");
  } catch (error) {
    console.error("Failed to complete multipart upload:", error);
    throw new Error(`Multipart completion failed: ${error.message}`);
  }

  // Verify upload (optional but recommended)
  if (lfsObject.actions.verify) {
    try {
      await s3Client.post(lfsObject.actions.verify.href, {
        oid: sha256,
        size: file.size,
      });
      console.log("LFS verification successful");
    } catch (error) {
      // Verification failure is non-fatal - file is already uploaded
      console.warn("LFS verification failed (non-fatal):", error);
    }
  }

  return {
    oid: sha256,
    size: file.size,
  };
}

/**
 * Upload file through Git LFS workflow (supports both single-part and multipart)
 * @param {string} repoId - Repository ID (namespace/name)
 * @param {File} file - File to upload
 * @param {string} sha256 - Pre-calculated SHA256 hash
 * @param {Function} onProgress - Progress callback
 * @returns {Promise<Object>} - { oid: string, size: number }
 */
export async function uploadLFSFile(repoId, file, sha256, onProgress) {
  const size = file.size;

  // Call LFS batch API to get upload URL
  const batchResponse = await api.post(
    `/${repoId}.git/info/lfs/objects/batch`,
    {
      operation: "upload",
      transfers: ["basic"],
      objects: [
        {
          oid: sha256,
          size: size,
        },
      ],
      hash_algo: "sha256",
      is_browser: true, // Tell backend to include Content-Type in presigned URL signature
    },
    {
      timeout: 60000, // 60 seconds for LFS batch API
    },
  );

  const lfsObject = batchResponse.data.objects[0];

  if (lfsObject.error) {
    throw new Error(`LFS batch error: ${lfsObject.error.message}`);
  }

  // If actions.upload exists, upload to S3
  if (lfsObject.actions && lfsObject.actions.upload) {
    const uploadHeaders = lfsObject.actions.upload.header || {};

    // Check if this is a multipart upload (presence of chunk_size in header)
    const isMultipart = uploadHeaders.chunk_size !== undefined;

    if (isMultipart) {
      console.log("Using multipart upload for large file");
      return await uploadLFSFileMultipart(
        repoId,
        file,
        sha256,
        lfsObject,
        onProgress,
      );
    }

    // Single-part upload (original working implementation)
    const uploadUrl = lfsObject.actions.upload.href;

    console.log("LFS batch response headers:", uploadHeaders);
    console.log("Upload URL:", uploadUrl);

    // Upload file to S3 using presigned URL
    // Use clean axios instance (no auth interceptors)
    try {
      await s3Client.put(uploadUrl, file, {
        headers: uploadHeaders,
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = progressEvent.loaded / progressEvent.total;
            onProgress(progress);
          }
        },
      });

      console.log("S3 upload successful");
    } catch (error) {
      console.error("S3 upload failed:", error);
      console.error("Upload URL:", uploadUrl);
      console.error("Headers sent:", uploadHeaders);
      if (error.response) {
        console.error("Response status:", error.response.status);
        console.error("Response data:", error.response.data);
      }
      throw error;
    }

    // Verify upload (optional but recommended)
    if (lfsObject.actions.verify) {
      try {
        // Use s3Client (no credentials) for verify to avoid CORS issues
        await s3Client.post(lfsObject.actions.verify.href, {
          oid: sha256,
          size: size,
        });
        console.log("LFS verification successful");
      } catch (error) {
        // Verification failure is non-fatal - file is already uploaded
        console.warn("LFS verification failed (non-fatal):", error);
      }
    }
  } else {
    // File already exists in LFS storage (deduplication)
    console.log(`LFS file already exists (${sha256})`);
  }

  return {
    oid: sha256,
    size: size,
  };
}

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted size string
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  if (bytes < 1000) return bytes + " B";
  if (bytes < 1000 * 1000) return (bytes / 1000).toFixed(1) + " KB";
  if (bytes < 1000 * 1000 * 1000)
    return (bytes / (1000 * 1000)).toFixed(1) + " MB";
  return (bytes / (1000 * 1000 * 1000)).toFixed(1) + " GB";
}
