---
name: end-cloudflare-deployment
description: Use this skill when the user triggers the "/end-cloudflare-deployment" shortcut to tear down, delete, or suspend the deployment on Cloudflare.
---

# End Cloudflare Deployment Skill

You are an automated DevOps agent running inside Google Antigravity. When a user executes `/end-cloudflare-deployment`, your job is to remove or suspend the live application deployment on Cloudflare from the laptop CLI.

## Execution Sequence
1. **Confirm Project Context**: 
   - Read `wrangler.toml` or `wrangler.jsonc` to fetch the specific Worker or Pages project name.
2. **Execute Teardown Command**:
   - **For Workers**: Execute `npx wrangler delete` to entirely remove the script and route from the Cloudflare network.
   - **For Pages**: Instruct the user or use the Cloudflare API/CLI commands to delete the project or take the current live deployment down.
3. **Clean Up Local Artifacts**: 
   - Clear out the local `.wrangler` cache or temporary build directories if requested.
4. **Status Report**: 
   - Confirm to the user that the production URL has been disabled and the project deployment has ended.
