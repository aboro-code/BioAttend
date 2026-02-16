import cv2

def capture_photo(output_name="rongu.jpg"):
    # 0 is usually the default built-in webcam
    cam = cv2.VideoCapture(0)
    
    print("Press SPACE to capture, or ESC to exit.")
    
    while True:
        ret, frame = cam.read()
        if not ret:
            print("Failed to grab frame")
            break
            
        cv2.imshow("Webcam Test - Press SPACE to Capture", frame)
        
        k = cv2.waitKey(1) & 0xFF
        if k == 27: # ESC pressed
            print("Closing...")
            break
        elif k == ord(' '): # SPACE pressed
            cv2.imwrite(output_name, frame)
            print(f"✅ Photo saved as {output_name}!")
            break

    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_photo()