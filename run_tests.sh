#!/bin/bash
export PYTHONPATH=$(pwd)
xvfb-run -a python -m pytest tests/scenarios/test_meeting_mode_blacklist.py
