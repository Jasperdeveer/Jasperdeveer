# Git Workflow Guide - JSPR Beamer Setup

This document explains the branching strategy and workflow scripts for managing stable and development versions of the application.

## Branch Strategy

We use a two-branch model:

- **`stable`** - Production-ready, tested version
  - Always safe to use
  - Only receives tested features from dev
  - Use this for daily work

- **`dev`** - Development version with new features
  - May contain untested or experimental features
  - Used for testing before merging to stable
  - May be unstable at times

## Scripts Overview

### Daily Use Scripts

#### `./run_stable.sh`
Runs the **stable** version of the application.

```bash
./run_stable.sh
```

**What it does:**
- Switches to the stable branch
- Activates the virtual environment
- Installs dependencies if needed
- Launches the application

**Use when:** You want to use the reliable, tested version.

#### `./run_dev.sh`
Runs the **development** version with latest features.

```bash
./run_dev.sh
```

**What it does:**
- Shows warning about untested features
- Switches to the dev branch
- Activates the virtual environment
- Installs dependencies if needed
- Launches the application

**Use when:** You want to test new features before they're merged to stable.

### Update Scripts

#### `./update_stable.sh`
Updates the stable version from the remote repository.

```bash
./update_stable.sh
```

**What it does:**
- Stashes any local changes
- Switches to stable branch
- Pulls latest stable version from origin
- Restores local changes

**Use when:** You want to get the latest stable release.

#### `./update_dev.sh`
Updates the development version from the remote repository.

```bash
./update_dev.sh
```

**What it does:**
- Stashes any local changes
- Switches to dev branch
- Pulls latest dev version from origin
- Restores local changes

**Use when:** You want to get the latest development features.

### Maintenance Script

#### `./merge_dev_to_stable.sh`
Merges tested features from dev into stable.

```bash
./merge_dev_to_stable.sh
```

**What it does:**
- Shows safety warning
- Asks for confirmation
- Checks for uncommitted changes
- Merges dev into stable
- Provides next steps

**Use when:** You've thoroughly tested features in dev and want to promote them to stable.

**IMPORTANT:** Only use this after extensive testing in dev!

## Common Workflows

### Workflow 1: Normal Daily Use

```bash
# Start the stable version
./run_stable.sh
```

That's it! Just run the stable version for normal use.

### Workflow 2: Testing New Features

```bash
# Switch to and run development version
./run_dev.sh

# Test the new features...
# Report any bugs you find
```

### Workflow 3: Getting Updates

```bash
# Update to latest stable version
./update_stable.sh

# Then run it
./run_stable.sh
```

### Workflow 4: Promoting Features to Stable

This workflow is for when you've tested features in dev and want to make them available in stable:

```bash
# 1. First, test thoroughly in dev
./run_dev.sh
# ... extensive testing ...

# 2. Ensure dev is clean (no uncommitted changes)
git status

# 3. Merge dev to stable
./merge_dev_to_stable.sh
# Type "yes" when prompted

# 4. Test the merged stable version
./run_stable.sh
# ... verify everything works ...

# 5. If everything works, push to remote
git push origin stable

# 6. If there are problems, rollback
git reset --hard HEAD~1
```

## Virtual Environment

All scripts automatically handle the Python virtual environment (`venv`):

- Activates venv before running
- Checks for PyQt5 installation
- Installs dependencies from `requirements.txt` if needed
- Deactivates venv on exit

If you don't have a venv yet:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

## Safety Guidelines

### Before Merging Dev to Stable:

1. Test all new features thoroughly in dev
2. Check for crashes or bugs
3. Verify UI works correctly
4. Test all keyboard shortcuts
5. Check export functionality
6. Ensure no performance regressions

### If Something Goes Wrong:

#### After running a script:
```bash
# Check what branch you're on
git branch

# Switch back to stable if needed
git checkout stable
```

#### After a bad merge:
```bash
# Undo the merge (before pushing!)
git reset --hard HEAD~1

# Or abort during merge conflicts
git merge --abort
```

#### Lost work:
```bash
# View stashed changes
git stash list

# Restore stashed changes
git stash pop
```

## Troubleshooting

### Script won't run:
```bash
# Make scripts executable
chmod +x *.sh
```

### Virtual environment not found:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Dependencies missing:
```bash
# Install dependencies manually
source venv/bin/activate
pip install -r requirements.txt
```

### Can't switch branches:
```bash
# Commit or stash your changes first
git status
git stash  # Or git add . && git commit -m "WIP"
```

### Merge conflicts:
```bash
# Check which files have conflicts
git status

# Edit the conflicting files
# Look for <<<<<<< markers

# After resolving conflicts
git add .
git commit

# Or abort the merge
git merge --abort
```

## Branch History

- **Current version**: Marked as stable (January 2026)
  - Modern responsive UI
  - Resizable panels with draggable splitters
  - Improved button styling and spacing
  - Crash prevention in shortcuts widget
  - Full presentation mode support

- **Development**: New features being tested

## Questions?

If you encounter issues:
1. Check `git status` to see current state
2. Read the error messages carefully
3. Check this document for common solutions
4. Make sure you're on the right branch
5. Verify venv is working: `which python3` (should show venv path)

## Quick Reference

| Task | Command |
|------|---------|
| Run stable version | `./run_stable.sh` |
| Run dev version | `./run_dev.sh` |
| Update stable | `./update_stable.sh` |
| Update dev | `./update_dev.sh` |
| Merge dev → stable | `./merge_dev_to_stable.sh` |
| Check current branch | `git branch` |
| See uncommitted changes | `git status` |
| Switch to stable | `git checkout stable` |
| Switch to dev | `git checkout dev` |
