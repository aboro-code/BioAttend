import React, { useState, useRef, useEffect } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import toast from "react-hot-toast";
import { Camera, CheckCircle, RefreshCw } from "lucide-react";

const Enrollment = () => {
  const webcamRef = useRef(null);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);

  useEffect(() => {
    // Proactively release backend camera when this component mounts
    const prepareCamera = async () => {
      try {
        await axios.post("http://localhost:8000/camera/release");
        console.log("✅ Backend camera released for enrollment");
        // Wait for Windows to fully release
        await new Promise((resolve) => setTimeout(resolve, 800));
        setCameraReady(true);
      } catch (error) {
        console.error("Camera release error:", error);
        toast.error("Camera may be in use. Try refreshing.");
      }
    };

    prepareCamera();
  }, []);

  const handleEnroll = async () => {
    if (!name.trim()) return toast.error("Please enter a name");

    setLoading(true);
    const imageSrc = webcamRef.current?.getScreenshot();

    if (!imageSrc) {
      toast.error("Camera not ready. Please refresh.");
      setLoading(false);
      return;
    }

    try {
      const response = await axios.post("http://localhost:8000/enroll", {
        name: name,
        image: imageSrc,
      });

      if (response.data.success) {
        toast.success(response.data.message);
        setName("");
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      toast.error("Enrollment failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8 animate-in slide-in-from-bottom-4 duration-700">
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-black text-slate-800">New Registration</h2>
        <p className="text-slate-500">
          Stand in front of the camera and enter your name.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        <div className="relative bg-black rounded-3xl overflow-hidden shadow-2xl aspect-square border-4 border-white">
          {cameraReady ? (
            <Webcam
              audio={false}
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              className="w-full h-full object-cover"
              onUserMedia={() => console.log("✅ Webcam ready")}
              onUserMediaError={(err) => {
                console.error("Webcam error:", err);
                toast.error("Camera blocked. Click the refresh button.");
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-white">
              <RefreshCw className="w-8 h-8 animate-spin" />
            </div>
          )}
        </div>

        <div className="bg-white p-8 rounded-3xl border border-slate-100 shadow-xl space-y-4">
          <input
            type="text"
            placeholder="Student Full Name"
            className="w-full p-4 bg-slate-50 border-2 border-slate-100 rounded-2xl focus:border-indigo-500 outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button
            onClick={handleEnroll}
            disabled={loading || !cameraReady}
            className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              "Processing..."
            ) : (
              <>
                <Camera /> Enroll Student
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Enrollment;
