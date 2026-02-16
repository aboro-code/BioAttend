import React, { useState, useEffect } from "react";
import AttendanceTable from "./AttendanceTable";
import StudentGallery from "./StudentGallery";
import Enrollment from "./Enrollment";
import { Users, ClipboardList, ShieldCheck, UserPlus } from "lucide-react";
import { Toaster } from "react-hot-toast";

function App() {
  // Initialize state from localStorage, default to 'attendance'
  const [view, setView] = useState(() => {
    return localStorage.getItem("currentView") || "attendance";
  });

  // Save view to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem("currentView", view);
  }, [view]);

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
              onClick={() => setView("attendance")}
              icon={ClipboardList}
              label="Live Logs"
            />
            <NavBtn
              active={view === "enroll"}
              onClick={() => setView("enroll")}
              icon={UserPlus}
              label="Enroll"
            />
            <NavBtn
              active={view === "gallery"}
              onClick={() => setView("gallery")}
              icon={Users}
              label="Gallery"
            />
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full py-8 px-6">
        {view === "attendance" && <AttendanceTable />}
        {view === "enroll" && <Enrollment />}
        {view === "gallery" && <StudentGallery />}
      </main>
    </div>
  );
}

const NavBtn = ({ active, onClick, icon: Icon, label }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold transition-all ${
      active
        ? "bg-white text-indigo-600 shadow-md scale-105"
        : "text-slate-500 hover:text-slate-700"
    }`}
  >
    <Icon className="w-4 h-4" />
    {label}
  </button>
);

export default App;
