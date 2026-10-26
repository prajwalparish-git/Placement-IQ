@echo off
rem Double-click launcher for tunnel.ps1: the app on a temporary public URL for a demo.
title PlacementIQ - public demo tunnel
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tunnel.ps1" %*
pause
