---
name: end-local-deployment
description: Use this skill when the user triggers the "/end-local-deployment" shortcut to stop the local development server and free up the network ports.
---

# End Local Deployment Skill

You are an automated DevOps agent running inside Google Antigravity. When a user executes `/end-local-deployment`, your job is to safely terminate the active local server running on the laptop.

## Execution Sequence
1. **Identify the Active Process**: 
   - Search for the background process or PID associated with the local runtime launched by the `/local-deploy` command (e.g., node, python, vite, wrangler dev).
2. **Kill the Process**: 
   - Send a graceful termination signal (`SIGINT` or `Ctrl+C` equivalent) to the process. 
   - If it refuses to close, force kill it (`SIGKILL`) to prevent orphaned zombie processes.
3. **Verify Port Liberation**: 
   - Check the target port (e.g., 3000, 5173, 8000) to confirm it is fully freed up and available for future use.
4. **Status Report**: 
   - Inform the user that the local server has been shut down successfully.
