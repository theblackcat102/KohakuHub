#!/usr/bin/env node
/**
 * Prebuild script for KohakuHub frontend
 * Recursively copies documentation files from docs/ to public/documentation/
 * Supports nested directory structure for better organization
 */

const fs = require('fs');
const path = require('path');

// Define paths
const rootDir = path.join(__dirname, '..', '..', '..');
const publicDir = path.join(__dirname, '..', 'public');
const docsPublicDir = path.join(publicDir, 'documentation');
const imagesPublicDir = path.join(publicDir, 'images');
const docsSourceDir = path.join(rootDir, 'docs');

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
 * Copy a single file
 */
function copyFile(source, dest) {
  try {
    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }
    fs.copyFileSync(source, dest);
    console.log(`✓ Copied: ${path.basename(source)} -> ${path.relative(process.cwd(), dest)}`);
  } catch (error) {
    console.error(`✗ Failed to copy ${source}: ${error.message}`);
    process.exit(1);
  }
}

/**
 * Recursively copy directory and generate manifests
 */
function copyDirRecursive(sourceDir, destDir) {
  if (!fs.existsSync(sourceDir)) {
    console.warn(`⚠ Source directory not found: ${sourceDir}`);
    return;
  }

  if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
  }

  const entries = fs.readdirSync(sourceDir, { withFileTypes: true });
  const mdFiles = [];

  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name);
    const destPath = path.join(destDir, entry.name);

    if (entry.isDirectory()) {
      // Recursively copy subdirectory
      copyDirRecursive(sourcePath, destPath);
    } else if (entry.isFile() && entry.name.endsWith('.md') && entry.name !== 'index.md') {
      // Copy markdown file
      copyFile(sourcePath, destPath);
      mdFiles.push(entry.name);
    }
  }

  // Generate .manifest.json for directory listing
  if (mdFiles.length > 0) {
    const manifestPath = path.join(destDir, '.manifest.json');
    fs.writeFileSync(manifestPath, JSON.stringify(mdFiles, null, 2));
    console.log(`  Generated manifest: ${mdFiles.length} files in ${path.basename(destDir)}/`);
  }
}

/**
 * Main function
 */
function main() {
  console.log('📚 Copying documentation and images...\n');

  // Create directories
  if (!fs.existsSync(docsPublicDir)) {
    fs.mkdirSync(docsPublicDir, { recursive: true });
  }
  if (!fs.existsSync(imagesPublicDir)) {
    fs.mkdirSync(imagesPublicDir, { recursive: true });
  }

  // Recursively copy entire docs/ directory
  console.log('Copying docs/ directory recursively...');
  copyDirRecursive(docsSourceDir, docsPublicDir);

  // Copy CONTRIBUTING.md
  const contributingSource = path.join(rootDir, 'CONTRIBUTING.md');
  const contributingDest = path.join(docsPublicDir, 'contributing.md');
  if (fs.existsSync(contributingSource)) {
    copyFile(contributingSource, contributingDest);
  }

  // Copy logo files
  console.log('\nCopying logo files...');
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

  logoFiles.forEach(file => copyFile(file.source, file.dest));

  console.log('\n✅ All files copied successfully!');
}

main();
