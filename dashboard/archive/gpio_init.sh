#!/bin/bash
# Initialize GPIO pin 18 (physical pin 12) to LOW at boot
# Using gpioset - runs in background to hold the pin state

# GPIO18 = physical pin 12 (magnet control)
gpioset --mode=signal --chip gpiochip0 18=0 &
