import serial
import re
import time

PORT = '/dev/ttyUSB0'
BAUD = 9600   # 🔴 try 115200 first

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)  # allow device to initialize
    print(f"Connected to {PORT} at {BAUD}")

    count = 0

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()

            count += 1

            # skip initial garbage lines
            if count <= 10:
                continue

            numbers = re.findall(r'-?\d+\.?\d*', line)

            if len(numbers) == 3:
                x, y, z = map(float, numbers)

                print(f"X: {x:8.4f}  Y: {y:8.4f}  Z: {z:8.4f}")

        else:
            # helpful debug message
            
            time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopped by user.")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Serial closed.")