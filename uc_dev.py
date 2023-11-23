#!/usr/bin/python


import os
import sys
import signal


uc_dev = os.path.expanduser('~')+"/.uc_dev/repo"

if not os.path.exists( uc_dev ):
    os.system("git clone https://github.com/lordrasmus/uclibc-ng-dev.git " + uc_dev )


sys.path.append(uc_dev)


from uc_dev import *


def signal_handler(sig, frame):
    print("\nCtrl+C (SIGINT) received. Cleaning up or performing any necessary actions.")
    # Füge hier deinen eigenen Code hinzu, der beim Empfangen von Ctrl+C ausgeführt werden soll
    sys.exit(0)  # Beende das Programm sauber (optional)

# Registriere den Signal-Handler für Ctrl+C (SIGINT)
signal.signal(signal.SIGINT, signal_handler)

# Beispielcode, der auf das Signal wartet
print("Press Ctrl+C to trigger the signal handler.")

if __name__ == '__main__':
    dev_uc_main.dev_uc_main()


