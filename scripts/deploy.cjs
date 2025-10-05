#!/usr/bin/env node
/**
 * Cross-platform deployment script for KohakuHub
 * Works on both Windows and Linux
 */

const { execSync } = require('child_process');
const path = require('path');

/**
 * Execute a command with proper output handling
 * @param {string} command - Command to execute
 * @param {string} description - Human-readable description
 */
function runCommand(command, description) {
  console.log(`\n📦 ${description}...`);
  console.log(`   Running: ${command}\n`);

  try {
    execSync(command, {
      stdio: 'inherit',
      cwd: path.join(__dirname, '..'),
      shell: true
    });
    console.log(`✅ ${description} - Done\n`);
  } catch (error) {
    console.error(`\n❌ ${description} - Failed`);
    console.error(`   Error: ${error.message}`);
    process.exit(1);
  }
}

/**
 * Main deployment function
 */
function main() {
  console.log('========================================');
  console.log('   KohakuHub Deployment Script');
  console.log('========================================');

  // Step 1: Install frontend dependencies
  runCommand(
    'npm install --prefix ./src/kohaku-hub-ui',
    'Installing frontend dependencies'
  );

  // Step 2: Build frontend (prebuild script will copy docs automatically)
  runCommand(
    'npm run build --prefix ./src/kohaku-hub-ui',
    'Building frontend'
  );

  // Step 3: Start Docker services
  runCommand(
    'docker-compose up -d --build',
    'Starting Docker services'
  );

  console.log('========================================');
  console.log('✅ Deployment Complete!');
  console.log('========================================');
  console.log('\n📍 Access your KohakuHub instance at:');
  console.log('   Web UI:  http://localhost:28080');
  console.log('   API:     http://localhost:48888');
  console.log('   Docs:    http://localhost:48888/docs\n');
}

// Run the deployment
main();
