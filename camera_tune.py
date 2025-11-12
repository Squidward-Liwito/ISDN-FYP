import cv2
import subprocess
import time
import numpy as np
import json
import os

# ============================================
# CAMERA CONFIGURATION - Adjust these values
# ============================================
CAMERA_CONFIG = {
    # Device settings
    'device': '/dev/video0',
    'width': 640,
    'height': 480,
    'fps': 30,
    
    # Exposure and brightness (v4l2 hardware controls)
    'auto_exposure': 1,        # 0=auto, 1=manual (IMPORTANT: 1 for manual control!)
    'exposure': 800,           # 4-1964 (lower=darker, higher=brighter)
    'analogue_gain': 112,      # 16-1023 (lower=less noise, higher=brighter)
    'white_balance_auto': 0,   # 0=manual, 1=auto (for color correction)
    
    # Image processing (OpenCV software controls)
    'brightness_offset': 15,    # -100 to 100
    'contrast': 1.4,           # 0.5 to 3.0 (1.0 = no change)
    'saturation': 1.1,         # 0.0 to 2.0 (1.0 = no change)
    'sharpness': 0.0,          # 0.0 to 2.0 (0.0 = no sharpening)
    
    # RGB Channel gains (0.0 to 2.0, 1.0 = no change)
    'red_gain': 1.0,           # Red channel multiplier
    'green_gain': 1.0,         # Green channel multiplier
    'blue_gain': 1.0,          # Blue channel multiplier
    
    # Advanced
    'denoise': False,          # Apply denoising filter
    'auto_adjust': False,      # Auto brightness/contrast (experimental)
}

# Settings file path
SETTINGS_FILE = os.path.expanduser('~/Desktop/camera_settings.json')

# ============================================
# SETTINGS SAVE/LOAD FUNCTIONS
# ============================================

