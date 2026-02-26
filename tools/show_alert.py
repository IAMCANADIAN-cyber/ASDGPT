import tkinter as tk
import sys

def show_alert(message):
    """
    Displays a blocking, full-screen alert window with the given message.
    """
    try:
        root = tk.Tk()
        root.title("ASDGPT Alert")

        # Configure window to be topmost and fullscreen-ish
        root.attributes('-topmost', True)
        root.geometry("600x400")

        # Center on screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (600 // 2)
        y = (screen_height // 2) - (400 // 2)
        root.geometry(f"600x400+{x}+{y}")

        # Add message label
        label = tk.Label(root, text=message, font=("Arial", 24), wraplength=550, justify="center")
        label.pack(expand=True, padx=20, pady=20)

        # Add acknowledge button
        btn = tk.Button(root, text="I acknowledge. I will take a break.", font=("Arial", 14), command=root.destroy, bg="#ffdddd")
        btn.pack(pady=20)

        # Handle close window event (prevent easy closing without acknowledgement if desired, but for now allow it)
        root.protocol("WM_DELETE_WINDOW", root.destroy)

        root.mainloop()
    except Exception as e:
        print(f"Error showing alert: {e}")

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Urgent Alert: Please take a break."
    show_alert(msg)
