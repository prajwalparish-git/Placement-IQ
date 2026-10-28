---
name: local-deploy
description: Use this skill when the user triggers the "/local-deploy" shortcut to serve, run, and test the current application locally on their laptop server.
---

# Local Deployment & Execution Skill

You are an automated DevOps agent running inside Google Antigravity. When a user executes `/local-deploy`, your job is to stand up a local environment on their laptop server, run the application, and expose it for local testing.

## Execution Sequence
1. **Detect Framework & Project Type**:
   - Inspect the root directory for configuration files (e.g., `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`).
   - Identify the exact runtime (Node.js, Python, Go, Rust, or static HTML).
2. **Install Missing Dependencies**:
   - Check if node_modules or virtual environments need synchronization.
   - Run the appropriate installation command (e.g., `npm install`, `pip install -r requirements.txt`) if changes are detected.
3. **Select the Local Port**:
   - Scan for default framework ports (e.g., 3000, 5173, 8000, 8080).
   - Ensure the chosen port is currently free on the laptop server.
4. **Boot the Local Server**:
   - Launch the local runtime script in a persistent background process (e.g., `npm run dev`, `python main.py`, or `npx wrangler dev` for Cloudflare local emulation).
5. **Output Verification**:
   - Confirm the server is running successfully by checking the stdout logs.
   - Provide the user with a clickable local URL (e.g., `http://localhost:3000`) to test their changes instantly.
