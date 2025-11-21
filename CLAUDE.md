# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python CLI client for ComfyUI that submits image generation workflows to a remote ComfyUI server. It loads JSON workflows, modifies prompts, sends them via HTTP, monitors progress via WebSocket, and downloads generated images.

## Running the Project

```bash
# Activate virtual environment
source venv/bin/activate

# Run image generation
python main.py
```

No build, test, or lint systems are configured.

## Architecture

**main.py** - Single-file application with this flow:
1. `load_workflow()` - Load workflow.json
2. `set_prompt()` - Inject text prompt into specified node
3. `send_prompt_to_comfy()` - POST to `/prompt` endpoint
4. `wait_for_images()` - WebSocket listener for execution status
5. `download_image()` - GET from `/view` endpoint, save with timestamp

**workflow.json** - ComfyUI node graph configuration for Qwen 2.5 VL 7B model with AuraFlow sampling. Node 6 contains the positive prompt, Node 7 the negative prompt.

## Configuration (in main.py)

- `COMFY_HOST` / `COMFY_PORT` - Remote ComfyUI server address
- `PROMPT_NODE_ID` - Workflow node ID to modify (default: "6")
- `WORKFLOW_JSON` - Path to workflow file

To find the correct node ID: open workflow.json, locate the node with `"class_type": "CLIPTextEncode"` containing your prompt text.

## Dependencies

- `requests` - HTTP client
- `websocket-client` - WebSocket for real-time status
