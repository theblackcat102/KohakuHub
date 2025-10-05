// src/kohaku-hub-ui/src/utils/markdown.js
import MarkdownIt from "markdown-it";
import DOMPurify from "isomorphic-dompurify";
import hljs from "highlight.js/lib/core";

// Import only the languages you need (reduces bundle size)
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import python from "highlight.js/lib/languages/python";
import java from "highlight.js/lib/languages/java";
import cpp from "highlight.js/lib/languages/cpp";
import csharp from "highlight.js/lib/languages/csharp";
import go from "highlight.js/lib/languages/go";
import rust from "highlight.js/lib/languages/rust";
import php from "highlight.js/lib/languages/php";
import ruby from "highlight.js/lib/languages/ruby";
import swift from "highlight.js/lib/languages/swift";
import kotlin from "highlight.js/lib/languages/kotlin";
import shell from "highlight.js/lib/languages/shell";
import bash from "highlight.js/lib/languages/bash";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";
import yaml from "highlight.js/lib/languages/yaml";
import markdown from "highlight.js/lib/languages/markdown";
import css from "highlight.js/lib/languages/css";
import sql from "highlight.js/lib/languages/sql";

// Register languages
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("python", python);
hljs.registerLanguage("java", java);
hljs.registerLanguage("cpp", cpp);
hljs.registerLanguage("csharp", csharp);
hljs.registerLanguage("go", go);
hljs.registerLanguage("rust", rust);
hljs.registerLanguage("php", php);
hljs.registerLanguage("ruby", ruby);
hljs.registerLanguage("swift", swift);
hljs.registerLanguage("kotlin", kotlin);
hljs.registerLanguage("shell", shell);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("json", json);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("yaml", yaml);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("css", css);
hljs.registerLanguage("sql", sql);

/**
 * Create markdown renderer with XSS protection and syntax highlighting
 * Using blacklist approach to allow HTML+CSS galleries
 */
const md = new MarkdownIt({
  html: true, // Enable HTML tags in source
  linkify: true, // Auto-convert URLs to links
  typographer: true, // Enable smart quotes and other typographic replacements
  breaks: true, // Convert \n to <br>
  highlight: function (code, lang) {
    // Use highlight.js for syntax highlighting
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value;
      } catch (e) {
        console.error("Highlight error:", e);
      }
    }
    // Fallback to plain code
    return md.utils.escapeHtml(code);
  },
});

/**
 * Add support for GitHub-style task lists
 * Converts - [ ] and - [x] to checkboxes
 */
md.core.ruler.after("inline", "task-lists", function (state) {
  const tokens = state.tokens;
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].type !== "inline") continue;

    const children = tokens[i].children;
    for (let j = 0; j < children.length; j++) {
      const token = children[j];
      if (token.type !== "text") continue;

      const content = token.content;
      // Match [ ] or [x] or [X] at the start of list items
      const match = content.match(/^\[([ xX])\]\s+/);
      if (!match) continue;

      // Create checkbox element
      const isChecked = match[1].toLowerCase() === "x";
      const checkbox = new state.Token("html_inline", "", 0);
      checkbox.content = `<input type="checkbox" disabled ${isChecked ? "checked" : ""} class="task-list-checkbox"> `;

      // Create remaining text
      const remainingText = new state.Token("text", "", 0);
      remainingText.content = content.slice(match[0].length);

      // Replace the token
      children.splice(j, 1, checkbox, remainingText);
      break;
    }
  }
  return true;
});

/**
 * Sanitize HTML with blacklist approach
 * Allows most HTML/CSS but removes dangerous elements
 *
 * @param {string} html - Raw HTML to sanitize
 * @returns {string} - Sanitized HTML
 */
