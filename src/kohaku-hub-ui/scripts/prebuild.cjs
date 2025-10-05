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
const docsPublicDir = path.join(publicDir, 'docs');

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
    source: path.join(rootDir, 'docs', 'TODO.md'),
    dest: path.join(docsPublicDir, 'TODO.md'),
  },
  {
    source: path.join(rootDir, 'CONTRIBUTING.md'),
    dest: path.join(publicDir, 'CONTRIBUTING.md'),
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
  console.log('📚 Copying documentation files to public directory...\n');

  // Create docs directory if it doesn't exist
  if (!fs.existsSync(docsPublicDir)) {
    fs.mkdirSync(docsPublicDir, { recursive: true });
  }

  // Copy all files
  filesToCopy.forEach((file) => {
    copyFile(file.source, file.dest);
  });

  console.log('\n✅ Documentation files copied successfully!');
}

// Run the script
main();
