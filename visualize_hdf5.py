"""
HDF5 RGB VISUALIZER
Continuously visualize RGB frames from HDF5 robot data files
"""
import sys
import h5py
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def visualize_hdf5(hdf5_path, output_path=None, num_frames=9):
    """
    Create a visual montage of RGB frames from HDF5 file

    Args:
        hdf5_path: Path to HDF5 file
        output_path: Where to save visualization (default: auto-generated)
        num_frames: Number of frames to show (default: 9)
    """
    hdf5_path = Path(hdf5_path)

    if not hdf5_path.exists():
        print(f"❌ File not found: {hdf5_path}")
        return False

    print("="*70)
    print("HDF5 RGB VISUALIZER")
    print("="*70)
    print(f"File: {hdf5_path.name}")
    print()

    try:
        with h5py.File(hdf5_path, 'r') as f:
            # Check for RGB data
            demo = f['data/demo_0']

            if 'obs/agentview_rgb' not in demo:
                print("❌ No RGB frames found in this file!")
                print("   This appears to be a pose-only HDF5 file.")
                return False

            rgb_frames = demo['obs/agentview_rgb']
            total_frames = len(rgb_frames)

            print(f"Total frames: {total_frames}")
            print(f"Frame shape: {rgb_frames.shape}")
            print(f"Data type: {rgb_frames.dtype}")
            print()

            # Get metadata
            task_name = demo.attrs.get('task_name', 'unknown')
            confidence = demo.attrs.get('confidence', 0.0)
            duration = demo.attrs.get('duration', 0.0)

            print(f"Task: {task_name}")
            print(f"Confidence: {confidence:.2%}")
            print(f"Duration: {duration:.1f}s")
            print()

            # Calculate which frames to extract (evenly spaced)
            if num_frames > total_frames:
                num_frames = total_frames

            frame_indices = np.linspace(0, total_frames-1, num_frames, dtype=int)

            print(f"Extracting {num_frames} frames...")
            print(f"Frame indices: {frame_indices.tolist()}")
            print()

            # Extract frames
            frames = []
            for idx in frame_indices:
                frame = rgb_frames[idx]
                # Convert to PIL Image
                img = Image.fromarray(frame, mode='RGB')
                frames.append((idx, img))

            # Create montage
            print("Creating visualization montage...")

            # Calculate grid dimensions
            cols = int(np.ceil(np.sqrt(num_frames)))
            rows = int(np.ceil(num_frames / cols))

            # Frame size
            frame_w, frame_h = frames[0][1].size

            # Montage size (with padding and labels)
            padding = 10
            label_height = 30
            montage_w = cols * frame_w + (cols + 1) * padding
            montage_h = rows * (frame_h + label_height) + (rows + 1) * padding

            # Create montage canvas
            montage = Image.new('RGB', (montage_w, montage_h), color=(20, 20, 20))
            draw = ImageDraw.Draw(montage)

            # Add frames to montage
            for i, (frame_idx, frame) in enumerate(frames):
                row = i // cols
                col = i % cols

                x = col * frame_w + (col + 1) * padding
                y = row * (frame_h + label_height) + (row + 1) * padding

                # Paste frame
                montage.paste(frame, (x, y))

                # Add label
                timestamp = (frame_idx / total_frames) * duration
                label = f"Frame {frame_idx} ({timestamp:.1f}s)"

                # Draw label background
                label_y = y + frame_h
                draw.rectangle(
                    [(x, label_y), (x + frame_w, label_y + label_height)],
                    fill=(40, 40, 40)
                )

                # Draw label text
                try:
                    # Try to use a nice font
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
                except:
                    # Fall back to default
                    font = ImageFont.load_default()

                # Center text
                bbox = draw.textbbox((0, 0), label, font=font)
                text_w = bbox[2] - bbox[0]
                text_x = x + (frame_w - text_w) // 2
                text_y = label_y + 5

                draw.text((text_x, text_y), label, fill=(255, 255, 255), font=font)

            # Add title
            title_height = 50
            final_montage = Image.new('RGB', (montage_w, montage_h + title_height), color=(10, 10, 10))

            # Draw title
            draw = ImageDraw.Draw(final_montage)
            title = f"{hdf5_path.stem[:50]}"
            subtitle = f"Task: {task_name} | Confidence: {confidence:.0%} | {total_frames} frames"

            try:
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
                subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()

            draw.text((padding, 5), title, fill=(255, 255, 255), font=title_font)
            draw.text((padding, 28), subtitle, fill=(180, 180, 180), font=subtitle_font)

            # Paste montage below title
            final_montage.paste(montage, (0, title_height))

            # Save
            if output_path is None:
                output_path = f"{hdf5_path.stem}_visualization.png"

            final_montage.save(output_path)

            print(f"✅ Visualization saved: {output_path}")
            print(f"   Size: {Path(output_path).stat().st_size / 1024:.1f} KB")
            print(f"   Grid: {rows}×{cols} ({num_frames} frames)")
            print()
            print("="*70)
            print("✅ VISUALIZATION COMPLETE")
            print("="*70)
            print()
            print(f"Open '{output_path}' to see RGB frames!")

            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def visualize_directory(directory, pattern="*.hdf5", num_frames=9):
    """
    Visualize all HDF5 files in a directory

    Args:
        directory: Path to directory
        pattern: File pattern to match (default: *.hdf5)
        num_frames: Frames per file
    """
    directory = Path(directory)

    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return

    hdf5_files = list(directory.glob(pattern))

    if not hdf5_files:
        print(f"❌ No HDF5 files found in {directory}")
        return

    print("="*70)
    print(f"BATCH VISUALIZATION")
    print("="*70)
    print(f"Directory: {directory}")
    print(f"Files found: {len(hdf5_files)}")
    print()

    success_count = 0

    for i, hdf5_file in enumerate(hdf5_files, 1):
        print(f"[{i}/{len(hdf5_files)}] Processing: {hdf5_file.name}")

        output_path = f"visualizations/{hdf5_file.stem}_viz.png"
        Path("visualizations").mkdir(exist_ok=True)

        if visualize_hdf5(hdf5_file, output_path, num_frames):
            success_count += 1

        print()

    print("="*70)
    print("BATCH COMPLETE")
    print("="*70)
    print(f"Successfully visualized: {success_count}/{len(hdf5_files)}")
    print(f"Output directory: visualizations/")


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Visualize RGB frames from HDF5 robot data files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize single file
  python visualize_hdf5.py test_rgb_output.hdf5

  # Visualize with custom frame count
  python visualize_hdf5.py test_rgb_output.hdf5 --frames 16

  # Visualize all files in directory
  python visualize_hdf5.py data_mine/permanent_data/hdf5/ --batch

  # Custom output path
  python visualize_hdf5.py test.hdf5 --output my_viz.png
        """
    )

    parser.add_argument('path', help='HDF5 file or directory')
    parser.add_argument('--frames', '-f', type=int, default=9,
                       help='Number of frames to show (default: 9)')
    parser.add_argument('--output', '-o', help='Output image path')
    parser.add_argument('--batch', '-b', action='store_true',
                       help='Process all HDF5 files in directory')

    args = parser.parse_args()

    path = Path(args.path)

    if args.batch or path.is_dir():
        # Batch mode
        visualize_directory(path, num_frames=args.frames)
    else:
        # Single file
        visualize_hdf5(path, args.output, args.frames)


if __name__ == '__main__':
    main()
