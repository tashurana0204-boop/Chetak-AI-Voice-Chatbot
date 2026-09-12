import subprocess
import sys
import time
import webbrowser


print("================================")
print("     AI VOICE CHATBOT")
print("================================")
print()
print("🔐 Starting Face ID...")

result = subprocess.run(
    [sys.executable, "verify_face.py"],
    check=False
)

if result.returncode != 0:
    print()
    print("🔒 Access denied.")
    print("Chatbot will remain locked.")
    input("Press Enter to exit...")
    sys.exit(1)

print()
print("🔓 Face verified!")
print("🤖 Starting AI chatbot...")

time.sleep(1)

# Start Flask
subprocess.Popen(
    [sys.executable, "app.py"]
)

time.sleep(2)

# Open chatbot in browser
webbrowser.open("http://127.0.0.1:5000")

print()
print("🚀 AI Chatbot is running!")