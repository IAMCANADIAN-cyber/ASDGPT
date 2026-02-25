import tkinter as tk
from tkinter import messagebox
import sys

def show_alert(title, message):
    root = tk.Tk()
    root.withdraw() # Hide the main window
    root.attributes('-topmost', True) # Keep on top

    # We use showwarning for now, but could be showinfo or showerror
    messagebox.showwarning(title, message)

    root.destroy()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python show_alert.py <title> <message>")
        sys.exit(1)

    title = sys.argv[1]
    message = sys.argv[2]
    show_alert(title, message)
