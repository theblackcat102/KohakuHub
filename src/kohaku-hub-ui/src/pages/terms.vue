<!-- src/pages/terms.vue -->
<script setup>
import MarkdownPage from '@/components/common/MarkdownPage.vue'

const content = `# Terms of Service

**Last Updated**: January 2025

## 1. Acceptance of Terms

By accessing and using KohakuHub ("the Service"), you accept and agree to be bound by the terms and provisions of this agreement.

## 2. Use License

Permission is granted to temporarily download one copy of the materials (information or software) on KohakuHub for personal, non-commercial transitory viewing only.

### This is the grant of a license, not a transfer of title, and under this license you may not:

- Modify or copy the materials
- Use the materials for any commercial purpose or for any public display
- Attempt to reverse engineer any software contained on KohakuHub
- Remove any copyright or other proprietary notations from the materials
- Transfer the materials to another person or "mirror" the materials on any other server

## 3. User Accounts

### 3.1 Account Creation

- You must provide accurate and complete information when creating an account
- You are responsible for maintaining the security of your account and password
- You must notify us immediately of any unauthorized use of your account

### 3.2 Account Responsibilities

- You are responsible for all content and activity that occurs under your account
- You may not use another user's account without permission
- You must be at least 13 years old to use this Service

## 4. Content Guidelines

### 4.1 Your Content

- You retain ownership of content you upload to KohakuHub
- You grant us a license to host, store, and share your content as necessary to provide the Service
- You are responsible for ensuring you have the right to upload and share your content

### 4.2 Prohibited Content

You may not upload content that:

- Violates any laws or regulations
- Infringes on intellectual property rights
- Contains malware, viruses, or malicious code
- Is hateful, threatening, or harassing
- Contains private information of others without consent

## 5. Repository Management

### 5.1 Public Repositories

- Public repositories are visible to everyone
- Anyone can view and download public repository content
- You should not include sensitive information in public repositories

### 5.2 Private Repositories

- Private repositories are only accessible to you and collaborators you invite
- We reserve the right to access private repositories if required by law or to investigate violations

## 6. Intellectual Property

### 6.1 Service Ownership

- KohakuHub and its original content, features, and functionality are owned by the project maintainers
- The Service is protected by copyright, trademark, and other laws

### 6.2 User Content

- You retain all rights to your original content
- By uploading content, you grant other users the licenses specified in your repository (e.g., MIT, GPL, Apache)

## 7. Termination

We may terminate or suspend your account and access to the Service immediately, without prior notice or liability, for any reason, including:

- Violation of these Terms
- Fraudulent or illegal activity
- At your request
- Extended period of inactivity

## 8. Limitation of Liability

In no event shall KohakuHub, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential, or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses.

## 9. Disclaimer

Your use of the Service is at your sole risk. The Service is provided on an "AS IS" and "AS AVAILABLE" basis without any warranty or condition, express, implied, or statutory.

## 10. Governing Law

These Terms shall be governed by and construed in accordance with the laws of your jurisdiction, without regard to its conflict of law provisions.

## 11. Changes to Terms

We reserve the right to modify or replace these Terms at any time. If a revision is material, we will provide at least 30 days' notice prior to any new terms taking effect.

## 12. Contact Us

If you have any questions about these Terms, please contact us:

- GitHub: [https://github.com/KohakuBlueleaf/Kohaku-Hub](https://github.com/KohakuBlueleaf/Kohaku-Hub)
- Discord: [https://discord.gg/xWYrkyvJ2s](https://discord.gg/xWYrkyvJ2s)

---

By using KohakuHub, you acknowledge that you have read, understood, and agree to be bound by these Terms of Service.
`
</script>

<template>
  <MarkdownPage :content="content" />
</template>