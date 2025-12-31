import subprocess
import time

with open("app_output.log", "w") as f:
    process = subprocess.Popen(["python3", "main.py"], stdout=f, stderr=subprocess.STDOUT)

    time.sleep(5)

    process.terminate()
