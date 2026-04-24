import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import StudentGallery from "./StudentGallery";
import Enrollment from "./Enrollment";
import ProfessorDashboard from "./ProfessorDashboard";
import StudentAttendancePage from "./StudentAttendancePage";
import {
  Users,
  ShieldCheck,
  UserPlus,
  GraduationCap,
  ScanFace,
  Home,
} from "lucide-react";
import { Toaster } from "react-hot-toast";
import toast from "react-hot-toast";
import API, { setAuthToken } from "./api";

function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const [auth, setAuth] = useState(() => {
    const raw = localStorage.getItem("auth");
    const parsedAuth = raw ? JSON.parse(raw) : null;
    setAuthToken(parsedAuth?.token || null);
    return parsedAuth;
  });

  const [cameraReleasing, setCameraReleasing] = useState(false);

  const handlePageChange = async (newPath) => {
    if (location.pathname === "/student" && newPath !== "/student") {
      setCameraReleasing(true);
      try {
        await API.post("/camera/release");
        console.log("✅ Camera released by App coordinator");
      } catch (error) {
        console.error("Camera release error:", error);
      }

      await new Promise((resolve) => setTimeout(resolve, 1000));
      setCameraReleasing(false);
    }
    navigate(newPath);
  };

  useEffect(() => {
    setAuthToken(auth?.token || null);
    if (auth) {
      localStorage.setItem("auth", JSON.stringify(auth));
    } else {
      localStorage.removeItem("auth");
    }
  }, [auth]);

  const handleLogin = async (username, password) => {
    try {
      const res = await API.post("/auth/login", { username, password });
      const userAuth = {
        token: res.data.access_token,
        role: res.data.role,
        username: res.data.username,
      };
      setAuth(userAuth);
      navigate(res.data.role === "professor" ? "/professor" : "/student");
      toast.success(`Welcome, ${res.data.username}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Login failed");
    }
  };

  const logout = () => {
    setAuth(null);
    navigate("/");
    toast.success("Logged out");
  };

  const isProfessor = auth?.role === "professor";

  if (!auth && (location.pathname.startsWith("/professor") || location.pathname === "/login")) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <Toaster position="top-right" />
        <LoginCard onLogin={handleLogin} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Toaster position="top-right" />

      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <button
            type="button"
            onClick={() => handlePageChange("/")}
            className="flex items-center gap-3 select-none"
            aria-label="Go to home"
            disabled={cameraReleasing}
          >
            <div className="bg-indigo-600 p-2 rounded-xl shadow-indigo-200 shadow-lg">
              <ShieldCheck className="text-white w-5 h-5" />
            </div>
            <h1 className="text-xl font-black tracking-tight text-slate-800">
              BIO<span className="text-indigo-600">ATTEND</span>
            </h1>
          </button>

          <div className="flex items-center gap-3">
            <nav className="flex gap-2 bg-slate-100 p-1.5 rounded-2xl">
              <NavBtn
                active={location.pathname === "/"}
                onClick={() => handlePageChange("/")}
                icon={Home}
                label="Home"
                disabled={cameraReleasing}
              />
              {isProfessor && (
                <>
                  <NavBtn
                    active={location.pathname === "/professor" || location.pathname.startsWith("/professor/sessions")}
                    onClick={() => handlePageChange("/professor")}
                    icon={GraduationCap}
                    label="Professor"
                    disabled={cameraReleasing}
                  />
                  <NavBtn
                    active={location.pathname === "/professor/enroll"}
                    onClick={() => handlePageChange("/professor/enroll")}
                    icon={UserPlus}
                    label="Enroll"
                    disabled={cameraReleasing}
                  />
                  <NavBtn
                    active={location.pathname === "/professor/gallery"}
                    onClick={() => handlePageChange("/professor/gallery")}
                    icon={Users}
                    label="Gallery"
                    disabled={cameraReleasing}
                  />
                </>
              )}
              {!isProfessor && (
                <NavBtn
                  active={location.pathname === "/student"}
                  onClick={() => handlePageChange("/student")}
                  icon={ScanFace}
                  label="Student"
                  disabled={cameraReleasing}
                />
              )}
            </nav>
            {auth && (
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 rounded-xl hover:bg-slate-200"
              >
                Logout
              </button>
            )}
          </div>
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
          <Routes>
            <Route
              path="/"
              element={<HomePage onGoProfessor={() => handlePageChange("/professor")} onGoStudent={() => handlePageChange("/student")} />}
            />

            {isProfessor ? (
              <>
                <Route path="/professor" element={<ProfessorDashboard />} />
                <Route path="/professor/sessions/:sessionId" element={<ProfessorDashboard />} />
                <Route path="/professor/enroll" element={<Enrollment />} />
                <Route path="/professor/gallery" element={<StudentGallery />} />
              </>
            ) : (
              <Route path="/professor/*" element={<Navigate to="/" replace />} />
            )}

            <Route path="/student" element={<StudentAttendancePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
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

const HomePage = ({ onGoProfessor, onGoStudent }) => {
  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="w-full max-w-3xl bg-white rounded-3xl shadow-sm border border-slate-200 p-8 md:p-10">
        <h2 className="text-3xl md:text-4xl font-black tracking-tight text-slate-900">
          Welcome to BIO<span className="text-indigo-600">ATTEND</span>
        </h2>
        <p className="mt-3 text-slate-600">
          Choose your portal to continue.
        </p>

        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={onGoProfessor}
            className="group flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-6 py-5 hover:bg-slate-100 transition"
          >
            <div className="text-left">
              <div className="text-sm font-bold text-slate-500 uppercase tracking-wider">
                Professor
              </div>
              <div className="mt-1 text-lg font-black text-slate-900">
                Manage sessions & enrollment
              </div>
            </div>
            <GraduationCap className="w-7 h-7 text-indigo-600 group-hover:scale-105 transition-transform" />
          </button>

          <button
            onClick={onGoStudent}
            className="group flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-6 py-5 hover:bg-slate-100 transition"
          >
            <div className="text-left">
              <div className="text-sm font-bold text-slate-500 uppercase tracking-wider">
                Student
              </div>
              <div className="mt-1 text-lg font-black text-slate-900">
                Mark attendance
              </div>
            </div>
            <ScanFace className="w-7 h-7 text-indigo-600 group-hover:scale-105 transition-transform" />
          </button>
        </div>
      </div>
    </div>
  );
};

const LoginCard = ({ onLogin }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    await onLogin(username, password);
    setLoading(false);
  };

  return (
    <form onSubmit={submit} className="w-full max-w-md bg-white rounded-2xl shadow p-8 space-y-4">
      <h2 className="text-2xl font-black text-slate-800">Login</h2>
      <p className="text-sm text-slate-500">
        Use seeded accounts: `professor1` / `prof123` or `student1` / `stud123`
      </p>
      <input
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        className="w-full px-4 py-3 border rounded-xl"
        placeholder="Username"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full px-4 py-3 border rounded-xl"
        placeholder="Password"
      />
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 bg-indigo-600 text-white rounded-xl font-bold disabled:opacity-50"
      >
        {loading ? "Signing in..." : "Sign In"}
      </button>
    </form>
  );
};

export default App;
