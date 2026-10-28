---
name: cloudflare-laptop-deploy
description: Use this skill when asked to deploy the current project from the local laptop environment to Cloudflare (Workers or Pages) using Wrangler.
---

# Cloudflare Laptop Deployment Skill

You are an automated DevOps agent running inside Google Antigravity. Your job is to deploy the current local project to Cloudflare using the laptop as the build and deployment server.

## Prerequisites Check
1. Verify that `wrangler` is installed locally (`npx wrangler --version` or `wrangler --version`). If missing, instruct or install it.
2. Verify that the user is authenticated with Cloudflare (`wrangler whoami`). If not logged in, instruct the user to run `npx wrangler login`.
3. Inspect `package.json`, `wrangler.toml`, or project structure to determine if the target is:
   - **Cloudflare Workers** (serverless script/API)
   - **Cloudflare Pages** (static site or SSR framework build)

## Deployment Steps
1. **Build the Project**: Run the local build command if required (e.g., `npm run build`, `vite build`, or skip if pure HTML/JS).
2. **Configure Wrangler**: Check or generate a valid `wrangler.toml` or `wrangler.jsonc` in the root directory with appropriate compatibility flags, entrypoints, and bindings (KV, D1, R2 if needed).
3. **Deploy from Laptop**:
   - For Workers: Execute `npx wrangler deploy`
   - For Pages: Execute `npx wrangler pages deploy <BUILD_OUTPUT_DIR>`
4. **Output Verification**: Capture the live production URL returned by Wrangler and present it clearly to the user.
