#!/bin/bash
# Hermes cron entry: daily AI job pipeline (code: ~/code/job-application-skill/career_ops/daily_pipeline.py)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p ~/.hermes/job-pipeline
python3 ~/code/job-application-skill/career_ops/daily_pipeline.py 2>>~/.hermes/job-pipeline/errors.log
