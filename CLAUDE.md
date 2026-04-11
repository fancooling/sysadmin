# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This is a sysadmin dotfiles and utilities repository. It stores configuration files (bash, tmux, screen) and backup scripts meant to be deployed to Linux (WSL2) machines.

## Repository Structure

- `bash/` - Bash configuration files (`.bashrc`, `.bash_aliases`, `.bash_functions`) meant to be symlinked or copied to `~/`
- `immich_backup/` - Python backup script for Immich photo server (Docker Compose based), with encrypted 7z full/incremental backups and rsync to remote
- `.tmux.conf`, `.screenrc` - Terminal multiplexer configs

## Key Conventions

- Secrets (API keys, passwords, tokens) must never appear in tracked files. Bash secrets go in `~/.bash_keys` (sourced by `.bashrc`, not checked in). Immich backup secrets go in a `.env` file (see `immich_backup/example.env`).
- The immich backup script requires Python 3.6+, 7z, rsync, and docker compose.