export function sanitizeHTML(html) {
  if (!html) return "";

  return DOMPurify.sanitize(html, {
    // Blacklist dangerous tags
    // Note: We allow 'input' for radio-based image galleries and task list checkboxes
    FORBID_TAGS: [
      "script",
      "iframe",
      "object",
      "embed",
      "applet",
      "meta",
      "link",
      "base",
      "form",
      "button",
      "textarea",
      "select",
    ],

    // Blacklist dangerous attributes
    FORBID_ATTR: [
      "onerror",
      "onload",
      "onclick",
      "onmouseover",
      "onfocus",
      "onblur",
      "onchange",
      "onsubmit",
    ],

    // Allow data attributes and styles for galleries
    ALLOW_DATA_ATTR: true,
    ALLOW_UNKNOWN_PROTOCOLS: false,

    // Sanitize CSS in style attributes
    SANITIZE_DOM: true,
    KEEP_CONTENT: true,

    // Allow MathML and SVG
    USE_PROFILES: {
      html: true,
      svg: true,
      mathMl: false,
    },
  });
}

/**
 * Strip YAML frontmatter from markdown content
 * HuggingFace repo cards use YAML frontmatter for metadata
 *
 * @param {string} markdown - Markdown text with potential YAML frontmatter
 * @returns {string} - Markdown without frontmatter
 */
export function stripYAMLFrontmatter(markdown) {
  if (!markdown) return "";

  // Match YAML frontmatter: starts with ---, ends with ---
  const frontmatterRegex = /^---\s*\n([\s\S]*?\n)?---\s*\n/;
  return markdown.replace(frontmatterRegex, "");
}

/**
 * Transform relative image paths to absolute repository URLs
 *
 * @param {string} html - HTML with potential relative image paths
 * @param {Object} repoContext - Repository context for path resolution
 * @returns {string} - HTML with absolute image paths
 */
function resolveImagePaths(html, repoContext) {
  if (!html || !repoContext) return html;

  const { repoType, namespace, name, branch } = repoContext;
  const baseUrl = `/${repoType}s/${namespace}/${name}/resolve/${branch}`;

  // Create a DOM parser
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  // Find all img tags
  const images = doc.querySelectorAll("img");

  images.forEach((img) => {
    const src = img.getAttribute("src");
    if (src && !isAbsoluteUrl(src)) {
      // Remove leading ./ if present
      const cleanPath = src.replace(/^\.\//, "");
      img.setAttribute("src", `${baseUrl}/${cleanPath}`);
    }
  });

  return doc.body.innerHTML;
}

/**
 * Check if URL is absolute
 *
 * @param {string} url - URL to check
 * @returns {boolean} - True if URL is absolute
 */
function isAbsoluteUrl(url) {
  return /^(https?:\/\/|\/\/)/.test(url) || url.startsWith("/");
}

/**
 * Render markdown to safe HTML
 *
 * @param {string} markdown - Markdown text
 * @param {Object} options - Rendering options
 * @param {boolean} options.stripFrontmatter - Strip YAML frontmatter (default: false)
 * @param {Object} options.repoContext - Repository context for image path resolution
 * @returns {string} - Sanitized HTML
 */
export function renderMarkdown(markdown, options = {}) {
  if (!markdown) return "";

  const { stripFrontmatter = false, repoContext = null } = options;

  try {
    // Strip YAML frontmatter if requested
    let content = stripFrontmatter ? stripYAMLFrontmatter(markdown) : markdown;

    let rawHTML = md.render(content);

    // Resolve relative image paths if repo context provided
    if (repoContext) {
      rawHTML = resolveImagePaths(rawHTML, repoContext);
    }

    return sanitizeHTML(rawHTML);
  } catch (err) {
    console.error("Markdown rendering error:", err);
    return "";
  }
}

/**
 * Render inline markdown (no <p> wrapper)
 *
 * @param {string} markdown - Inline markdown text
 * @returns {string} - Sanitized HTML
 */
export function renderInlineMarkdown(markdown) {
  if (!markdown) return "";

  try {
    const rawHTML = md.renderInline(markdown);
    return sanitizeHTML(rawHTML);
  } catch (err) {
    console.error("Inline markdown rendering error:", err);
    return "";
  }
}

export default md;
