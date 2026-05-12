"""
Cleanup all IO pins.

This script resets all GPIO pins to a safe default state (input mode)
and releases any resources held by the GPIO library. Useful at the
end of a program or after an unexpected error to avoid leaving pins
in an undefined state.
"""

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None


def cleanup_all_pins():
    """Reset every GPIO pin and release library resources."""
    if GPIO is None:
        print("RPi.GPIO not available. Nothing to clean up.")
        return

    try:
        # Use BCM numbering; suppress warnings about channels already in use
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Set every BCM pin (0-27 on most Pi models) to input as a safe state
        for pin in range(0, 28):
            try:
                GPIO.setup(pin, GPIO.IN)
            except Exception as e:
                print(f"Could not reset pin {pin}: {e}")

        # Release all resources held by the GPIO library
        GPIO.cleanup()
        print("All IO pins cleaned up successfully.")

    except Exception as e:
        print(f"Error during cleanup: {e}")


if __name__ == "__main__":
    cleanup_all_pins()