# Changelog

All notable changes to Sakhi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Session memory for Claude (`.claude/MEMORY.md`, `.claude/CURRENT_TASK.md`)
- Quick task shortcuts in CLAUDE.md
- Auto-changelog generation (`make changelog`)
- Pre-commit hooks with black, ruff, typecheck
- Code generators (`make new-route`, `make new-service`)
- Test fixtures and factories
- Feature flags system
- API test client for TypeScript
- Dev status dashboard (`make status`)
- Comprehensive test structure (unit/integration/e2e)

### Changed
- Reorganized test directories under `sakhi/tests/`
- Enhanced Makefile with verification commands
- Improved CLAUDE.md with workflows and shortcuts

### Fixed
- Build verification to catch Vercel/Railway errors before commit

---

## [0.1.0] - 2026-02-01

### Added
- Initial Sakhi MVP
- FastAPI backend with 80+ routes
- Next.js 14 frontend
- Ayurvedic-informed conversation engine
- Memory system (episodic, semantic, graph)
- Friction Framework for user state
- Voice integration (STT/TTS)
- Desktop agent foundation
