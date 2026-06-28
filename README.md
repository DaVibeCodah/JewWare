# JewWare

An interactive, high-performance screen overlay engine built using Python and PyQt6. It provides a highly customizable vector crosshair alongside dynamic visual effects, making it a robust template for immersive screen overlays.

---

## ✨ Features

- **High-Performance Crosshair:** Smooth spinning crosshair with fully adjustable speed, scale, and exact pixel coordinate alignment.
- **Independent Spawning Pools:** Separated controls for custom Hebrew text phrases, Star of David shapes, and custom image uploads.
- **Divided Physics Engine:** Independent sliders to control the travel speed, sizes, and total count of both bouncing symbols and images separately.
- **Smart Hotkey Listener:** Press `*` at any time to seamlessly fade the control dashboard out of sight without losing window focus or stopping background rendering.
- **Dynamic Taskbar Icon:** Displays a real-time vector graphic icon on your OS taskbar that spins in sync with your crosshair speed.
- **Photosensitivity Interceptor:** Includes a toggleable random full-screen event engine with precise timer intervals.

---

## 🛠️ Requirements

Make sure you have Python 3 installed, then install the required dependencies using pip:

```bash
pip install PyQt6 Pillow mss requests
```


## 🚀 How to Use

1. Run the script using Python:
   ```bash
   python jewware.py
   ```
2. Accept the safety warning to launch the control board.
3. Align the crosshair onto your target display screen using the interactive canvas preview.
4. Press the `*` key on your keyboard to instantly hide or show the control panel.

---

## 🛡️ License

This project is licensed under the Creative Commons Attribution 4.0 International (CC BY 4.0) License.
