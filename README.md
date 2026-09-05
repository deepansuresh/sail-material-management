# SAIL Material Management Module - Salem Steel Plant

Web-based Purchase Proposal Note extraction and generation system for Steel Authority of India Limited (SAIL) - Salem Steel Plant.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/deepansuresh/sail-material-management)

## Overview
This application accepts purchase requisition / indent PDFs (including scanned and digital documents), performs dynamic multi-pass text and OCR extraction, and formats the output strictly into the approved 3-page SAIL Purchase Proposal Note template with 8 tables, 9 narrative clauses, commercial terms, and approval pathways.

## Cloud Deployment
Deploy to Render, Railway, or any Docker-compatible PaaS:
- **Dockerfile**: Full support for Debian/Ubuntu with `tesseract-ocr` and Python 3.11.
- **Render Blueprint**: Configured via `render.yaml` for automatic 1-click deployment.

## Features
- 100% template preservation matching SAIL official specifications.
- Dynamic data extraction with zero hardcoding.
- Word document (.docx) generation matching official layout.
- Fast, clean, responsive web interface.
