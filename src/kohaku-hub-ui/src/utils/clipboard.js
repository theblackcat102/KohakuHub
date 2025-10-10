/**
 * Copy text to clipboard with fallback for non-secure contexts
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} - True if successful
 */
export async function copyToClipboard(text) {
  // Try modern Clipboard API first (requires HTTPS or localhost)
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn(
        "Clipboard API failed, falling back to textarea method:",
        err,
      );
    }
  }

  // Fallback for non-secure contexts (HTTP)
  return copyToClipboardFallback(text);
}

/**
 * Fallback method using textarea (works in non-secure contexts)
 * @param {string} text - Text to copy
 * @returns {boolean} - True if successful
 */
function copyToClipboardFallback(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "-9999px";
  document.body.appendChild(textarea);

  try {
    textarea.select();
    textarea.setSelectionRange(0, text.length);
    const successful = document.execCommand("copy");
    document.body.removeChild(textarea);
    return successful;
  } catch (err) {
    console.error("Fallback copy failed:", err);
    document.body.removeChild(textarea);
    return false;
  }
}
