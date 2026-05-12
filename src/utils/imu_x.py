import serial
import re
import time

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
time.sleep(2)

try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()

            numbers = re.findall(r'-?\d+\.?\d*', line)

            if len(numbers) == 3:
                x = float(numbers[0])   # ONLY X

                print(f"Heading: {x:.4f}")

        else:
            time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    ser.close()