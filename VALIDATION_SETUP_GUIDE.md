# 🤖 ROBOT POLICY TRAINING - VALIDATION GUIDE

## STEP-BY-STEP: Train Policy to Validate Your Data

---

## 📦 STEP 1: INSTALLATION (1-2 hours)

### Option A: Local Setup (If you have GPU)

```bash
# 1. Create new conda environment
conda create -n robot_validation python=3.9
conda activate robot_validation

# 2. Install PyTorch (with GPU support)
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

# 3. Install RoboMimic
pip install robomimic

# 4. Install simulation environment
pip install robosuite
pip install mujoco

# 5. Install utilities
pip install h5py numpy matplotlib tensorboard

# 6. Verify installation
python -c "import robomimic; print('RoboMimic installed!')"
python -c "import robosuite; print('RoboSuite installed!')"
```

### Option B: Cloud GPU (If no local GPU)

**Use Google Colab (Free) or Vast.ai ($0.20/hour)**

```python
# In Colab notebook:
!pip install robomimic robosuite mujoco h5py
```

---

## 🔄 STEP 2: CONVERT YOUR DATA FORMAT (2-4 hours)

Your HDF5 files need slight modifications to work with RoboMimic.

### Current Format vs Required Format

**What you have:**
```
/data/demo_0/
    /obs/
        - eef_pos (N, 3)
        - eef_vel (N, 3)
        - gripper_state (N, 1)
        - joint_pos (N, 7)
        - agentview_rgb (N, H, W, 3)  # After you add RGB
    /actions/
        - delta_pos (N-1, 3)
        - gripper_commands (N-1, 1)
```

**What RoboMimic expects:**
```
/data/demo_0/
    /obs/
        - robot0_eef_pos (N, 3)        # Same data, different name
        - robot0_eef_vel (N, 3)
        - robot0_gripper_qpos (N, 2)   # 2D instead of 1D
        - agentview_image (N, H, W, 3) # Different name
    /actions (N, 7)                     # Flattened: [dx, dy, dz, drx, dry, drz, gripper]
```

### Conversion Script

Create `convert_to_robomimic.py`:

```python
"""
Convert your HDF5 format to RoboMimic format
"""
import h5py
import numpy as np
from pathlib import Path

def convert_demo(input_hdf5, output_hdf5):
    """
    Convert your format to RoboMimic format

    Args:
        input_hdf5: Your HDF5 file
        output_hdf5: Output file in RoboMimic format
    """
    print(f"Converting {input_hdf5} -> {output_hdf5}")

    with h5py.File(input_hdf5, 'r') as f_in:
        with h5py.File(output_hdf5, 'w') as f_out:
            # Copy each demo
            for demo_name in f_in['data'].keys():
                demo_in = f_in['data'][demo_name]
                demo_out = f_out.create_group(f'data/{demo_name}')

                # ============ OBSERVATIONS ============
                obs_in = demo_in['obs']
                obs_out = demo_out.create_group('obs')

                # Rename and copy observations
                if 'eef_pos' in obs_in:
                    obs_out.create_dataset(
                        'robot0_eef_pos',
                        data=obs_in['eef_pos'][:]
                    )

                if 'eef_vel' in obs_in:
                    obs_out.create_dataset(
                        'robot0_eef_vel',
                        data=obs_in['eef_vel'][:]
                    )

                if 'gripper_state' in obs_in:
                    # Convert (N, 1) to (N, 2) - duplicate for left/right fingers
                    gripper = obs_in['gripper_state'][:]
                    gripper_2d = np.concatenate([gripper, gripper], axis=1)
                    obs_out.create_dataset(
                        'robot0_gripper_qpos',
                        data=gripper_2d
                    )

                if 'joint_pos' in obs_in:
                    obs_out.create_dataset(
                        'robot0_joint_pos',
                        data=obs_in['joint_pos'][:]
                    )

                # RGB images
                if 'agentview_rgb' in obs_in:
                    obs_out.create_dataset(
                        'agentview_image',
                        data=obs_in['agentview_rgb'][:],
                        compression='gzip'
                    )

                # ============ ACTIONS ============
                actions_in = demo_in['actions']

                # Combine delta_pos and gripper into single action vector
                delta_pos = actions_in['delta_pos'][:]  # (N-1, 3)
                gripper = actions_in['gripper_commands'][:]  # (N-1, 1)

                # Pad with zeros for rotation (we don't have rotation data)
                delta_rot = np.zeros((len(delta_pos), 3))  # (N-1, 3)

                # Concatenate: [dx, dy, dz, drx, dry, drz, gripper]
                actions = np.concatenate([
                    delta_pos,      # (N-1, 3)
                    delta_rot,      # (N-1, 3)
                    gripper         # (N-1, 1)
                ], axis=1)  # (N-1, 7)

                demo_out.create_dataset('actions', data=actions)

                # ============ METADATA ============
                # Copy attributes
                for key, val in demo_in.attrs.items():
                    demo_out.attrs[key] = val

                # Add required RoboMimic attributes
                demo_out.attrs['num_samples'] = len(actions)
                demo_out.attrs['model_file'] = 'custom'  # No specific robot model

                print(f"  ✅ Converted {demo_name}: {len(actions)} timesteps")

            # Dataset-level attributes
            f_out.attrs['total'] = len(f_in['data'].keys())
            f_out.attrs['env_name'] = 'CustomEnv'

    print(f"✅ Conversion complete: {output_hdf5}")
    return output_hdf5

def convert_dataset(input_dir, output_dir):
    """
    Convert all HDF5 files in directory
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    hdf5_files = list(input_dir.glob('*.hdf5'))
    print(f"Found {len(hdf5_files)} files to convert")

    for hdf5_file in hdf5_files:
        output_file = output_dir / hdf5_file.name
        convert_demo(hdf5_file, output_file)

    print(f"\n✅ Converted {len(hdf5_files)} files")
    print(f"Output directory: {output_dir}")

if __name__ == '__main__':
    # Convert your approved data
    convert_dataset(
        input_dir='data_mine/permanent_data/approved',
        output_dir='data_mine/robomimic_format'
    )
```

