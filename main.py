import json
import uuid
import time
import os
import threading
import queue
from dataclasses import dataclass
import requests
from websocket import create_connection
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from prompt_generator import (
    seed_database,
    get_next_prompt,
    mark_in_progress,
    mark_completed,
    mark_failed,
    mark_generated,
    get_stats,
    reset_in_progress,
    reset_interrupted,
    get_next_generated,
    get_theme,
    get_output_prefix,
    get_app_name,
)
from arkiv_uploader import upload_image_to_arkiv

# ComfyUI configuration (from .env)
COMFY_HOST = os.getenv("COMFY_HOST", "192.168.0.122")
COMFY_PORT = int(os.getenv("COMFY_PORT", "8899"))

BASE_URL = f"http://{COMFY_HOST}:{COMFY_PORT}"
WS_URL = f"ws://{COMFY_HOST}:{COMFY_PORT}/ws"

# Workflow file name located next to this script
WORKFLOW_JSON = "workflow.json"

# Node ID that has the "text" field with the prompt
# How to find it:
# - open workflow.json in a text editor
# - find your example prompt
# - the dictionary key above that fragment is the node ID, e.g. "7"
PROMPT_NODE_ID = "6"

# Delay between generations (seconds)
DELAY_BETWEEN_GENERATIONS = 2

# ARKIV settings
MAX_IMAGE_SIZE_KB = 117
UPLOAD_TO_ARKIV = True

# Threading settings
UPLOAD_QUEUE_SIZE = 5  # Max items in upload queue (backpressure)


# =============================================================================
# THREADING INFRASTRUCTURE
# =============================================================================

@dataclass
class GeneratedImage:
    """Data passed between generator and uploader threads."""
    prompt_id: int
    prompt_text: str
    image_path: str
    image_id: int


# Thread-safe queue for communication between threads
upload_queue: queue.Queue = queue.Queue(maxsize=UPLOAD_QUEUE_SIZE)

# Shutdown signal for graceful termination
shutdown_event = threading.Event()


# =============================================================================
# COMFYUI FUNCTIONS
# =============================================================================

