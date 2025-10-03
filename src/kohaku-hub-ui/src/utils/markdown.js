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
      'input',
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
 * Render markdown to safe HTML
 * 
 * @param {string} markdown - Markdown text
 * @returns {string} - Sanitized HTML
 */
export function renderMarkdown(markdown) {
  if (!markdown) return ''
  
  try {
    const rawHTML = md.render(markdown)
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