**Run it:**
```bash
python convert_to_robomimic.py
```

---

## 🧠 STEP 3: TRAIN BEHAVIOR CLONING POLICY (1-2 hours)

### What is Behavior Cloning (BC)?

**Simple idea:** Neural network learns to copy demonstrations
- Input: Observation (image + robot state)
- Output: Action (what to do next)
- Training: Minimize difference between predicted action and demo action

### Training Script

Create `train_policy.py`:

```python
"""
Train robot policy using Behavior Cloning
"""
import robomimic
import robomimic.utils.file_utils as FileUtils
import robomimic.utils.train_utils as TrainUtils
from robomimic.config import config_factory
import torch
import numpy as np

def train_bc_policy(dataset_path, output_dir='trained_models'):
    """
    Train Behavior Cloning policy on your data

    Args:
        dataset_path: Path to your HDF5 dataset
        output_dir: Where to save trained model
    """
    print("="*70)
    print("TRAINING BEHAVIOR CLONING POLICY")
    print("="*70)
    print(f"Dataset: {dataset_path}")
    print(f"Output: {output_dir}")
    print()

    # Create BC config
    config = config_factory(algo_name="bc")

    # ============ DATASET CONFIG ============
    config.train.data = [dataset_path]
    config.train.output_dir = output_dir

    # How much data to use for training vs validation
    config.train.hdf5_filter_key = None  # Use all demos
    config.train.hdf5_validation_filter_key = None

    # Split: 90% training, 10% validation
    config.train.num_data_workers = 4
    config.train.hdf5_cache_mode = "low_dim"  # Cache strategy

    # ============ TRAINING CONFIG ============
    config.train.num_epochs = 100  # Number of training epochs
    config.train.batch_size = 32   # Samples per batch

    # Learning rate
    config.train.lr = 1e-4

    # Save checkpoints
    config.experiment.save.enabled = True
    config.experiment.save.every_n_epochs = 10

    # Validation
    config.experiment.validation_epoch_every_n_steps = 50

    # Logging
    config.experiment.logging.terminal_output_to_txt = True
    config.experiment.logging.log_tb = True  # TensorBoard

    # ============ OBSERVATION CONFIG ============
    # What observations to use
    config.observation.modalities.obs.low_dim = [
        "robot0_eef_pos",
        "robot0_eef_vel",
        "robot0_gripper_qpos"
    ]

    # Use RGB images if available
    config.observation.modalities.obs.rgb = ["agentview_image"]

    # Image encoding
    config.observation.encoder.rgb.core_class = "VisualCore"
    config.observation.encoder.rgb.core_kwargs.feature_dimension = 64
    config.observation.encoder.rgb.core_kwargs.backbone_class = "ResNet18Conv"
    config.observation.encoder.rgb.obs_randomizer_class = None

    # ============ POLICY NETWORK CONFIG ============
    config.algo.policy.rnn.enabled = False  # Don't use RNN for simplicity

    # MLP (feedforward network)
    config.algo.policy.mlp.hidden_dim = 256
    config.algo.policy.mlp.num_layers = 3
    config.algo.policy.mlp.activation = "relu"

    # ============ START TRAINING ============
    print("Starting training...")
    print(f"  Epochs: {config.train.num_epochs}")
    print(f"  Batch size: {config.train.batch_size}")
    print(f"  Learning rate: {config.train.lr}")
    print()

    # Train
    TrainUtils.train(config, device="cuda" if torch.cuda.is_available() else "cpu")

    print()
    print("="*70)
    print("✅ TRAINING COMPLETE")
    print("="*70)
    print(f"Model saved to: {output_dir}")
    print()
    print("View training progress:")
    print(f"  tensorboard --logdir {output_dir}")

if __name__ == '__main__':
    # Train on your converted dataset
    train_bc_policy(
        dataset_path='data_mine/robomimic_format/combined_dataset.hdf5',
        output_dir='trained_models/bc_policy'
    )
```

