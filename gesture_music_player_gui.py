import cv2
import mediapipe as mp
import tkinter as tk
from PIL import Image, ImageTk
import time
import math
import pyautogui
import subprocess
import psutil
import os
import ctypes
import sys

# Hide console window (for PyInstaller --onefile)
if sys.platform == 'win32':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Gesture utility functions
def distance(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def fingers_up(hand_landmarks):
    tips_ids = [4, 8, 12, 16, 20]
    fingers = []

    # Thumb detection
    thumb_mcp = hand_landmarks.landmark[2]
    thumb_tip = hand_landmarks.landmark[tips_ids[0]]
    thumb_length = distance(thumb_mcp, thumb_tip)
    thumb_extended = thumb_length > 0.05

    # Other fingers
    for i in range(1, 5):
        finger_tip = hand_landmarks.landmark[tips_ids[i]]
        finger_pip = hand_landmarks.landmark[tips_ids[i] - 2]
        fingers.append(finger_tip.y < finger_pip.y)

    fingers.insert(0, thumb_extended)
    return fingers

def is_thumbs_up(hand_landmarks):
    fingers = fingers_up(hand_landmarks)
    return fingers[0] and not any(fingers[1:])

def is_open_palm(hand_landmarks):
    fingers = fingers_up(hand_landmarks)
    return all(fingers)

def detect_gesture(hand_landmarks):
    fingers = fingers_up(hand_landmarks)

    if is_thumbs_up(hand_landmarks):
        return "thumbs_up", fingers
    elif is_open_palm(hand_landmarks):
        return "open_palm", fingers
    elif fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]:
        return "index_only", fingers
    elif fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
        return "index_middle", fingers
    elif fingers[1] and not fingers[2] and not fingers[3] and fingers[4]:
        return "index_pinky", fingers
    else:
        return None, fingers

def is_spotify_running():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == 'spotify.exe':
            return proc
    return None

class GestureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gesture Music Player")

        # Initialize webcam
        self.cap = cv2.VideoCapture(0)
        
        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

        # GUI setup
        self.label = tk.Label(root)
        self.label.pack()

        # Action cooldown
        self.last_action_time = 0
        self.action_cooldown = 2.0  # seconds

        self.update_frame()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            print("Failed to grab frame")
            self.root.after(10, self.update_frame)
            return

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

            gesture, fingers = detect_gesture(hand_landmarks)
            current_time = time.time()

            cv2.putText(frame, f"Gesture: {gesture}", (10, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Fingers: {fingers}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            if gesture and (current_time - self.last_action_time) > self.action_cooldown:
                self.handle_gesture(gesture)
                self.last_action_time = current_time
        else:
            cv2.putText(frame, "No Hand Detected", (10, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        self.label.imgtk = imgtk
        self.label.configure(image=imgtk)

        self.root.after(10, self.update_frame)

    def handle_gesture(self, gesture):
        if gesture == "thumbs_up":
            pyautogui.hotkey('alt', 'shift', 'b')
        elif gesture == "open_palm":
            pyautogui.press('space')
        elif gesture == "index_only":
            pyautogui.hotkey('ctrl', 'left')
        elif gesture == "index_middle":
            pyautogui.hotkey('ctrl', 'right')
        elif gesture == "index_pinky":
            if is_spotify_running():
                os.system("taskkill /f /im Spotify.exe")
            else:
                try:
                    subprocess.Popen(["start", "spotify:"], shell=True)
                except Exception as e:
                    print(f"Failed to open Spotify: {e}")

    def on_closing(self):
        self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GestureApp(root)
    root.mainloop()