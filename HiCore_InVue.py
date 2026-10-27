# import serial
#
# # Open COM15 at 9600 baud (change if needed)
# ser = serial.Serial('COM15', 9600, timeout=1)
#
# print("Reading from COM15...")
#
# try:
#     while True:
#         line = ser.readline().decode(errors='ignore').strip()
#         if line:
#             print("Received:", line)
#
# except KeyboardInterrupt:
#     print("Stopped by user.")
#
# finally:
#     ser.close()
# import tkinter as tk
# import serial
# import threading
# import time
#
# # ---- Serial Setup ----
# ser = serial.Serial('COM15', 9600, timeout=1)
#
# # ---- UI Setup ----
# root = tk.Tk()
# root.title("HiCore Stock View")
# root.geometry("300x150")
#
# label = tk.Label(root, text="Waiting for data...", font=("Arial", 16))
# label.pack(pady=20)
#
# running = True
#
# # ---- Function to Read Serial ----
# def read_serial():
#     while running:
#         try:
#             data = ser.readline().decode(errors='ignore').strip()
#             if data:
#                 # Update UI safely
#                 label.after(0, lambda d=data: label.config(text=f"{d}"))
#         except:
#             pass
#         time.sleep(0.05)
#
# # ---- Start Serial Thread ----
# thread = threading.Thread(target=read_serial, daemon=True)
# thread.start()
#
# # ---- Handle Close ----
# def on_close():
#     global running
#     running = False
#     ser.close()
#     root.destroy()
#
# root.protocol("WM_DELETE_WINDOW", on_close)
#
# root.mainloop()


import tkinter as tk
import serial
import threading
import time
import requests
import re

# ---- Serial Setup ----
ser = serial.Serial('COM5', 9600, timeout=1)

# ---- API Endpoint ----
# API_URL = "https://inventory-88g5.onrender.com/devices/1/weight"
API_URL = "http://151.185.41.194:8005/inventory/1/update-weight"

# ---- UI Setup ----
root = tk.Tk()
root.title("HiCore Stock View")
root.geometry("300x150")

label = tk.Label(root, text="Waiting for data...", font=("Arial", 16))
label.pack(pady=20)

running = True
latest_weight = None
last_sent_weight = None
last_sent_time = 0

SEND_INTERVAL = 5     # seconds
DIFF_WEIGHT = 10      # threshold

# ---- Extract Numeric Weight ----
def extract_weight(text):
    match = re.search(r"-?\d+\.?\d*", text)
    return float(match.group()) if match else None

# ---- Send Weight (PUT) ----
def send_weight(weight):
    try:
        response = requests.put(
            API_URL,
            params={"weight": weight},
            timeout=5
        )
        print(f"Sent: {weight} | Status: {response.status_code}")
    except requests.RequestException as e:
        print("API Error:", e)

# ---- Read Serial Data ----
def read_serial():
    global latest_weight
    while running:
        try:
            data = ser.readline().decode(errors='ignore').strip()
            if data:
                clean_weight = extract_weight(data)
                if clean_weight is not None:
                    latest_weight = clean_weight
                    label.after(0, lambda d=clean_weight: label.config(text=str(d)))
        except Exception as e:
            print("Serial Error:", e)

        time.sleep(0.05)

# ---- Send When Threshold Crossed (Up OR Down) ----
def send_loop():
    global last_sent_time, last_sent_weight

    while running:
        if latest_weight is not None:
            current_time = time.time()

            if current_time - last_sent_time >= SEND_INTERVAL:
                if last_sent_weight is None:
                    send_weight(latest_weight)
                    last_sent_weight = latest_weight
                else:
                    if (
                        latest_weight >= last_sent_weight + DIFF_WEIGHT or
                        latest_weight <= last_sent_weight - DIFF_WEIGHT
                    ):
                        send_weight(latest_weight)
                        last_sent_weight = latest_weight
                    else:
                        print("Threshold not crossed, not sent")

                last_sent_time = current_time

        time.sleep(0.1)

# ---- Start Threads ----
threading.Thread(target=read_serial, daemon=True).start()
threading.Thread(target=send_loop, daemon=True).start()

# ---- Handle Close ----
def on_close():
    global running
    running = False
    ser.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()