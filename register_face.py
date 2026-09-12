import cv2
import os

# Create folder for face samples
os.makedirs("face_data", exist_ok=True)

# Load OpenCV face detector
face_detector = cv2.CascadeClassifier(
    "haarcascade_frontalface_default.xml"
)

if face_detector.empty():
    print("Face detector could not be loaded.")
    exit()

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()

print("Starting face registration...")
print("Look at the camera.")
print("Press Q to stop.")

count = 0

while True:
    success, frame = camera.read()

    if not success:
        print("Could not read camera.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5
    )

    for (x, y, w, h) in faces:

        # Draw rectangle around detected face
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (255, 255, 255),
            2
        )

        # Save face sample
        face = gray[y:y+h, x:x+w]

        filename = f"face_data/user_{count}.jpg"
        cv2.imwrite(filename, face)

        count += 1

    cv2.putText(
        frame,
        f"Samples: {count}/30",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    cv2.imshow("AI Chatbot - Face Registration", frame)

    if cv2.waitKey(100) & 0xFF == ord("q"):
        break

    if count >= 30:
        break

camera.release()
cv2.destroyAllWindows()

print(f"\nFace registration completed!")
print(f"{count} face samples saved in face_data.")