def save_settings(config):
    """Save camera settings to JSON file"""
    try:
        # Only save the settings we want to persist (not device/width/height)
        settings_to_save = {
            'auto_exposure': config['auto_exposure'],
            'exposure': config['exposure'],
            'analogue_gain': config['analogue_gain'],
            'white_balance_auto': config['white_balance_auto'],
            'brightness_offset': config['brightness_offset'],
            'contrast': config['contrast'],
            'saturation': config['saturation'],
            'sharpness': config['sharpness'],
            'red_gain': config['red_gain'],
            'green_gain': config['green_gain'],
            'blue_gain': config['blue_gain'],
            'denoise': config['denoise'],
        }
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        
        print(f"✓ Settings saved to {SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"Warning: Failed to save settings: {e}")
        return False

def load_settings():
    """Load camera settings from JSON file"""
    if not os.path.exists(SETTINGS_FILE):
        print("No saved settings found, using defaults")
        return CAMERA_CONFIG.copy()
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            saved_settings = json.load(f)
        
        # Start with default config
        config = CAMERA_CONFIG.copy()
        
        # Update with saved settings
        config.update(saved_settings)
        
        print(f"✓ Settings loaded from {SETTINGS_FILE}")
        return config
    except Exception as e:
        print(f"Warning: Failed to load settings: {e}")
        return CAMERA_CONFIG.copy()

# ============================================
# CAMERA CONTROL FUNCTIONS
# ============================================

def set_v4l2_control(device, control, value):
    """Set V4L2 camera control using v4l2-ctl"""
    try:
        subprocess.run(['v4l2-ctl', '-d', device, f'--set-ctrl={control}={value}'], 
                      check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to set {control}={value}: {e.stderr}")
        return False

def apply_camera_hardware_settings(config):
    """Apply hardware camera settings via V4L2"""
    device = config['device']
    
    print("Applying hardware camera settings...")
    
    # IMPORTANT: Set auto_exposure to manual (0) first to allow manual exposure control
    set_v4l2_control(device, 'auto_exposure', config['auto_exposure'])
    time.sleep(0.1)  # Give camera time to switch modes
    
    # Now set manual exposure and gain values
    set_v4l2_control(device, 'exposure', config['exposure'])
    set_v4l2_control(device, 'analogue_gain', config['analogue_gain'])
    set_v4l2_control(device, 'white_balance_automatic', config['white_balance_auto'])
    
    print("✓ Hardware settings applied")
    mode = "MANUAL" if config['auto_exposure'] == 1 else "AUTO"
    print(f"  - Exposure mode: {mode} (auto_exposure={config['auto_exposure']})")
    print(f"  - Exposure: {config['exposure']}")
    print(f"  - Gain: {config['analogue_gain']}")

def adjust_brightness_contrast(image, brightness=0, contrast=1.0):
    """Adjust brightness and contrast"""
    if brightness != 0:
        if brightness > 0:
            shadow = brightness
            highlight = 255
        else:
            shadow = 0
            highlight = 255 + brightness
        alpha_b = (highlight - shadow) / 255
        gamma_b = shadow
        image = cv2.addWeighted(image, alpha_b, image, 0, gamma_b)
    
    if contrast != 1.0:
        image = cv2.convertScaleAbs(image, alpha=contrast, beta=0)
    
    return image

def adjust_saturation(image, saturation=1.0):
    """Adjust color saturation"""
    if saturation == 1.0:
        return image
    
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = hsv[:, :, 1] * saturation
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def adjust_rgb_channels(image, red_gain=1.0, green_gain=1.0, blue_gain=1.0):
    """Adjust individual RGB channel gains"""
    if red_gain == 1.0 and green_gain == 1.0 and blue_gain == 1.0:
        return image
    
    # Split image into B, G, R channels
    b, g, r = cv2.split(image.astype(np.float32))
    
    # Apply gains to each channel
    r = np.clip(r * red_gain, 0, 255)
    g = np.clip(g * green_gain, 0, 255)
    b = np.clip(b * blue_gain, 0, 255)
    
    # Merge channels back
    result = cv2.merge([b, g, r]).astype(np.uint8)
    return result

def apply_sharpening(image, amount=0.5):
    """Apply sharpening filter"""
    if amount <= 0:
        return image
    
    kernel = np.array([[-1,-1,-1],
                       [-1, 9,-1],
                       [-1,-1,-1]]) * (amount / 8)
    kernel[1, 1] = 1 + amount
    return cv2.filter2D(image, -1, kernel)

def apply_image_processing(frame, config):
    """Apply all software image processing"""
    # Brightness and contrast
    frame = adjust_brightness_contrast(frame, 
                                       config['brightness_offset'], 
                                       config['contrast'])
    
    # Saturation
    frame = adjust_saturation(frame, config['saturation'])
    
    # RGB channel gains
    frame = adjust_rgb_channels(frame, 
                               config['red_gain'], 
                               config['green_gain'], 
                               config['blue_gain'])
    
    # Sharpening
    if config['sharpness'] > 0:
        frame = apply_sharpening(frame, config['sharpness'])
    
    # Denoising
    if config['denoise']:
        frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
    
    return frame

def display_settings_overlay(frame, config):
    """Display current settings on frame"""
    y_offset = 30
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.45
    color = (0, 255, 0)
    thickness = 1
    
    auto_mode = "AUTO" if config['auto_exposure'] == 1 else "MANUAL"
    settings_text = [
        f"Exposure: {config['exposure']} (A/Z) [{auto_mode} - T to toggle]",
        f"Gain: {config['analogue_gain']} (S/X)",
        f"Brightness: {config['brightness_offset']} (D/C)",
        f"Contrast: {config['contrast']:.1f} (F/V)",
        f"Saturation: {config['saturation']:.1f} (G/B)",
        f"Sharpness: {config['sharpness']:.1f} (H/N)",
        f"",
        f"Red:   {config['red_gain']:.2f} (J/M)",
        f"Green: {config['green_gain']:.2f} (K/,)",
        f"Blue:  {config['blue_gain']:.2f} (L/.)",
        f"",
        f"Q:Quit | R:Reset | P:Print | O:Hide | T:Auto/Manual"
    ]
    
    for i, text in enumerate(settings_text):
        cv2.putText(frame, text, (10, y_offset + i * 18), 
                   font, font_scale, color, thickness, cv2.LINE_AA)
    
    return frame

# ============================================
# MAIN PROGRAM
# ============================================

def main():
    # Load saved settings or use defaults
    config = load_settings()
    
    # Initialize camera
    print(f"Opening camera: {config['device']}")
    cap = cv2.VideoCapture(config['device'])
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['width'])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['height'])
    cap.set(cv2.CAP_PROP_FPS, config['fps'])
    
    # Wait for camera to initialize
    time.sleep(0.5)
    
    # Apply hardware settings
    apply_camera_hardware_settings(config)
    
    print("\n" + "="*70)
    print("CAMERA PREVIEW WITH REAL-TIME CONTROLS + AUTO-SAVE")
    print("="*70)
    print("\nKeyboard Controls:")
    print("  Auto/Manual:  T (toggle auto/manual exposure)")
    print("  Exposure:     A (increase) / Z (decrease)")
    print("  Gain:         S (increase) / X (decrease)")
    print("  Brightness:   D (increase) / C (decrease)")
    print("  Contrast:     F (increase) / V (decrease)")
    print("  Saturation:   G (increase) / B (decrease)")
    print("  Sharpness:    H (increase) / N (decrease)")
    print("")
    print("  Red Channel:   J (increase) / M (decrease)")
    print("  Green Channel: K (increase) / , (decrease)")
    print("  Blue Channel:  L (increase) / . (decrease)")
    print("")
    print("  Toggle Overlay: O")
    print("  Reset:          R (reset to defaults)")
    print("  Print Settings: P (print current settings)")
    print("  Quit:           Q (auto-saves on exit)\n")
    print("="*70 + "\n")
    
    show_overlay = True
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            break
        
        # Apply image processing
        processed_frame = apply_image_processing(frame, config)
        
        # Show settings overlay
        if show_overlay:
            display_frame = display_settings_overlay(processed_frame.copy(), config)
        else:
            display_frame = processed_frame
        
        cv2.imshow('Camera Preview', display_frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('o') or key == ord('O'):
            show_overlay = not show_overlay
        elif key == ord('r') or key == ord('R'):
            config = CAMERA_CONFIG.copy()
            apply_camera_hardware_settings(config)
            print("Settings reset to defaults")
        elif key == ord('p') or key == ord('P'):
            print("\nCurrent Settings:")
            mode = "MANUAL" if config['auto_exposure'] == 1 else "AUTO"
            print(f"  auto_exposure: {config['auto_exposure']} ({mode})")
            print(f"  exposure: {config['exposure']}")
            print(f"  analogue_gain: {config['analogue_gain']}")
            print(f"  brightness_offset: {config['brightness_offset']}")
            print(f"  contrast: {config['contrast']:.1f}")
            print(f"  saturation: {config['saturation']:.1f}")
            print(f"  sharpness: {config['sharpness']:.1f}")
            print(f"  red_gain: {config['red_gain']:.2f}")
            print(f"  green_gain: {config['green_gain']:.2f}")
            print(f"  blue_gain: {config['blue_gain']:.2f}\n")
        elif key == ord('t') or key == ord('T'):
            # Toggle auto/manual exposure (0=auto, 1=manual)
            config['auto_exposure'] = 0 if config['auto_exposure'] == 1 else 1
            set_v4l2_control(config['device'], 'auto_exposure', config['auto_exposure'])
            time.sleep(0.1)
            mode = "MANUAL" if config['auto_exposure'] == 1 else "AUTO"
            print(f"Exposure mode: {mode}")
        
        # Exposure controls
        elif key == ord('a') or key == ord('A'):
            # Ensure manual mode is enabled (1=manual)
            if config['auto_exposure'] != 1:
                config['auto_exposure'] = 1
                set_v4l2_control(config['device'], 'auto_exposure', 1)
                time.sleep(0.1)
                print("Switched to MANUAL exposure mode")
            config['exposure'] = min(config['exposure'] + 50, 1964)
            set_v4l2_control(config['device'], 'exposure', config['exposure'])
        elif key == ord('z') or key == ord('Z'):
            # Ensure manual mode is enabled (1=manual)
            if config['auto_exposure'] != 1:
                config['auto_exposure'] = 1
                set_v4l2_control(config['device'], 'auto_exposure', 1)
                time.sleep(0.1)
                print("Switched to MANUAL exposure mode")
            config['exposure'] = max(config['exposure'] - 50, 4)
            set_v4l2_control(config['device'], 'exposure', config['exposure'])
        
        # Gain controls
        elif key == ord('s') or key == ord('S'):
            config['analogue_gain'] = min(config['analogue_gain'] + 32, 1023)
            set_v4l2_control(config['device'], 'analogue_gain', config['analogue_gain'])
        elif key == ord('x') or key == ord('X'):
            config['analogue_gain'] = max(config['analogue_gain'] - 32, 16)
            set_v4l2_control(config['device'], 'analogue_gain', config['analogue_gain'])
        
        # Brightness controls
        elif key == ord('d') or key == ord('D'):
            config['brightness_offset'] = min(config['brightness_offset'] + 5, 100)
        elif key == ord('c') or key == ord('C'):
            config['brightness_offset'] = max(config['brightness_offset'] - 5, -100)
        
        # Contrast controls
        elif key == ord('f') or key == ord('F'):
            config['contrast'] = min(config['contrast'] + 0.1, 3.0)
        elif key == ord('v') or key == ord('V'):
            config['contrast'] = max(config['contrast'] - 0.1, 0.5)
        
        # Saturation controls
        elif key == ord('g') or key == ord('G'):
            config['saturation'] = min(config['saturation'] + 0.1, 2.0)
        elif key == ord('b') or key == ord('B'):
            config['saturation'] = max(config['saturation'] - 0.1, 0.0)
        
        # Sharpness controls
        elif key == ord('h') or key == ord('H'):
            config['sharpness'] = min(config['sharpness'] + 0.1, 2.0)
        elif key == ord('n') or key == ord('N'):
            config['sharpness'] = max(config['sharpness'] - 0.1, 0.0)
        
        # RED channel controls
        elif key == ord('j') or key == ord('J'):
            config['red_gain'] = min(config['red_gain'] + 0.05, 2.0)
        elif key == ord('m') or key == ord('M'):
            config['red_gain'] = max(config['red_gain'] - 0.05, 0.0)
        
        # GREEN channel controls
        elif key == ord('k') or key == ord('K'):
            config['green_gain'] = min(config['green_gain'] + 0.05, 2.0)
        elif key == 44:  # comma key ','
            config['green_gain'] = max(config['green_gain'] - 0.05, 0.0)
        
        # BLUE channel controls
        elif key == ord('l') or key == ord('L'):
            config['blue_gain'] = min(config['blue_gain'] + 0.05, 2.0)
        elif key == 46:  # period key '.'
            config['blue_gain'] = max(config['blue_gain'] - 0.05, 0.0)
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    # Save settings before exit
    print("\nSaving settings...")
    save_settings(config)
    print("Camera closed. Goodbye!")

if __name__ == "__main__":
    main()