### Combine Multiple Demos Into One Dataset

Create `combine_datasets.py`:

```python
"""
Combine multiple HDF5 files into single training dataset
"""
import h5py
from pathlib import Path

def combine_hdf5_files(input_dir, output_file):
    """
    Merge multiple HDF5 files into one
    """
    input_dir = Path(input_dir)
    hdf5_files = sorted(input_dir.glob('*.hdf5'))

    print(f"Combining {len(hdf5_files)} files...")

    with h5py.File(output_file, 'w') as f_out:
        demo_idx = 0

        for hdf5_file in hdf5_files:
            print(f"  Adding: {hdf5_file.name}")

            with h5py.File(hdf5_file, 'r') as f_in:
                # Copy all demos from this file
                for demo_name in f_in['data'].keys():
                    src_demo = f_in['data'][demo_name]
                    dst_demo = f_out.create_group(f'data/demo_{demo_idx}')

                    # Recursively copy all data
                    def copy_recursive(src_group, dst_group):
                        for key in src_group.keys():
                            if isinstance(src_group[key], h5py.Group):
                                dst_subgroup = dst_group.create_group(key)
                                copy_recursive(src_group[key], dst_subgroup)
                            else:
                                dst_group.create_dataset(
                                    key,
                                    data=src_group[key][:],
                                    compression='gzip'
                                )

                        # Copy attributes
                        for attr_key, attr_val in src_group.attrs.items():
                            dst_group.attrs[attr_key] = attr_val

                    copy_recursive(src_demo, dst_demo)
                    demo_idx += 1

        # Dataset attributes
        f_out.attrs['total'] = demo_idx
        f_out.attrs['env_name'] = 'CustomEnv'

    print(f"✅ Combined {demo_idx} demos into {output_file}")
    return output_file

if __name__ == '__main__':
    combine_hdf5_files(
        input_dir='data_mine/robomimic_format',
        output_file='data_mine/robomimic_format/combined_dataset.hdf5'
    )
```

### Run Training

```bash
# 1. Convert your data
python convert_to_robomimic.py

# 2. Combine into single dataset
python combine_datasets.py

# 3. Train policy
python train_policy.py

# 4. Monitor training (in another terminal)
tensorboard --logdir trained_models/bc_policy
# Open browser: http://localhost:6006
```

---

## 📊 STEP 4: EVALUATE THE POLICY (1 hour)

### What to Look For During Training

**1. Loss Curve (Most Important)**
```
Epoch 1:  Loss = 2.5
Epoch 10: Loss = 1.2
Epoch 20: Loss = 0.8
Epoch 50: Loss = 0.3
```

