import React, { useMemo, useRef, useState } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import toast from "react-hot-toast";

const steps = [
  "OTP Validation",
  "Location + Device Score",
  "Liveness Challenge",
  "Final Face Capture",
];

const StudentAttendancePage = () => {
  const webcamRef = useRef(null);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  const [otp, setOtp] = useState("");
  const [session, setSession] = useState(null);
  const [score, setScore] = useState(null);
  const [liveness, setLiveness] = useState(null);
  const [result, setResult] = useState(null);

  const canGoStep3 = !!score?.passed;
  const canGoStep4 =
    canGoStep3 && (liveness?.liveness_passed || !session?.requires_liveness);

  const progress = useMemo(() => (step / steps.length) * 100, [step]);

  const buildDeviceFingerprint = () => {
    const parts = [
      navigator.userAgent || "",
      navigator.platform || "",
      navigator.language || "",
      Intl.DateTimeFormat().resolvedOptions().timeZone || "",
      `${window.screen.width}x${window.screen.height}`,
      String(window.devicePixelRatio || 1),
    ];
    return parts.join("|");
  };

  const validateOtp = async () => {
    if (otp.trim().length !== 6)
      return toast.error("Enter a valid 6-digit OTP");
    setLoading(true);
    try {
      const res = await axios.post(
        "http://localhost:8000/attendance/validate-otp",
        {
          otp: otp.trim(),
        },
      );
      if (!res.data.success) {
        toast.error(res.data.message || "OTP validation failed");
        return;
      }
      setSession(res.data);
      setStep(2);
      toast.success("OTP validated");
    } catch (err) {
      toast.error(err.response?.data?.detail || "OTP validation failed");
    } finally {
      setLoading(false);
    }
  };

  const calculateScore = async () => {
    if (!session?.session_id) return;
    if (!navigator.geolocation) {
      toast.error("Geolocation is not supported in this browser");
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const deviceFingerprint = buildDeviceFingerprint();
          const res = await axios.post(
            "http://localhost:8000/attendance/calculate-score",
            {
              session_id: session.session_id,
              otp: otp.trim(),
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              device_fingerprint: deviceFingerprint,
              client_meta: {
                accuracy: position.coords.accuracy,
                timestamp: Date.now(),
              },
            },
          );
          setScore(res.data);
          if (res.data.passed) {
            toast.success(
              `Verification score passed (${res.data.total_score}/100)`,
            );
            setStep(3);
          } else {
            toast.error(
              `Score too low (${res.data.total_score}/100), required 70`,
            );
          }
        } catch (err) {
          toast.error(
            err.response?.data?.detail || "Failed to calculate score",
          );
        } finally {
          setLoading(false);
        }
      },
      (error) => {
        setLoading(false);
        toast.error(`Location permission failed: ${error.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  /**
   * UPDATED: Liveness capture logic
   * Now ensures exactly the object structure expected by LivenessFrame model
   */
  const runLiveness = async () => {
    if (!session?.requires_liveness) {
      setLiveness({ liveness_passed: true, confidence_score: 1, details: {} });
      setStep(4);
      return;
    }
    if (!webcamRef.current) return toast.error("Camera not ready");

    setLoading(true);
    toast("Capturing liveness... Please blink!", { icon: "📸" });

    try {
      const frames = [];
      // Capture 30 frames (minimum required by backend)
      for (let i = 0; i < 40; i++) {
        const frameData = webcamRef.current.getScreenshot();
        if (frameData) {
          frames.push({
            frame_data: frameData, // Matches Pydantic 'frame_data' field
            frame_number: i,
            timestamp: Date.now() / 1000,
          });
        }
        await new Promise((resolve) => setTimeout(resolve, 50)); // ~20fps
      }

      const res = await axios.post(
        "http://localhost:8000/attendance/verify-liveness",
        {
          session_id: session.session_id,
          otp: otp.trim(),
          frames: frames, // List of LivenessFrame objects
          challenges_completed: ["blink"],
        },
      );

      setLiveness(res.data);
      if (res.data.liveness_passed) {
        toast.success("Liveness verified!");
        setStep(4);
      } else {
        toast.error("Liveness failed. Try blinking more clearly.");
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail;
      // Handle Pydantic validation error specifically for easier debugging
      if (Array.isArray(errorMsg)) {
        toast.error("Data format error. Check console.");
        console.error("Validation Errors:", errorMsg);
      } else {
        toast.error(errorMsg || "Liveness verification failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const submitFinalAttendance = async () => {
    if (!session?.session_id || !score?.passed) return;
    const image = webcamRef.current?.getScreenshot();
    if (!image) return toast.error("Capture failed.");

    setLoading(true);
    try {
      const geo = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
        });
      });

      const res = await axios.post(
        "http://localhost:8000/attendance/mark-secure",
        {
          session_id: session.session_id,
          otp: otp.trim(),
          image: image, // Base64 string
          latitude: geo.coords.latitude,
          longitude: geo.coords.longitude,
          device_fingerprint: buildDeviceFingerprint(),
          liveness_data: {
            passed: !!liveness?.liveness_passed,
            confidence: liveness?.confidence_score || 0,
            details: liveness?.details || {},
          },
        },
      );

      setResult(res.data);
      if (res.data.success) {
        toast.success(res.data.message || "Attendance marked!");
      } else {
        toast.error(res.data.message || "Failed.");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Submission failed");
    } finally {
      setLoading(false);
    }
  };

  // ... (Keep the existing Return/JSX as it was, it looks solid)
  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* UI Code Same as before */}
      <div className="bg-white rounded-2xl shadow p-6">
        <h2 className="text-2xl font-black text-slate-800">
          Student Attendance
        </h2>
        <div className="mt-4 h-2 bg-slate-100 rounded-full">
          <div
            className="h-2 bg-indigo-600 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {steps.map((label, idx) => (
            <div
              key={label}
              className={`p-2 rounded-lg text-center font-semibold ${
                step === idx + 1
                  ? "bg-indigo-100 text-indigo-700"
                  : step > idx + 1
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-100 text-slate-500"
              }`}
            >
              {idx + 1}. {label}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow p-6 space-y-5 flex flex-col items-center">
        <Webcam
          audio={false}
          ref={webcamRef}
          screenshotFormat="image/jpeg"
          className="w-full max-w-md rounded-xl border border-slate-200 shadow-inner"
        />

        {step === 1 && (
          <div className="w-full flex flex-col items-center space-y-3">
            <input
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              maxLength={6}
              className="w-full max-w-sm px-4 py-3 border rounded-xl tracking-[0.3em] text-center font-mono text-xl"
              placeholder="000000"
            />
            <button
              disabled={loading}
              onClick={validateOtp}
              className="w-full max-w-sm px-5 py-3 bg-indigo-600 text-white rounded-xl font-bold"
            >
              {loading ? "Validating..." : "Validate OTP"}
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="w-full flex flex-col items-center space-y-3">
            <p className="text-slate-600">
              Course: <span className="font-bold">{session?.course_name}</span>
            </p>
            <button
              disabled={loading}
              onClick={calculateScore}
              className="w-full max-w-sm px-5 py-3 bg-indigo-600 text-white rounded-xl font-bold"
            >
              {loading ? "Checking Location..." : "Verify Location & Device"}
            </button>
          </div>
        )}

        {step === 3 && (
          <div className="w-full flex flex-col items-center space-y-3">
            <p className="text-slate-600 text-center animate-pulse">
              Blink your eyes naturally when you start.
            </p>
            <button
              disabled={loading}
              onClick={runLiveness}
              className="w-full max-w-sm px-5 py-3 bg-violet-600 text-white rounded-xl font-bold"
            >
              {loading ? "Analyzing Frames..." : "Start Liveness Check"}
            </button>
          </div>
        )}

        {step === 4 && (
          <div className="w-full flex flex-col items-center space-y-3">
            <button
              disabled={loading}
              onClick={submitFinalAttendance}
              className="w-full max-w-sm px-5 py-3 bg-emerald-600 text-white rounded-xl font-bold"
            >
              {loading ? "Submitting..." : "Submit Final Attendance"}
            </button>
          </div>
        )}
      </div>

      {result && (
        <div
          className={`rounded-2xl p-5 border ${result.success ? "bg-emerald-50 border-emerald-200" : "bg-rose-50 border-rose-200"}`}
        >
          <p className="font-bold text-slate-800">{result.message}</p>
          {result.student_name && (
            <p className="text-sm text-slate-600 mt-1">
              Confirmed as: {result.student_name}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default StudentAttendancePage;
