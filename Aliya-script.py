import mss
import time
import pytesseract
from PIL import Image
import shutil
import hashlib

def capture_screen():
    region = {
        "top": 150,
        "left": 500,
        "width": 480,
        "height": 870
    }
    with mss.mss() as sct:
        screenshot = sct.grab(region)
        img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
        img.save("screenshot.png")
    return "screenshot.png"

def extract_text(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    return text

def classify_messages(ocr_data, screen_width):
    messages = []
    current_text = ""
    current_left = None
    current_top = None
    previous_bottom = -9999
    vertical_threshold = 25  # adjust based on font size and spacing

    for i in range(len(ocr_data['text'])):
        word = ocr_data['text'][i].strip()
        if word == "":
            continue

        top = ocr_data['top'][i]
        height = ocr_data['height'][i]
        bottom = top + height
        left = ocr_data['left'][i]

        # New message if vertical gap is too large
        if top - previous_bottom > vertical_threshold:
            if current_text:
                side = "Aliya" if current_left < screen_width // 2 else "Player"
                messages.append((side, current_text.strip()))
            current_text = word
            current_left = left
        else:
            current_text += " " + word
        previous_bottom = bottom

    # Catch the last message
    if current_text:
        side = "Aliya" if current_left < screen_width // 2 else "Player"
        messages.append((side, current_text.strip()))

    return messages

recent_messages = set()

def write_unique_messages(dialogue, filename='aliya_chat_log.txt'):
    global recent_messages
    with open(filename, 'a', encoding='utf-8') as f:
        for speaker, message in dialogue:
            line = f"{speaker}: {message}".strip()
            # Basic normalization: remove double spaces, lowercase
            normalized = ' '.join(line.lower().split())
            if normalized not in recent_messages:
                f.write(line + '\n')
                recent_messages.add(normalized)

                # Optional: limit memory use
                if len(recent_messages) > 1000:
                    recent_messages = set(list(recent_messages)[-500:])

def write_to_file(dialogue, filename='aliya_chat_log.txt'):
    with open(filename, 'a', encoding='utf-8') as f:
        for speaker, message in dialogue:
            f.write(f"{speaker}: {message}\n")

def main_loop():
    screen_width = 480  # since your capture is 480px wide

    while True:
        screenshot_path = capture_screen()
        ocr_data = extract_text(screenshot_path)
        raw_messages = classify_messages(ocr_data, screen_width)
        write_unique_messages(raw_messages)  # ← This was missing

        time.sleep(1)  # adjust depending on dialogue pacing

if __name__ == "__main__":
    main_loop()