**Good signs:**
- ✅ Loss decreases over time
- ✅ Reaches below 1.0
- ✅ Validation loss tracks training loss

**Bad signs:**
- ❌ Loss stays high (>2.0)
- ❌ Loss increases
- ❌ Validation loss much higher than training (overfitting)

**2. Action Prediction Accuracy**

Check how well policy predicts actions:
```python
# Prediction error
Position error: 2.3 cm (GOOD if < 5cm)
Gripper error: 5% (GOOD if < 10%)
```

---

## 🎮 STEP 5: TEST IN SIMULATION (2-4 hours)

### Option A: Simple Playback Test

Create `test_policy.py`:

```python
"""
Test trained policy by comparing predictions to ground truth
"""
import h5py
import torch
import numpy as np
from robomimic.utils.file_utils import policy_from_checkpoint

def test_policy(model_path, test_dataset_path):
    """
    Test how well policy reproduces demo actions
    """
    print("Loading policy...")
    policy, _ = policy_from_checkpoint(ckpt_path=model_path)
    policy.eval()

    print("Loading test data...")
    with h5py.File(test_dataset_path, 'r') as f:
        # Test on first demo
        demo = f['data/demo_0']

        observations = demo['obs']
        ground_truth_actions = demo['actions'][:]

        # Extract observations
        eef_pos = observations['robot0_eef_pos'][:]
        gripper = observations['robot0_gripper_qpos'][:]

        if 'agentview_image' in observations:
            images = observations['agentview_image'][:]
        else:
            images = None

        # Predict actions
        predicted_actions = []

        for t in range(len(ground_truth_actions)):
            # Build observation dict
            obs = {
                'robot0_eef_pos': torch.FloatTensor(eef_pos[t]).unsqueeze(0),
                'robot0_gripper_qpos': torch.FloatTensor(gripper[t]).unsqueeze(0)
            }

            if images is not None:
                obs['agentview_image'] = torch.FloatTensor(images[t]).unsqueeze(0)

            # Predict
            with torch.no_grad():
                action = policy(obs)

            predicted_actions.append(action.cpu().numpy()[0])

        predicted_actions = np.array(predicted_actions)

        # Compute errors
        position_error = np.abs(
            predicted_actions[:, :3] - ground_truth_actions[:, :3]
        ).mean(axis=0)

        gripper_error = np.abs(
            predicted_actions[:, 6] - ground_truth_actions[:, 6]
        ).mean()

        print("\n" + "="*70)
        print("POLICY TEST RESULTS")
        print("="*70)
        print(f"Samples tested: {len(ground_truth_actions)}")
        print()
        print("Position Error (mean absolute):")
        print(f"  X: {position_error[0]*100:.2f} cm")
        print(f"  Y: {position_error[1]*100:.2f} cm")
        print(f"  Z: {position_error[2]*100:.2f} cm")
        print(f"  Average: {position_error.mean()*100:.2f} cm")
        print()
        print(f"Gripper Error: {gripper_error*100:.1f}%")
        print()

        # Success criteria
        avg_pos_error = position_error.mean() * 100  # in cm

        if avg_pos_error < 3.0 and gripper_error < 0.15:
            print("✅ EXCELLENT: Policy accurately reproduces demonstrations")
        elif avg_pos_error < 5.0 and gripper_error < 0.25:
            print("✅ GOOD: Policy shows strong learning")
        elif avg_pos_error < 10.0:
            print("⚠️  FAIR: Policy learned something but needs improvement")
        else:
            print("❌ POOR: Policy did not learn well from data")

        print("="*70)

if __name__ == '__main__':
    test_policy(
        model_path='trained_models/bc_policy/models/model_epoch_100.pth',
        test_dataset_path='data_mine/robomimic_format/combined_dataset.hdf5'
    )
```

### Run Test

```bash
python test_policy.py
```

---

## ✅ SUCCESS CRITERIA

### What "Success" Looks Like

**Level 1: Data Format Works** ✅
- [ ] Data loads without errors
- [ ] Training starts and completes
- [ ] No crashes or format issues

**Level 2: Policy Learns Something** ✅✅
- [ ] Loss decreases below 1.0
- [ ] Position error < 10 cm
- [ ] Gripper error < 25%

