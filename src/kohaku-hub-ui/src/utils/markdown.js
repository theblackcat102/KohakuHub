// src/kohaku-hub-ui/src/utils/markdown.js
import MarkdownIt from 'markdown-it'
import DOMPurify from 'isomorphic-dompurify'

/**
 * Create markdown renderer with XSS protection
 * Using blacklist approach to allow HTML+CSS galleries
 */
const md = new MarkdownIt({
  html: true, // Enable HTML tags in source
  linkify: true, // Auto-convert URLs to links
  typographer: true, // Enable smart quotes and other typographic replacements
  breaks: true // Convert \n to <br>
})

/**
 * Sanitize HTML with blacklist approach
 * Allows most HTML/CSS but removes dangerous elements
 * 
 * @param {string} html - Raw HTML to sanitize
 * @returns {string} - Sanitized HTML
 */
export function sanitizeHTML(html) {
  if (!html) return ''
  
  return DOMPurify.sanitize(html, {
    // Blacklist dangerous tags
    // Note: We allow 'input' for radio-based image galleries
    FORBID_TAGS: [
      'script',
      'iframe',
      'object',
      'embed',
      'applet',
      'meta',
      'link',
      'base',
      'form',
      'button',
      'textarea',
      'select'
    ],
    
    // Blacklist dangerous attributes
    FORBID_ATTR: [
      'onerror',
      'onload',
      'onclick',
      'onmouseover',
      'onfocus',
      'onblur',
      'onchange',
      'onsubmit'
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
      mathMl: false
    }
  })
}

/**
 * Strip YAML frontmatter from markdown content
 * HuggingFace repo cards use YAML frontmatter for metadata
 *
 * @param {string} markdown - Markdown text with potential YAML frontmatter
 * @returns {string} - Markdown without frontmatter
 */
export function stripYAMLFrontmatter(markdown) {
  if (!markdown) return ''

  // Match YAML frontmatter: starts with ---, ends with ---
  const frontmatterRegex = /^---\s*\n([\s\S]*?\n)?---\s*\n/
  return markdown.replace(frontmatterRegex, '')
}

/**
 * Render markdown to safe HTML
 *
 * @param {string} markdown - Markdown text
 * @param {Object} options - Rendering options
 * @param {boolean} options.stripFrontmatter - Strip YAML frontmatter (default: false)
 * @returns {string} - Sanitized HTML
 */
export function renderMarkdown(markdown, options = {}) {
  if (!markdown) return ''

  const { stripFrontmatter = false } = options

  try {
    // Strip YAML frontmatter if requested
    let content = stripFrontmatter ? stripYAMLFrontmatter(markdown) : markdown

    const rawHTML = md.render(content)
    return sanitizeHTML(rawHTML)
  } catch (err) {
    console.error('Markdown rendering error:', err)
    return ''
  }
}

/**
 * Render inline markdown (no <p> wrapper)
 * 
 * @param {string} markdown - Inline markdown text
 * @returns {string} - Sanitized HTML
 */
export function renderInlineMarkdown(markdown) {
  if (!markdown) return ''
  
  try {
    const rawHTML = md.renderInline(markdown)
    return sanitizeHTML(rawHTML)
  } catch (err) {
    console.error('Inline markdown rendering error:', err)
    return ''
  }
}

export default md