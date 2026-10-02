from huggingface_hub import snapshot_download
from engine import SPEECH, EDITOR

if __name__ == "__main__":
    print("Downloading speech model (Whisper base). Videos are never uploaded.", flush=True)
    snapshot_download("Systran/faster-whisper-base", local_dir=str(SPEECH),
                      allow_patterns=["*.json", "*.bin", "*.txt"])
    print("Downloading local editor (Qwen3 1.7B, 4-bit).", flush=True)
    snapshot_download("mlx-community/Qwen3-1.7B-4bit", local_dir=str(EDITOR),
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja"])
    (EDITOR / ".ready").write_text("Download complete\n")
    print("Downloading the local sports vision model.", flush=True)
    from vision_sports import VISION
    snapshot_download("mlx-community/Qwen3-VL-2B-Instruct-4bit", local_dir=str(VISION),
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja", "README.md", "LICENSE*"])
    (VISION / ".ready").write_text("Download complete\n")

    for repository,directory in [('mlx-community/whisper-large-v3-turbo','whisper-turbo'),('mlx-community/Qwen3-4B-Instruct-2507-4bit','qwen3-4b'),('mlx-community/Qwen3-VL-4B-Instruct-4bit','sports-vision-4b')]:
        target=SPEECH.parent/directory
        print('Downloading '+directory,flush=True)
        snapshot_download(repository,local_dir=str(target),allow_patterns=['*.json','*.safetensors','*.npz','*.txt','*.jinja','*.model','*.tiktoken','LICENSE*'])
        (target/'.ready').write_text(repository)

    print("Models ready. Double-click Start Clipping.command.", flush=True)
