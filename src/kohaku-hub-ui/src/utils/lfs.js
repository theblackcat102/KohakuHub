// src/kohaku-hub-ui/src/utils/lfs.js
import axios from "axios";
import api from "./api";

// Create a clean axios instance for S3 uploads (no interceptors, no extra headers)
const s3Client = axios.create();

/**
 * Calculate SHA256 hash of file
 * @param {File} file - File object
 * @returns {Promise<string>} - SHA256 hex string
 */
export async function calculateSHA256(file) {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  console.log("SHA256 calculation:", {
    fileName: file.name,
    fileSize: file.size,
    arrayBufferSize: arrayBuffer.byteLength,
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
 * Upload file through Git LFS workflow
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
  );

  const lfsObject = batchResponse.data.objects[0];

  if (lfsObject.error) {
    throw new Error(`LFS batch error: ${lfsObject.error.message}`);
  }

  // If actions.upload exists, upload to S3
  if (lfsObject.actions && lfsObject.actions.upload) {
    const uploadUrl = lfsObject.actions.upload.href;
    const uploadHeaders = lfsObject.actions.upload.header || {};

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
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  if (bytes < 1024 * 1024 * 1024)
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}
