import React, { useState, useEffect } from "react";
import AttendanceTable from "./AttendanceTable";
import StudentGallery from "./StudentGallery";
import Enrollment from "./Enrollment";
import { Users, ClipboardList, ShieldCheck, UserPlus } from "lucide-react";
import { Toaster } from "react-hot-toast";
import axios from "axios";

function App() {
  const [view, setView] = useState(() => {
    return localStorage.getItem("currentView") || "attendance";
  });

  const [cameraReleasing, setCameraReleasing] = useState(false);

  // Handle view changes with camera coordination
  const handleViewChange = async (newView) => {
    // If switching away from attendance, release camera
    if (view === "attendance" && newView !== "attendance") {
      setCameraReleasing(true);
      try {
        await axios.post("http://localhost:8000/camera/release");
        console.log("Camera released by App coordinator");
      } catch (error) {
        console.error("Camera release error:", error);
      }

      // Wait for Windows to process
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setCameraReleasing(false);
    }

    setView(newView);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Toaster position="top-right" />

      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 p-2 rounded-xl shadow-indigo-200 shadow-lg">
              <ShieldCheck className="text-white w-5 h-5" />
            </div>
            <h1 className="text-xl font-black tracking-tight text-slate-800">
              BIO<span className="text-indigo-600">ATTEND</span>
            </h1>
          </div>

          <nav className="flex gap-2 bg-slate-100 p-1.5 rounded-2xl">
            <NavBtn
              active={view === "attendance"}
              onClick={() => handleViewChange("attendance")}
              icon={ClipboardList}
              label="Live Logs"
              disabled={cameraReleasing}
            />
            <NavBtn
              active={view === "enroll"}
              onClick={() => handleViewChange("enroll")}
              icon={UserPlus}
              label="Enroll"
              disabled={cameraReleasing}
            />
            <NavBtn
              active={view === "gallery"}
              onClick={() => handleViewChange("gallery")}
              icon={Users}
              label="Gallery"
              disabled={cameraReleasing}
            />
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full py-8 px-6">
        {cameraReleasing ? (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-slate-600 font-medium">Releasing camera...</p>
            </div>
          </div>
        ) : (
          <>
            {view === "attendance" && <AttendanceTable />}
            {view === "enroll" && <Enrollment />}
            {view === "gallery" && <StudentGallery />}
          </>
        )}
      </main>
    </div>
  );
}

const NavBtn = ({ active, onClick, icon: Icon, label, disabled }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold transition-all ${
      active
        ? "bg-white text-indigo-600 shadow-md scale-105"
        : "text-slate-500 hover:text-slate-700"
    } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
  >
    <Icon className="w-4 h-4" />
    {label}
  </button>
);

export default App;
