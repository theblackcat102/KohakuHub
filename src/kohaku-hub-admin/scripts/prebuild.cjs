#!/usr/bin/env node
/**
 * Prebuild script for KohakuHub Admin Portal
 * Copies logo files from the root images/ directory to public/
 * so they can be used as favicon and branding assets.
 */

const fs = require('fs');
const path = require('path');

// Define paths relative to the script location
const rootDir = path.join(__dirname, '..', '..', '..');
const publicDir = path.join(__dirname, '..', 'public');
const imagesPublicDir = path.join(publicDir, 'images');

// Files to copy
const filesToCopy = [
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
  console.log('🎨 Copying logo files to public directory...\n');

  // Create images directory if it doesn't exist
  if (!fs.existsSync(imagesPublicDir)) {
    fs.mkdirSync(imagesPublicDir, { recursive: true });
  }

  // Copy all files
  filesToCopy.forEach((file) => {
    copyFile(file.source, file.dest);
  });

  console.log('\n✅ Logo files copied successfully!');
}

// Run the script
main();
