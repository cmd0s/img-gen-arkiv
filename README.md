# CCats - Endless Cat Image Generator

Automated cat image generator using ComfyUI with blockchain storage on ARKIV network.

## Features

- Generates unique cat images using AI (ComfyUI + Qwen 2.5 VL model)
- 2.3M+ unique prompt combinations (cats × accessories × styles × colors × backgrounds)
- Automatic upload to ARKIV blockchain
- SQLite database for progress tracking and resume capability
- Runs continuously until all combinations are generated

## Prerequisites

- Python 3.11+
- ComfyUI running on a remote machine (Windows/Linux with GPU)
- ARKIV wallet with test funds

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd img-gen-arkiv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --pre -r requirements.txt
```

## Configuration

1. Copy the environment template:
```bash
cp .env.TEMPLATE .env
```

2. Edit `.env` with your ARKIV credentials:
```env
RPC_URL=https://mendoza.hoodi.arkiv.network/rpc
PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
```

3. Edit `main.py` to configure ComfyUI connection:
```python
COMFY_HOST = "192.168.0.122"  # Your ComfyUI machine IP
COMFY_PORT = 8899             # ComfyUI port
```

4. Place your ComfyUI workflow as `workflow.json` and set the correct `PROMPT_NODE_ID`.

## Usage

```bash
# Run the endless generator
python main.py

# Preview possible combinations (without generating)
python prompt_generator.py

# Test ARKIV connection
python arkiv_uploader.py
```

### Controls

- `Ctrl+C` - Stop gracefully (saves progress)
- Resume anytime by running `python main.py` again

## Project Structure

```
img-gen-arkiv/
├── main.py              # Main generator loop
├── prompt_generator.py  # Prompt combinations & SQLite database
├── arkiv_uploader.py    # ARKIV blockchain upload
├── workflow.json        # ComfyUI workflow configuration
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
├── .env.TEMPLATE        # Environment template
├── generations.db       # SQLite progress database (auto-created)
└── output/              # Generated images (auto-created)
```

## How It Works

1. **Prompt Generation**: Combines cat types, accessories, styles, colors, backgrounds, and quality tags into unique prompts
2. **ComfyUI Integration**: Sends workflow via HTTP, monitors via WebSocket
3. **Image Storage**: Saves locally as PNG, uploads to ARKIV if <117KB
4. **Progress Tracking**: SQLite database tracks completed/pending prompts

## ARKIV Annotations

Each uploaded image includes:
- `type`: "image"
- `app`: "CCats"
- `prompt`: Generation prompt text
- `id`: Unique image ID

## Configuration Options

In `main.py`:
```python
DELAY_BETWEEN_GENERATIONS = 2  # Seconds between generations
MAX_IMAGE_SIZE_KB = 117        # Skip ARKIV upload if larger
UPLOAD_TO_ARKIV = True         # Enable/disable blockchain upload
```

## Getting ARKIV Test Funds

1. Generate a wallet at [vanity-eth.tk](https://vanity-eth.tk/)
2. Get test ETH from [Mendoza Faucet](https://mendoza.hoodi.arkiv.network/faucet/)
3. Add private key to `.env`

## Documentation

- [ARKIV Python SDK Tutorial](ARKIV_TUTORIAL.md)
- [ARKIV Network](https://arkiv.network)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)

## License

MIT
