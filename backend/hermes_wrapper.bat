@echo off
REM Hermes Wrapper for Windows - Calls WSL Ubuntu Hermes
REM Use C.UTF-8 which is available in minimal WSL installs
wsl -d Ubuntu -e bash -c "export LC_ALL=C.UTF-8 && export LANG=C.UTF-8 && source ~/.hermes/hermes-agent/venv/bin/activate && hermes %*"