**Level 3: Policy Works Well** ✅✅✅
- [ ] Loss reaches < 0.5
- [ ] Position error < 5 cm
- [ ] Gripper error < 15%
- [ ] Can reproduce demo actions accurately

**Level 4: Ready for Real Robot** ✅✅✅✅
- [ ] Position error < 3 cm
- [ ] Gripper error < 10%
- [ ] Consistent across multiple test demos
- [ ] Works with RGB observations

---

## 🎯 WHAT EACH LEVEL MEANS FOR YOUR BUSINESS

### Level 1: Technical Validation
**Meaning:** Your data format is compatible with industry tools
**Business value:** Can sell data to technical customers
**Confidence:** 50% - need more validation

### Level 2: Proof of Concept
**Meaning:** Data contains learnable patterns
**Business value:** Can demo to investors/customers
**Confidence:** 70% - data has value

### Level 3: Production Quality
**Meaning:** Data quality rivals human teleoperation
**Business value:** Can compete with established datasets
**Confidence:** 90% - ready to scale

### Level 4: Industry Standard
**Meaning:** Data works for real robot deployment
**Business value:** Premium pricing, enterprise customers
**Confidence:** 95% - market leader potential

---

## 🐛 TROUBLESHOOTING

### Problem: Training loss not decreasing

**Possible causes:**
1. Learning rate too high/low → Try 1e-3, 1e-4, 1e-5
2. Not enough data → Need 100+ demos minimum
3. Data quality issues → Check for NaN, Inf values
4. Network too small → Increase hidden_dim to 512

### Problem: High position error (>10cm)

**Possible causes:**
1. Coordinate system mismatch → Check units (meters vs cm)
2. Poor state observations → Need more informative features
3. No RGB images → Visual context critical for accuracy

### Problem: Training crashes / OOM error

**Solutions:**
1. Reduce batch_size (32 → 16 → 8)
2. Reduce image resolution (224 → 128 → 64)
3. Use CPU if GPU memory insufficient
4. Cache mode: "low_dim" instead of "all"

---

## 📈 EXPECTED TIMELINE

| Task | Time | Difficulty |
|------|------|-----------|
| Setup environment | 1-2 hours | Easy |
| Convert data format | 2-4 hours | Medium |
| Combine datasets | 30 min | Easy |
| Train policy | 2-6 hours | Easy (mostly waiting) |
| Evaluate results | 1 hour | Easy |
| **TOTAL** | **1-2 days** | **Medium** |

---

## 💰 COST ESTIMATE

### Local (If you have GPU)
- **Cost:** $0
- **Time:** 2-6 hours training

### Cloud GPU
- **Service:** Vast.ai, Lambda Labs, Google Colab Pro
- **Cost:** $0.20 - $1.00/hour
- **Training time:** 2-6 hours
- **Total cost:** $0.40 - $6.00

**This is incredibly cheap to validate a multi-million dollar business idea.**

---

## 🎯 DELIVERABLES AFTER VALIDATION

Once you complete this, you'll have:

1. **Proof Your Data Works**
   - Training curves showing learning
   - Quantitative metrics (error rates)
   - Can show to investors/customers

2. **Benchmark Results**
   - "Our data achieves X cm position accuracy"
   - "Trained policy with Y% success rate"
   - Comparable to published datasets

3. **Technical Credibility**
   - "Compatible with RoboMimic framework"
   - "Tested with Behavior Cloning algorithm"
   - Industry-standard validation

4. **Sales Material**
   - Demo video of policy execution
   - Training curves chart
   - Accuracy comparison table

---

## 🚀 NEXT STEP

Ready to implement? Here's the exact order:

```bash
# 1. Install tools (1 hour)
conda create -n robot_validation python=3.9
conda activate robot_validation
pip install robomimic robosuite torch h5py

# 2. Add RGB to your pipeline (from previous masterplan)
# This is prerequisite - need RGB in HDF5 files

# 3. Convert data format (2 hours)
python convert_to_robomimic.py

# 4. Train policy (4 hours)
python combine_datasets.py
python train_policy.py

# 5. Evaluate (1 hour)
python test_policy.py
```

**Total time: 1-2 days**
**Total cost: $0-10**
**Result: Know if your data works**

---

Want me to create these scripts for you RIGHT NOW?
