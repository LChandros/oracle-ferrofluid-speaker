#!/usr/bin/env python3
import lgpio
import time

# GPIO 16 (physical pin 36)
GPIO_PIN = 16

print('Opening GPIO chip...')
h = lgpio.gpiochip_open(0)

print('Setting up GPIO 16 as output...')
lgpio.gpio_claim_output(h, GPIO_PIN)

try:
    print('Turning electromagnet ON...')
    lgpio.gpio_write(h, GPIO_PIN, 1)
    
    print('Electromagnet should be ON for 5 seconds - check if it attracts metal!')
    time.sleep(5)
    
    print('Turning electromagnet OFF...')
    lgpio.gpio_write(h, GPIO_PIN, 0)
    print('Done!')
    
except KeyboardInterrupt:
    print('\nInterrupted by user')
    lgpio.gpio_write(h, GPIO_PIN, 0)
    
except Exception as e:
    print(f'Error: {e}')
    lgpio.gpio_write(h, GPIO_PIN, 0)
    
finally:
    lgpio.gpio_free(h, GPIO_PIN)
    lgpio.gpiochip_close(h)
    print('GPIO cleaned up')
