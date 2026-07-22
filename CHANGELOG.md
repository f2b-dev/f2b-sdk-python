# Changelog

本文件遵循 Keep a Changelog；版本约定见 [f2b-meta RELEASE.md](https://github.com/f2b-dev/f2b-meta/blob/main/RELEASE.md)。  
**1.0 前不发布 PyPI**；请用 `pip install -e .`。

## [Unreleased]

### Added

- `scripts/pack-check.sh`：sdist 审阅（不 upload PyPI）
- CI 起 fake sandbox 跑 `scripts/smoke.py`；healthz 等待失败即退出

## [0.1.0] - 2026-07

- 与 JS SDK 对齐的核心客户端能力（生命周期 / 命令 / 文件等）
