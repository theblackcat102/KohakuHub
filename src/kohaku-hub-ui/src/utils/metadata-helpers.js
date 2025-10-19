/**
 * Helper utilities for repository metadata display
 */

/**
 * Language ISO 639-1 code to full name mapping
 * @param {string} code - ISO 639-1 language code
 * @returns {string} Full language name
 */
export function getLanguageName(code) {
  const languageMap = {
    en: "English",
    zh: "Chinese",
    ja: "Japanese",
    ko: "Korean",
    es: "Spanish",
    fr: "French",
    de: "German",
    it: "Italian",
    pt: "Portuguese",
    ru: "Russian",
    ar: "Arabic",
    hi: "Hindi",
    nl: "Dutch",
    pl: "Polish",
    tr: "Turkish",
    vi: "Vietnamese",
    th: "Thai",
    id: "Indonesian",
    he: "Hebrew",
    sv: "Swedish",
    fi: "Finnish",
    da: "Danish",
    no: "Norwegian",
    cs: "Czech",
    ro: "Romanian",
    uk: "Ukrainian",
    el: "Greek",
    hu: "Hungarian",
    sk: "Slovak",
    bg: "Bulgarian",
    hr: "Croatian",
    sr: "Serbian",
    ca: "Catalan",
    multilingual: "Multilingual",
    code: "Code",
  };
  return languageMap[code] || code.toUpperCase();
}

/**
 * Get standard license documentation link
 * @param {string} license - License identifier
 * @returns {string|null} License documentation URL
 */
export function getStandardLicenseLink(license) {
  if (!license) return null;

  const licenseLinks = {
    mit: "https://opensource.org/licenses/MIT",
    "apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
    "gpl-3.0": "https://www.gnu.org/licenses/gpl-3.0.html",
    "gpl-2.0": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
    "lgpl-3.0": "https://www.gnu.org/licenses/lgpl-3.0.html",
    "bsd-3-clause": "https://opensource.org/licenses/BSD-3-Clause",
    "bsd-2-clause": "https://opensource.org/licenses/BSD-2-Clause",
    "mpl-2.0": "https://www.mozilla.org/en-US/MPL/2.0/",
    "cc0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc-by-nc-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nc-sa-4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    unlicense: "https://unlicense.org/",
    isc: "https://opensource.org/licenses/ISC",
    "artistic-2.0": "https://opensource.org/licenses/Artistic-2.0",
    "epl-2.0": "https://www.eclipse.org/legal/epl-2.0/",
  };

  return licenseLinks[license.toLowerCase()] || null;
}

/**
 * Format metadata key from snake_case to Title Case
 * @param {string} key - Metadata key in snake_case
 * @returns {string} Formatted key
 */
export function formatMetadataKey(key) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

/**
 * Get friendly name for license
 * @param {string} license - License identifier
 * @returns {string} Friendly license name
 */
export function getLicenseName(license) {
  const licenseNames = {
    mit: "MIT License",
    "apache-2.0": "Apache License 2.0",
    "gpl-3.0": "GNU GPL v3.0",
    "gpl-2.0": "GNU GPL v2.0",
    "lgpl-3.0": "GNU LGPL v3.0",
    "bsd-3-clause": "BSD 3-Clause",
    "bsd-2-clause": "BSD 2-Clause",
    "mpl-2.0": "Mozilla Public License 2.0",
    "cc0-1.0": "CC0 1.0 Universal",
    "cc-by-4.0": "CC BY 4.0",
    "cc-by-sa-4.0": "CC BY-SA 4.0",
    "cc-by-nc-4.0": "CC BY-NC 4.0",
    "cc-by-nc-sa-4.0": "CC BY-NC-SA 4.0",
    unlicense: "The Unlicense",
    isc: "ISC License",
    other: "Other License",
  };
  return licenseNames[license.toLowerCase()] || license.toUpperCase();
}

/**
 * Get friendly name for pipeline tag
 * @param {string} tag - Pipeline tag
 * @returns {string} Friendly pipeline name
 */
export function getPipelineTagName(tag) {
  const pipelineNames = {
    "text-classification": "Text Classification",
    "token-classification": "Token Classification",
    "text-generation": "Text Generation",
    "text2text-generation": "Text-to-Text Generation",
    "fill-mask": "Fill Mask",
    "question-answering": "Question Answering",
    translation: "Translation",
    summarization: "Summarization",
    conversational: "Conversational",
    "feature-extraction": "Feature Extraction",
    "sentence-similarity": "Sentence Similarity",
    "zero-shot-classification": "Zero-Shot Classification",
    "image-classification": "Image Classification",
    "object-detection": "Object Detection",
    "image-segmentation": "Image Segmentation",
    "image-to-text": "Image-to-Text",
    "text-to-image": "Text-to-Image",
    "image-to-image": "Image-to-Image",
    "audio-classification": "Audio Classification",
    "automatic-speech-recognition": "Speech Recognition",
    "text-to-speech": "Text-to-Speech",
    "audio-to-audio": "Audio-to-Audio",
    "video-classification": "Video Classification",
    "reinforcement-learning": "Reinforcement Learning",
    "tabular-classification": "Tabular Classification",
    "tabular-regression": "Tabular Regression",
  };
  return pipelineNames[tag] || formatMetadataKey(tag);
}

/**
 * Get friendly name for task category
 * @param {string} task - Task category
 * @returns {string} Friendly task name
 */
export function getTaskCategoryName(task) {
  return getPipelineTagName(task);
}

/**
 * Format size category
 * @param {string} size - Size category (e.g., "1K<n<10K")
 * @returns {string} Formatted size
 */
export function formatSizeCategory(size) {
  return size.replace(/n/g, "N").replace(/</g, " < ").replace(/>/g, " > ");
}