def load_workflow() -> dict:
    with open(WORKFLOW_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def set_prompt(workflow: dict, node_id: str, prompt: str) -> dict:
    # Deep copy to avoid modifying the original
    wf = json.loads(json.dumps(workflow))
    if node_id not in wf:
        raise KeyError(f"Node with id {node_id} not found in workflow.json")

    if "inputs" not in wf[node_id] or "text" not in wf[node_id]["inputs"]:
        raise KeyError(f"Node {node_id} does not have inputs.text field")

    wf[node_id]["inputs"]["text"] = prompt
    return wf


def send_prompt_to_comfy(workflow: dict, client_id: str):
    payload = {
        "prompt": workflow,
        "client_id": client_id,
    }

    resp = requests.post(f"{BASE_URL}/prompt", json=payload)
    resp.raise_for_status()
    data = resp.json()
    prompt_id = data.get("prompt_id")

    if not prompt_id:
        raise RuntimeError(f"No prompt_id in ComfyUI response: {data}")

    print("Prompt sent to ComfyUI, prompt_id:", prompt_id)
    return prompt_id


def wait_for_images(ws, prompt_id: str, timeout: int = 300):
    """Wait for generation to complete and collect image info."""

    images = []
    start = time.time()

    while True:
        if time.time() - start > timeout:
            raise TimeoutError("Timeout waiting for images")

        msg = ws.recv()
        if not msg:
            continue

        data = json.loads(msg)

        msg_type = data.get("type")
        msg_data = data.get("data", {})

        # Look for executed nodes
        if msg_type == "executed":
            if msg_data.get("prompt_id") != prompt_id:
                continue

            output = msg_data.get("output", {})
            if "images" in output:
                for img in output["images"]:
                    images.append(img)

        # End of workflow execution signal
        if msg_type in ("execution_success", "execution_complete"):
            if msg_data.get("prompt_id") == prompt_id:
                print("ComfyUI finished generating for this prompt.")
                break

    if not images:
        raise RuntimeError("ComfyUI did not return any images")

    return images


def download_image(image_info: dict, out_path: str):
    params = {
        "filename": image_info["filename"],
        "subfolder": image_info.get("subfolder", ""),
        "type": image_info.get("type", "output"),
    }

    resp = requests.get(f"{BASE_URL}/view", params=params, stream=True)
    resp.raise_for_status()

    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print("Image saved:", out_path)


def upload_to_arkiv(image_path: str, prompt: str, image_id: int) -> dict:
    """Upload image to ARKIV blockchain."""

    print(f"Uploading to ARKIV: {image_path}")

    # Read image data
    with open(image_path, "rb") as f:
        image_data = f.read()

    # Determine content type
    ext = os.path.splitext(image_path)[1].lower()
    content_type = "image/png" if ext == ".png" else "image/jpeg"

    size_kb = len(image_data) / 1024
    app_name = get_app_name()
    print(f"Image size: {size_kb:.2f}KB, Content-Type: {content_type}, App: {app_name}")

    # Upload to ARKIV
    result = upload_image_to_arkiv(image_data, prompt, image_id, content_type, app_name)

    print(f"ARKIV upload success! Entity: {result.get('entityKey')}")
    return result


def generate_image_only(prompt_text: str, image_id: int) -> str:
    """Generate image using ComfyUI (GPU work only, no upload).

    Used by threaded mode - upload is handled by separate uploader thread.
    """
    # 1. Load workflow
    workflow = load_workflow()

    # 2. Replace prompt
    workflow = set_prompt(workflow, PROMPT_NODE_ID, prompt_text)

    # 3. Generate client_id and connect WebSocket BEFORE sending prompt
    client_id = str(uuid.uuid4())
    ws_url_with_client = f"{WS_URL}?clientId={client_id}"
    print(f"Connecting to WebSocket: {ws_url_with_client}")
    ws = create_connection(ws_url_with_client)

    try:
        # 4. Send workflow to ComfyUI
        prompt_id = send_prompt_to_comfy(workflow, client_id)

        # 5. Wait for images via WebSocket
        images = wait_for_images(ws, prompt_id)
    finally:
        ws.close()

    # 6. Download first image and save as PNG
    os.makedirs("output", exist_ok=True)
    img_info = images[0]
    prefix = get_output_prefix()
    out_path = f"output/{prefix}_{image_id}.png"
    download_image(img_info, out_path)

    return out_path


def generate_image(prompt_text: str, image_id: int) -> str:
    """Generate image and upload to ARKIV (legacy single-threaded mode)."""
    # Generate the image
    out_path = generate_image_only(prompt_text, image_id)

    # Upload to ARKIV if enabled
    if UPLOAD_TO_ARKIV:
        # Check image size
        image_size_kb = os.path.getsize(out_path) / 1024

        if image_size_kb > MAX_IMAGE_SIZE_KB:
            print(f"Image too large for ARKIV ({image_size_kb:.2f}KB > {MAX_IMAGE_SIZE_KB}KB), skipping upload")
        else:
            # Upload to ARKIV
            try:
                upload_to_arkiv(out_path, prompt_text, image_id)
            except Exception as e:
                print(f"ARKIV upload failed (continuing anyway): {e}")

    return out_path


# =============================================================================
# THREADED MODE FUNCTIONS
# =============================================================================

def generator_thread():
    """Thread 1: Continuously generates images (GPU work).

    Picks pending prompts, generates images, marks as 'generated',
    and queues them for upload.
    """
    thread_name = threading.current_thread().name
    print(f"[{thread_name}] Started")

    while not shutdown_event.is_set():
        # Get next pending prompt
        item = get_next_prompt()

        if not item:
            # No more prompts - signal done and exit
            print(f"[{thread_name}] No more prompts to generate")
            break

        prompt_id = item["id"]
        prompt_text = item["prompt"]
        image_id = prompt_id

        stats = get_stats()
        print(f"\n[{thread_name}] [{stats['completed'] + stats['generated'] + 1}/{stats['total']}] Generating...")
        print(f"[{thread_name}] Prompt: {prompt_text[:70]}...")

        # Mark as in progress
        mark_in_progress(prompt_id)

        try:
            # Generate image (GPU work only)
            output_path = generate_image_only(prompt_text, image_id)

            # Mark as generated in DB
            mark_generated(prompt_id, output_path)

            # Queue for upload (blocks if queue is full - backpressure)
            if UPLOAD_TO_ARKIV:
                upload_queue.put(GeneratedImage(
                    prompt_id=prompt_id,
                    prompt_text=prompt_text,
                    image_path=output_path,
                    image_id=image_id
                ))
                print(f"[{thread_name}] Queued for upload: {output_path}")
            else:
                # No upload - mark as completed directly
                mark_completed(prompt_id, output_path)
                print(f"[{thread_name}] SUCCESS (no upload): {output_path}")

        except Exception as e:
            print(f"[{thread_name}] FAILED: {e}")
            mark_failed(prompt_id)
            # Continue with next prompt

    print(f"[{thread_name}] Finished")


def uploader_thread():
    """Thread 2: Uploads images to ARKIV (network I/O).

    Takes generated images from queue and uploads them to ARKIV blockchain.
    """
    thread_name = threading.current_thread().name
    print(f"[{thread_name}] Started")

    while not shutdown_event.is_set() or not upload_queue.empty():
        try:
            # Get next item with timeout (to check shutdown_event periodically)
            item = upload_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        try:
            # Check image size
            image_size_kb = os.path.getsize(item.image_path) / 1024

            if image_size_kb > MAX_IMAGE_SIZE_KB:
                print(f"[{thread_name}] Image too large ({image_size_kb:.2f}KB > {MAX_IMAGE_SIZE_KB}KB), skipping upload")
                mark_completed(item.prompt_id, item.image_path)
            else:
                # Upload to ARKIV
                print(f"[{thread_name}] Uploading: {item.image_path}")
                upload_to_arkiv(item.image_path, item.prompt_text, item.image_id)
                mark_completed(item.prompt_id, item.image_path)
                print(f"[{thread_name}] SUCCESS: {item.image_path}")

        except Exception as e:
            print(f"[{thread_name}] Upload FAILED: {e}")
            # Mark back to generated for retry on next run
            mark_generated(item.prompt_id, item.image_path)

        finally:
            upload_queue.task_done()

    print(f"[{thread_name}] Finished")


def run_threaded_generator():
    """Run image generation with two threads (optimized mode).

    - Generator thread: GPU work (generate images)
    - Uploader thread: Network I/O (upload to ARKIV)

    GPU doesn't wait for uploads, maximizing utilization.
    """
    global shutdown_event

    theme = get_theme()
    print("=" * 60)
    print(f"THREADED {theme['name'].upper()} IMAGE GENERATOR")
    print("=" * 60)

    # Initialize and seed database if needed
    seed_database(shuffle=True)

    # Reset interrupted items (crash recovery)
    reset_interrupted()

    stats = get_stats()
    print(f"\nStarting from: {stats['completed']}/{stats['total']} completed ({stats['progress_percent']:.1f}%)")
    if stats['generated'] > 0:
        print(f"Images waiting for upload: {stats['generated']}")
    print(f"ARKIV upload: {'ENABLED' if UPLOAD_TO_ARKIV else 'DISABLED'}")
    print(f"Mode: THREADED (generator + uploader)")
    print("-" * 60)

    # Reset shutdown event in case of restart
    shutdown_event.clear()

    # Start threads
    gen_thread = threading.Thread(target=generator_thread, name="Generator")
    upl_thread = threading.Thread(target=uploader_thread, name="Uploader")

    gen_thread.start()
    if UPLOAD_TO_ARKIV:
        upl_thread.start()

    try:
        # Wait for generator to finish
        gen_thread.join()

        # Wait for all uploads to complete
        if UPLOAD_TO_ARKIV:
            print("\n[Main] Generator finished, waiting for uploads to complete...")
            upload_queue.join()

        # Signal uploader to stop
        shutdown_event.set()

        if UPLOAD_TO_ARKIV:
            upl_thread.join(timeout=10)

    except KeyboardInterrupt:
        print("\n\n[Main] Interrupted by user, shutting down gracefully...")
        shutdown_event.set()

        # Wait for threads to finish current work
        gen_thread.join(timeout=5)
        if UPLOAD_TO_ARKIV:
            upl_thread.join(timeout=10)

        print("[Main] Threads stopped")

    # Final stats
    stats = get_stats()
    print("\n" + "=" * 60)
    print("FINAL STATS")
    print("=" * 60)
    print(f"Completed: {stats['completed']}/{stats['total']} ({stats['progress_percent']:.1f}%)")
    if stats['generated'] > 0:
        print(f"Generated (pending upload): {stats['generated']}")
    if stats['pending'] > 0:
        print(f"Pending: {stats['pending']}")


def run_endless_generator():
    """Run endless image generation from database."""
    theme = get_theme()
    print("=" * 60)
    print(f"ENDLESS {theme['name'].upper()} IMAGE GENERATOR")
    print("=" * 60)

    # Initialize and seed database if needed
    seed_database(shuffle=True)

    # Reset any interrupted generations
    reset_in_progress()

    stats = get_stats()
    print(f"\nStarting from: {stats['completed']}/{stats['total']} completed ({stats['progress_percent']:.1f}%)")
    print(f"ARKIV upload: {'ENABLED' if UPLOAD_TO_ARKIV else 'DISABLED'}")
    print("-" * 60)

    generation_count = 0

    while True:
        # Get next prompt
        item = get_next_prompt()

        if not item:
            print("\n" + "=" * 60)
            print("ALL DONE! No more prompts to generate.")
            print("=" * 60)
            break

        prompt_id = item["id"]
        prompt_text = item["prompt"]
        image_id = prompt_id

        generation_count += 1
        stats = get_stats()

        print(f"\n[{stats['completed'] + 1}/{stats['total']}] Generating...")
        print(f"Prompt: {prompt_text[:80]}...")

        # Mark as in progress
        mark_in_progress(prompt_id)

        try:
            # Generate the image
            output_path = generate_image(prompt_text, image_id)

            # Mark as completed
            mark_completed(prompt_id, output_path)

            print(f"SUCCESS: {output_path}")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Marking current item as pending...")
            mark_failed(prompt_id)
            stats = get_stats()
            print(f"Progress saved: {stats['completed']}/{stats['total']} completed")
            break

        except Exception as e:
            print(f"FAILED: {e}")
            mark_failed(prompt_id)
            # Continue with next prompt

        # Small delay between generations
        if DELAY_BETWEEN_GENERATIONS > 0:
            time.sleep(DELAY_BETWEEN_GENERATIONS)

    # Final stats
    stats = get_stats()
    print(f"\nFinal stats: {stats['completed']}/{stats['total']} completed ({stats['progress_percent']:.1f}%)")


if __name__ == "__main__":
    import sys

    if "--legacy" in sys.argv:
        # Legacy single-threaded mode
        print("Running in LEGACY (single-threaded) mode...")
        run_endless_generator()
    else:
        # Default: optimized threaded mode
        run_threaded_generator()
