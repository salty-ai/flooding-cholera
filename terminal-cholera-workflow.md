# Flooding-Cholera Terminal Workflow

## Overview
This workflow demonstrates how to use terminal-code and terminal-browser for:
1. Running the cholera surveillance app entirely in terminal
2. Taking screenshots for documentation and sharing
3. Integrating with your Herdr/Claude Code workflow

## Setup
1. Ensure you have a terminal supporting kitty graphics protocol (ghostty, kitty, wezterm)
2. Install terminal-code: `curl -fsSl https://tode.sh/install | bash`
3. Clone the project: `git clone https://github.com/salty-ai/flooding-cholera`

## Workflow Steps

### 1. Launch Backend & Frontend in Terminal Splits
```bash
# Start Herdr pane with Claude Code (your agent)
# In Herdr pane:

# Split terminal and start backend
tode --split down
cd /root/flooding-cholera-sync/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# In original pane (or another split):
tode --split right
cd /root/flooding-cholera-sync/frontend
npm run dev
```

### 2. Access App & Take Screenshots
```bash
# From any pane, launch terminal-browser in app mode
tode --app-mode open http://localhost:5173

# Take screenshot of full app
tode --app-mode screenshot --full

# Take focused screenshot of risk map
tode --app-mode screenshot --crop 100 50 500 400

# Screenshots saved to ~/screenshot-YYYYMMDD-HHMMSS.png
```

### 3. Remote Development via SSH
```bash
# Access remote server running cholera app
tode --ssh user@remote-server --app-mode open http://localhost:5173

# Take screenshot remotely
tode --app-mode screenshot --full
```

### 4. Code Review Workflow
```bash
# In Herdr pane with Claude Code:
# Review PR changes
tode --review  # Opens source control panel

# Edit files in terminal VS Code
tode --app-mode open /root/flooding-cholera-sync/frontend/src/components/Map/
```

## Integration with Herdr
- Run Herdr in left pane
- Use `tode --split right` for code editor
- Use `tode --app-mode` for live app preview
- All in same terminal - zero context switching

## Screenshot Sharing
Screenshots are automatically saved as PNG files you can:
- Share directly via Telegram: `MEDIA:/root/screenshot-*.png`
- Include in documentation
- Send to Yaks for review

## Notes
- Works with any kitty-protocol terminal
- App mode removes browser chrome for clean screenshots
- Combines perfectly with your Claude Code CLI workflow