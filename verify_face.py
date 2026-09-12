import cv2
import os
import sys

# Check for registered face samples
if not os.path.exists("face_data"):
    print("No registered face found.")
    sys.exit()

# Face detector
face_detector = cv2.CascadeClassifier(
    "haarcascade_frontalface_default.xml"
)

if face_detector.empty():
    print("Face detector could not be loaded.")
    sys.exit()

# Create LBPH face recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

faces = []
labels = []

# Load registered face samples
for filename in os.listdir("face_data"):

    if filename.endswith(".jpg"):

        image_path = os.path.join("face_data", filename)

        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if image is not None:
            faces.append(image)
            labels.append(1)

if not faces:
    print("No face samples found.")
    sys.exit()

# Train recognizer
recognizer.train(faces, __import__("numpy").array(labels))

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    sys.exit()

print("🔐 Face verification started.")
print("Look at the camera...")

unlocked = False

while True:

    success, frame = camera.read()

    if not success:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    detected_faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5
    )

    for (x, y, w, h) in detected_faces:

        face = gray[y:y+h, x:x+w]

        label, confidence = recognizer.predict(face)

        # Lower confidence = better match
        if confidence < 70:

            unlocked = True

            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "ACCESS GRANTED",
                (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

        else:

            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "ACCESS DENIED",
                (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

    cv2.imshow("AI Chatbot - Face ID", frame)

    # Unlock
    if unlocked:
        cv2.waitKey(1200)
        break

    # Q = quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

if unlocked:
    print("🔓 FACE VERIFIED")
    print("AI CHATBOT UNLOCKED")
    sys.exit(0)
else:
    print("🔒 ACCESS DENIED")
    sys.exit(1)