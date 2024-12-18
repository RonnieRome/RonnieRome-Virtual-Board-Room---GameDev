import cv2
# Make sure OpenCV is installed by running "pip install opencv-python-headless" or "pip install opencv-python" if you require GUI support.

# Load image
image = cv2.imread('backgrounds/Saturn.jpg')

# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Detect circles using Hough Circle Transform
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1.2, 100)

# Draw circles on the image
if circles is not None:
    for circle in circles[0]:
        cv2.circle(image, (circle[0], circle[1]), circle[2], (0,255,0), 2)

# Display the result
cv2.imshow('Image with Circles', image)
cv2.waitKey(0)
cv2.destroyAllWindows()