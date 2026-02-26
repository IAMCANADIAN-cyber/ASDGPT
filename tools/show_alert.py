import tkinter as tk
from tkinter import messagebox
import sys

def show_alert(title, message):
    root = tk.Tk()
    root.withdraw() # Hide main window

    # Make it top most
    root.attributes('-topmost', True)

    # Use simple messagebox
    messagebox.showwarning(title, message)

    root.destroy()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        title = sys.argv[1]
        message = sys.argv[2]
        show_alert(title, message)
    else:
        print("Usage: python3 show_alert.py <title> <message>")
