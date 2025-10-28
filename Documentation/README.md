# Documentation Index

Complete documentation for the Treemap Visualization multi-format data source system.

## 🚀 Getting Started

Start here if you're new to the project:

- **[../README.md](../README.md)** - Project overview and main documentation
- **[../QUICKSTART.md](../QUICKSTART.md)** - Quick start guide for local development

---

## 📚 Multi-Format System

Documentation for the multi-format data source support:

### Core Guides

- **[MULTI_FORMAT_GUIDE.md](MULTI_FORMAT_GUIDE.md)** - Complete guide to using the multi-format system
  - Supported formats (Intercom MRT, Survey Multi-Ref)
  - How to upload different formats
  - Adding new formats
  - API usage

- **[FORMAT_COMPARISON.md](FORMAT_COMPARISON.md)** - Side-by-side comparison of data formats
  - MRT vs Wattbike structure
  - Transformation examples
  - Impact on visualization

### Technical Documentation

- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Complete technical summary
  - Architecture overview
  - File changes
  - Before/after comparisons
  - Performance considerations

### Testing & Deployment

- **[QUICK_TEST_GUIDE.md](QUICK_TEST_GUIDE.md)** - Quick local testing instructions
  - Manual step-by-step testing
  - Common issues and solutions
  - Success criteria

- **[TEST_CHECKLIST.md](TEST_CHECKLIST.md)** - Comprehensive testing checklist
  - Backend unit tests
  - API tests
  - Frontend tests
  - Performance tests
  - Error handling tests

---

## 🚢 Deployment

Guides for deploying to production:

- **[RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)** - Railway deployment guide
- **[DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)** - Pre-deployment checklist
- **[DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md)** - Post-deployment verification
- **[DEBUG_RAILWAY.md](DEBUG_RAILWAY.md)** - Debugging Railway deployments

---

## 📖 Historical Documentation

- **[PHASE1_COMPLETE.md](PHASE1_COMPLETE.md)** - Phase 1 completion summary

---

## 🔍 Quick Reference

### What should I read first?

**Just want to use the system?**
→ Start with [MULTI_FORMAT_GUIDE.md](MULTI_FORMAT_GUIDE.md)

**Want to understand the differences between formats?**
→ Read [FORMAT_COMPARISON.md](FORMAT_COMPARISON.md)

**Need to test locally?**
→ Follow [QUICK_TEST_GUIDE.md](QUICK_TEST_GUIDE.md)

**Deploying to production?**
→ Use [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)

**Want technical details?**
→ See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)

**Running comprehensive tests?**
→ Follow [TEST_CHECKLIST.md](TEST_CHECKLIST.md)

---

## 📂 Project Structure

```
treemap/
├── README.md                    # Main project README
├── QUICKSTART.md               # Quick start guide
├── Documentation/              # All documentation (you are here)
│   ├── README.md              # This file
│   ├── MULTI_FORMAT_GUIDE.md  # Multi-format usage guide
│   ├── FORMAT_COMPARISON.md   # Format comparison
│   ├── REFACTORING_SUMMARY.md # Technical summary
│   ├── QUICK_TEST_GUIDE.md    # Testing guide
│   ├── TEST_CHECKLIST.md      # Test checklist
│   ├── RAILWAY_DEPLOY.md      # Deployment guides
│   └── ...                    # Other docs
├── backend/                    # Backend API
│   ├── app/
│   │   ├── transformers/      # Format transformers
│   │   ├── models/            # Database models
│   │   └── ...
│   └── migrate_data_sources.py # Migration script
├── index.html                  # Frontend visualization
└── test_wattbike_local.sh     # Automated test script
```

---

## 🤝 Contributing

When adding new documentation:
1. Place it in the `Documentation/` folder
2. Update this README with a link
3. Use clear, descriptive filenames
4. Include examples where helpful

---

## 📝 Documentation Standards

All documentation should:
- Use clear, concise language
- Include code examples where relevant
- Provide both quick start and detailed sections
- Include troubleshooting sections
- Be kept up-to-date with code changes

---

## 🔗 External Resources

- [D3.js Documentation](https://d3js.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

Last updated: October 28, 2025

