<!-- src/pages/privacy.vue -->
<script setup>
import MarkdownPage from "@/components/common/MarkdownPage.vue";

const content = `# Privacy Policy

**Last Updated**: January 2025

## Introduction

Welcome to KohakuHub. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our service.

## Information We Collect

### Personal Information

When you register for an account, we collect:

- **Username**: Your chosen username for identification
- **Email Address**: For account verification and communication
- **Password**: Stored securely using industry-standard encryption
- **Profile Information**: Any additional information you choose to provide

### Repository Data

- **Code and Files**: Content you upload to your repositories
- **Commit History**: Version control information
- **Repository Metadata**: Names, descriptions, tags, and settings

### Usage Information

We automatically collect certain information when you use KohakuHub:

- **Log Data**: IP address, browser type, operating system, pages visited
- **Device Information**: Device identifiers and mobile network information
- **Cookies and Similar Technologies**: To maintain your session and preferences

## How We Use Your Information

We use the collected information for:

### Service Provision

- Creating and managing your account
- Hosting and displaying your repositories
- Providing version control functionality
- Enabling collaboration features

### Service Improvement

- Analyzing usage patterns to improve features
- Debugging and fixing technical issues
- Developing new features and services

### Communication

- Sending important service announcements
- Responding to your inquiries and support requests
- Notifying you of security issues (when necessary)

### Security

- Detecting and preventing fraud and abuse
- Protecting against security threats
- Enforcing our Terms of Service

## Information Sharing and Disclosure

### Public Information

- **Public Repositories**: Content in public repositories is visible to everyone
- **Profile Information**: Your username and public profile details are visible to all users
- **Activity**: Your public contributions and activity may be visible to others

### Private Information

We do not sell, trade, or rent your personal information to third parties. We may share information in these limited circumstances:

- **With Your Consent**: When you explicitly agree to share information
- **Legal Requirements**: When required by law, court order, or legal process
- **Service Providers**: With trusted third parties who help us operate the service (e.g., hosting providers)
- **Security Threats**: To protect rights, property, or safety of KohakuHub, our users, or others

## Data Storage and Security

### Security Measures

We implement appropriate technical and organizational measures to protect your data:

- Encrypted data transmission (HTTPS)
- Secure password storage (hashing and salting)
- Regular security audits and updates
- Access controls and authentication

### Data Retention

- **Active Accounts**: We retain your information as long as your account is active
- **Deleted Accounts**: Account data is removed within 90 days of deletion
- **Repository Data**: Deleted repositories are permanently removed according to our retention policy
- **Legal Obligations**: Some data may be retained longer if required by law

## Your Rights and Choices

### Access and Control

You have the right to:

- **Access**: View the personal information we hold about you
- **Correction**: Update or correct your information
- **Deletion**: Request deletion of your account and data
- **Export**: Download your repository data
- **Privacy Settings**: Control visibility of your repositories and profile

### How to Exercise Your Rights

- Update your profile through account settings
- Manage repository visibility settings
- Contact us for data access or deletion requests
- Use our API to export your data

## Cookies and Tracking

### What We Use

- **Essential Cookies**: Required for authentication and basic functionality
- **Analytics**: To understand how users interact with KohakuHub
- **Preferences**: To remember your settings and preferences

### Your Choices

- You can control cookies through your browser settings
- Disabling cookies may affect service functionality

## Third-Party Links

KohakuHub may contain links to external websites. We are not responsible for the privacy practices of these third-party sites. We encourage you to read their privacy policies.

## Children's Privacy

KohakuHub is not intended for users under 13 years of age. We do not knowingly collect personal information from children under 13. If we discover that a child under 13 has provided us with personal information, we will delete it immediately.

## International Users

KohakuHub is hosted and operated according to the laws of the hosting jurisdiction. By using the service, you consent to the transfer and processing of your information in that jurisdiction.

## Changes to This Privacy Policy

We may update this Privacy Policy from time to time. We will notify you of any material changes by:

- Posting the new Privacy Policy on this page
- Updating the "Last Updated" date
- Sending you an email notification (for significant changes)

Your continued use of KohakuHub after changes constitutes acceptance of the updated policy.

## Data Breach Notification

In the event of a data breach that affects your personal information, we will:

- Notify affected users within 72 hours of discovery
- Provide information about the nature of the breach
- Advise on steps to protect yourself
- Report to relevant authorities as required by law

## Contact Us

If you have questions, concerns, or requests regarding this Privacy Policy or your data, please contact us:

- **GitHub**: [https://github.com/KohakuBlueleaf/Kohaku-Hub](https://github.com/KohakuBlueleaf/Kohaku-Hub)
- **Discord**: [https://discord.gg/xWYrkyvJ2s](https://discord.gg/xWYrkyvJ2s)

## Your Consent

By using KohakuHub, you consent to this Privacy Policy and agree to its terms.

---

**Self-Hosted Instances**: If you are using a self-hosted instance of KohakuHub, this privacy policy may not apply. Please contact your instance administrator for their privacy policy.
`;
</script>

<template>
  <MarkdownPage :content="content" />
</template>
