#!/usr/bin/env node
/**
 * Prebuild script for KohakuBoard frontend
 * Copies logo files from root images/ to public/images/
 */

const fs = require('fs');
const path = require('path');

const rootDir = path.join(__dirname, '..', '..', '..');
const publicDir = path.join(__dirname, '..', 'public');
const imagesPublicDir = path.join(publicDir, 'images');

const logoFiles = [
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
  {
    source: path.join(rootDir, 'images', 'logo-square.svg'),
    dest: path.join(publicDir, 'favicon.svg'),
  },
];

function copyFile(source, dest) {
  try {
    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }
    fs.copyFileSync(source, dest);
    console.log(`✓ Copied: ${path.basename(source)}`);
  } catch (error) {
    console.error(`✗ Failed to copy ${source}: ${error.message}`);
    process.exit(1);
  }
}

function main() {
  console.log('📚 Copying logo files for KohakuBoard...\n');

  if (!fs.existsSync(imagesPublicDir)) {
    fs.mkdirSync(imagesPublicDir, { recursive: true });
  }

  logoFiles.forEach(file => copyFile(file.source, file.dest));

  console.log('\n✅ All files copied successfully!');
}

main();
