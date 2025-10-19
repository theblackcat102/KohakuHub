/**
 * Tag parsing utilities for repository metadata
 */

/**
 * Parse tags and categorize them
 * @param {Array<string>} tags - Raw tags array from API
 * @returns {Object} Categorized tags
 */
export function parseTags(tags) {
  if (!tags || !Array.isArray(tags)) {
    return {
      datasets: [],
      cleanTags: [],
    };
  }

  const datasets = [];
  const metadataPrefixes = [
    "dataset:",
    "license:",
    "region:",
    "language:",
    "library:",
    "pipeline:",
    "task_categories:",
    "task_ids:",
    "size_categories:",
    "format:",
    "modality:",
    "source:",
    "annotations_creators:",
    "language_creators:",
    "multilinguality:",
    "pretty_name:",
    "diffusers:",
    "transformers:",
    "timm:",
    "peft:",
    "sentence-transformers:",
    "sklearn:",
    "tensorboard:",
    "pytorch:",
    "tensorflow:",
    "jax:",
    "endpoints_compatible",
    "autotrain_compatible",
    "text-generation-inference",
    "has_space",
    "arxiv:",
    "doi:",
  ];

  const cleanTags = tags.filter((tag) => {
    // Extract dataset references
    if (tag.startsWith("dataset:")) {
      const datasetId = tag.substring(8); // Remove 'dataset:' prefix
      if (datasetId) {
        datasets.push(datasetId);
      }
      return false; // Remove from clean tags
    }

    // Filter out metadata-like tags
    for (const prefix of metadataPrefixes) {
      if (tag.startsWith(prefix) || tag === prefix) {
        return false;
      }
    }

    return true;
  });

  return {
    datasets,
    cleanTags,
  };
}

/**
 * Check if there are any clean tags to display
 * @param {Array<string>} tags - Raw tags array
 * @returns {boolean} True if there are displayable tags
 */
export function hasCleanTags(tags) {
  const { cleanTags } = parseTags(tags);
  return cleanTags.length > 0;
}
