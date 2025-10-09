#!/usr/bin/env node
/**
 * Prebuild script for KohakuHub frontend
 * Copies documentation files from the root docs/ directory to public/
 * so they can be served by the frontend application.
 */

const fs = require('fs');
const path = require('path');

// Define paths relative to the script location
const rootDir = path.join(__dirname, '..', '..', '..');
const publicDir = path.join(__dirname, '..', 'public');
const docsPublicDir = path.join(publicDir, 'documentation');
const imagesPublicDir = path.join(publicDir, 'images');

// Documentation files to copy
const filesToCopy = [
  {
    source: path.join(rootDir, 'docs', 'API.md'),
    dest: path.join(docsPublicDir, 'API.md'),
  },
  {
    source: path.join(rootDir, 'docs', 'CLI.md'),
    dest: path.join(docsPublicDir, 'CLI.md'),
  },
  {
    source: path.join(rootDir, 'docs', 'Git.md'),
    dest: path.join(docsPublicDir, 'Git.md'),
  },
  {
    source: path.join(rootDir, 'docs', 'Admin.md'),
    dest: path.join(docsPublicDir, 'Admin.md'),
  },
  {
    source: path.join(rootDir, 'docs', 'setup.md'),
    dest: path.join(docsPublicDir, 'setup.md'),
  },
  {
    source: path.join(rootDir, 'docs', 'deployment.md'),
    dest: path.join(docsPublicDir, 'deployment.md'),
  },
  {
    source: path.join(rootDir, 'docs', 'ports.md'),
    dest: path.join(docsPublicDir, 'ports.md'),
  },
  {
    source: path.join(rootDir, 'CONTRIBUTING.md'),
    dest: path.join(docsPublicDir, 'contributing.md'),
  },
  // Logo files
  {
    source: path.join(rootDir, 'images', 'logo-square.svg'),
    dest: path.join(imagesPublicDir, 'logo-square.svg'),
  },
  {
    source: path.join(rootDir, 'images', 'logo-banner.svg'),
    dest: path.join(imagesPublicDir, 'logo-banner.svg'),
  },
  {
    source: path.join(rootDir, 'images', 'logo-banner-dark.svg'),
    dest: path.join(imagesPublicDir, 'logo-banner-dark.svg'),
  },
  // Favicon (copy square logo as favicon)
  {
    source: path.join(rootDir, 'images', 'logo-square.svg'),
    dest: path.join(publicDir, 'favicon.svg'),
  },
];

/**
 * Copy a single file with error handling
 * @param {string} source - Source file path
 * @param {string} dest - Destination file path
 */
function copyFile(source, dest) {
  try {
    // Ensure destination directory exists
    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }

    // Copy file
    fs.copyFileSync(source, dest);
    console.log(`✓ Copied: ${path.basename(source)} -> ${path.relative(process.cwd(), dest)}`);
  } catch (error) {
    console.error(`✗ Failed to copy ${source}: ${error.message}`);
    process.exit(1);
  }
}

/**
 * Main function
 */
function main() {
  console.log('📚 Copying documentation files and logos to public directory...\n');

  // Create directories if they don't exist
  if (!fs.existsSync(docsPublicDir)) {
    fs.mkdirSync(docsPublicDir, { recursive: true });
  }
  if (!fs.existsSync(imagesPublicDir)) {
    fs.mkdirSync(imagesPublicDir, { recursive: true });
  }

  // Copy all files
  filesToCopy.forEach((file) => {
    copyFile(file.source, file.dest);
  });

  console.log('\n✅ Documentation files and logos copied successfully!');
}

// Run the script
main();
