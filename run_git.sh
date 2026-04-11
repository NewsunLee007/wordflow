#!/bin/bash
# Remove the old commit entirely by resetting to root or just creating a new orphan branch
git checkout --orphan temp_branch
git add -A
git commit -m "Clean initial commit"
git branch -M main
git push -u origin main --force
