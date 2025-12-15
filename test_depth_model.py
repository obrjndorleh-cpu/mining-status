"""
TEST DEPTH-ANYTHING V2
Quick test to verify depth model works
"""

import cv2
import numpy as np
import torch
from depth_anything_v2.dpt import DepthAnythingV2

def test_depth_model():
    print("🔬 Testing Depth-Anything V2...")

    # Model configuration
    model_configs = {
        'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
        'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
        'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]}
    }

    # Use small model for faster inference
    encoder = 'vits'  # Small model

    print(f"\n📦 Loading model: {encoder}")

    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    print(f"   Device: {device}")

    model = DepthAnythingV2(**model_configs[encoder])

    # Download pretrained weights
    print(f"   Downloading pretrained weights...")
    checkpoint_url = f'https://huggingface.co/depth-anything/Depth-Anything-V2-{encoder.upper()}/resolve/main/depth_anything_v2_{encoder}.pth'

    try:
        checkpoint = torch.hub.load_state_dict_from_url(
            checkpoint_url,
            map_location='cpu'
        )
        model.load_state_dict(checkpoint)
        print(f"   ✅ Weights loaded")
    except Exception as e:
        print(f"   ❌ Failed to load weights: {e}")
        return False

    model = model.to(device)
    model.eval()

    # Test on dummy image
    print(f"\n🎨 Testing on dummy image...")
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    with torch.no_grad():
        depth = model.infer_image(test_image)

    print(f"   Input shape: {test_image.shape}")
    print(f"   Depth shape: {depth.shape}")
    print(f"   Depth range: {depth.min():.3f} to {depth.max():.3f}")

    print(f"\n✅ Depth model test PASSED!")
    return True

if __name__ == "__main__":
    test_depth_model()
