import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import API from "./api";
import { Clock, Users, MapPin, X, RefreshCw, Download, Play, History, ArrowRight } from "lucide-react";
import toast from "react-hot-toast";

const ProfessorDashboard = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null); // The active session details
  const [loading, setLoading] = useState(false);
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  
  // Dashboard list state
  const [mySessions, setMySessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  const [formData, setFormData] = useState({
    course_name: "",
    duration_hours: 2,
    classroom_location: "",
    classroom_lat: null,
    classroom_lon: null,
    geofence_radius: 50,
  });

  // Fetch session details if sessionId is in URL
  useEffect(() => {
    if (!sessionId) {
      setSession(null);
      setAttendanceRecords([]);
      return;
    }

    const fetchSessionDetails = async () => {
      try {
        const res = await API.get(`/sessions/${sessionId}/details`);
        setSession(res.data.session);
        setAttendanceRecords(res.data.attendance_records);
      } catch (err) {
        console.error("Attendance fetch error:", err);
        toast.error("Failed to load session details");
        navigate("/professor");
      }
    };

    fetchSessionDetails();
    const interval = setInterval(fetchSessionDetails, 5000);

    return () => clearInterval(interval);
  }, [sessionId, navigate]);

  // Fetch "My Sessions" if on the dashboard root
  useEffect(() => {
    if (sessionId) return;

    const fetchMySessions = async () => {
      setLoadingSessions(true);
      try {
        const res = await API.get("/sessions/mine");
        setMySessions(res.data);
      } catch (err) {
        console.error("Failed to fetch sessions:", err);
        toast.error("Failed to load your sessions");
      } finally {
        setLoadingSessions(false);
      }
    };

    fetchMySessions();
  }, [sessionId]);

  const getCurrentLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocation not supported by your browser");
      return;
    }

    toast.loading("Getting your location...");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        toast.dismiss();
        setFormData((prev) => ({
          ...prev,
          classroom_lat: position.coords.latitude,
          classroom_lon: position.coords.longitude,
        }));
        toast.success("Location captured!");
      },
      (error) => {
        toast.dismiss();
        toast.error("Failed to get location: " + error.message);
      },
      { enableHighAccuracy: true },
    );
  };

  const createSession = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await API.post("/sessions/create", formData);

      if (response.data.success) {
        toast.success("Session created successfully!");
        navigate(`/professor/sessions/${response.data.session_id}`);
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      toast.error(
        "Failed to create session: " +
          (error.response?.data?.detail || error.message),
      );
    } finally {
      setLoading(false);
    }
  };

  const closeSession = async () => {
    if (!window.confirm("Are you sure you want to close this session?")) return;

    try {
      await API.post(`/sessions/${session.session_id}/close`);
      toast.success("Session closed");
      navigate("/professor");
    } catch (error) {
      toast.error("Failed to close session");
    }
  };

  const calculateTimeRemaining = (sessionData) => {
    if (!sessionData) return "";

    const expiresAt = new Date(sessionData.expires_at);
    const now = new Date();
    const diff = expiresAt - now;

    if (diff <= 0 || !sessionData.is_active) return "Closed";

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    return `${hours}h ${minutes}m`;
  };

  const downloadFile = async (url, filename) => {
    try {
      toast.loading(`Preparing ${filename}...`);
      const response = await API.get(url, { responseType: "blob" });
      toast.dismiss();

      const blob = new Blob([response.data], {
        type: response.headers["content-type"],
      });
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success(`${filename} downloaded!`);
    } catch (error) {
      toast.dismiss();
      toast.error("Failed to download file");
    }
  };

  if (sessionId && session) {
    // Active / Detail session view
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-50 p-8">
        <div className="max-w-7xl mx-auto">
          <button 
            onClick={() => navigate("/professor")}
            className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800 font-medium mb-4 transition-colors"
          >
            &larr; Back to Dashboard
          </button>
          
          {/* Header */}
          <div className="bg-white rounded-2xl shadow-lg p-6 mb-6 border-l-4 border-indigo-500">
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-3xl font-bold text-gray-900">
                    {session.course_name}
                  </h1>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${session.is_active && new Date(session.expires_at) > new Date() ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                    {session.is_active && new Date(session.expires_at) > new Date() ? 'Active' : 'Closed'}
                  </span>
                </div>
                <p className="text-gray-600 mt-1">
                  Professor: {session.professor_name} 
                  {session.classroom_location && ` • Location: ${session.classroom_location}`}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Session ID: {session.session_id}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    const name = session.course_name || "attendance";
                    downloadFile(
                      `/attendance/export/csv?session_id=${session.session_id}`,
                      `attendance_${name.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.csv`,
                    );
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  CSV
                </button>
                <button
                  onClick={() => {
                    const name = session.course_name || "attendance";
                    downloadFile(
                      `/attendance/export/excel?session_id=${session.session_id}`,
                      `attendance_${name.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.xlsx`,
                    );
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Excel
                </button>
                {session.is_active && (
                  <button
                    onClick={closeSession}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                  >
                    <X className="w-4 h-4" />
                    Close
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <div className={`flex items-center gap-3 p-4 rounded-xl ${session.is_active ? 'bg-blue-50' : 'bg-gray-50'}`}>
                <Clock className={`w-6 h-6 ${session.is_active ? 'text-blue-600' : 'text-gray-500'}`} />
                <div>
                  <p className="text-sm text-gray-600">Status / Time</p>
                  <p className="text-lg font-bold text-gray-900">
                    {calculateTimeRemaining(session)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 p-4 bg-green-50 rounded-xl">
                <Users className="w-6 h-6 text-green-600" />
                <div>
                  <p className="text-sm text-gray-600">Students Present</p>
                  <p className="text-lg font-bold text-gray-900">
                    {attendanceRecords.length}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 p-4 bg-purple-50 rounded-xl">
                <MapPin className="w-6 h-6 text-purple-600" />
                <div>
                  <p className="text-sm text-gray-600">Geofence Status</p>
                  <p className="text-lg font-bold text-gray-900">
                    Active
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid-cols-1 lg:grid-cols-2 gap-6">
            {session.is_active && (
                <>
                    <p className="text-sm text-gray-600 mb-2 font-medium">STUDENT ATTENDANCE OTP</p>
                    <div className="text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600 tracking-widest font-mono mb-6 drop-shadow-sm">
                    {session.otp || "N/A"}
                    </div>
                </>
            )}
            
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  Attendance Log
                </h2>
                {session.is_active && (
                  <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin-slow" />
                )}
              </div>

              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                {attendanceRecords.length === 0 ? (
                  <div className="text-center py-12 text-gray-400">
                    <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p>No students marked yet</p>
                    {session.is_active && (
                        <p className="text-sm mt-1">Waiting for first attendance...</p>
                    )}
                  </div>
                ) : (
                  attendanceRecords.map((record, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition-colors rounded-xl border border-slate-100"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-bold">
                          {idx + 1}
                        </div>
                        <div>
                          <p className="font-bold text-gray-900">
                            {record.student_name}
                          </p>
                          <p className="text-xs text-gray-500 font-medium tracking-wide">
                            {new Date(record.marked_at).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                      {record.location_score !== null && (
                        <div className="text-right">
                          <p className="text-sm font-bold text-indigo-700">
                            Score: {record.location_score}
                          </p>
                          <p className="text-xs text-gray-500 uppercase tracking-widest">
                            {record.verification_method || 'Verified'}
                          </p>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Dashboard / Session List View
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-50 p-8">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column - Create Session Form */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-2xl shadow-xl p-8 sticky top-24">
            <div className="flex items-center gap-2 mb-2">
                <Play className="text-indigo-600 w-6 h-6" />
                <h1 className="text-2xl font-bold text-gray-900">
                New Session
                </h1>
            </div>
            <p className="text-gray-500 text-sm mb-8">
              Configure and start a new attendance session
            </p>

            <form onSubmit={createSession} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Course Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.course_name}
                  onChange={(e) =>
                    setFormData({ ...formData, course_name: e.target.value })
                  }
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all shadow-sm"
                  placeholder="e.g. Data Structures"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Duration (hr) *
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    max="8"
                    value={formData.duration_hours}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        duration_hours: parseInt(e.target.value),
                      })
                    }
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Geofence (m)
                  </label>
                  <input
                    type="number"
                    min="10"
                    max="500"
                    value={formData.geofence_radius}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        geofence_radius: parseInt(e.target.value),
                      })
                    }
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all shadow-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Location Name (Optional)
                </label>
                <input
                  type="text"
                  value={formData.classroom_location}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      classroom_location: e.target.value,
                    })
                  }
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all shadow-sm"
                  placeholder="e.g. Room 301"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-sm font-medium text-gray-700">
                    GPS Coordinates
                  </label>
                  <button
                    type="button"
                    onClick={getCurrentLocation}
                    className="text-xs text-indigo-600 hover:text-indigo-800 font-bold uppercase tracking-wider bg-indigo-50 px-2 py-1 rounded"
                  >
                    Use current
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <input
                    type="number"
                    step="0.000001"
                    value={formData.classroom_lat || ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        classroom_lat: e.target.value
                          ? parseFloat(e.target.value)
                          : null,
                      })
                    }
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 text-sm shadow-sm"
                    placeholder="Latitude"
                  />
                  <input
                    type="number"
                    step="0.000001"
                    value={formData.classroom_lon || ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        classroom_lon: e.target.value
                          ? parseFloat(e.target.value)
                          : null,
                      })
                    }
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 text-sm shadow-sm"
                    placeholder="Longitude"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-4 bg-gradient-to-r from-indigo-600 to-blue-600 text-white font-bold rounded-xl hover:from-indigo-700 hover:to-blue-700 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all flex justify-center items-center gap-2 mt-4"
              >
                {loading ? "Starting..." : "Start Attendance"}
                <ArrowRight className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>

        {/* Right Column - My Sessions */}
        <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between bg-white px-6 py-4 rounded-2xl shadow-sm border border-slate-100">
                <div className="flex items-center gap-3 text-slate-800">
                    <History className="w-6 h-6 text-indigo-600" />
                    <h2 className="text-xl font-bold">My Sessions</h2>
                </div>
                <div className="text-sm font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
                    {mySessions.length} total
                </div>
            </div>

            {loadingSessions ? (
                <div className="flex justify-center py-12">
                    <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
                </div>
            ) : mySessions.length === 0 ? (
                <div className="bg-white rounded-2xl shadow-sm border border-dashed border-slate-300 p-12 text-center text-slate-500">
                    <Clock className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-800 mb-1">No sessions found</h3>
                    <p>Create your first session using the form on the left.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {mySessions.map((ms) => {
                        const isActive = ms.is_active && new Date(ms.expires_at) > new Date();
                        return (
                            <div 
                                key={ms.session_id} 
                                onClick={() => navigate(`/professor/sessions/${ms.session_id}`)}
                                className={`bg-white rounded-2xl p-5 cursor-pointer border-2 transition-all hover:-translate-y-1 hover:shadow-md ${isActive ? 'border-indigo-100 shadow-sm' : 'border-slate-100 opacity-90'}`}
                            >
                                <div className="flex justify-between items-start mb-3">
                                    <h3 className="text-lg font-bold text-slate-900 truncate pr-2">{ms.course_name}</h3>
                                    {isActive ? (
                                        <span className="shrink-0 flex h-3 w-3 relative">
                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                                        </span>
                                    ) : (
                                        <span className="shrink-0 h-3 w-3 rounded-full bg-slate-300"></span>
                                    )}
                                </div>
                                <div className="space-y-2 mb-4 text-sm">
                                    <div className="flex items-center gap-2 text-slate-500">
                                        <Clock className="w-4 h-4" />
                                        <span>{new Date(ms.expires_at).toLocaleDateString()}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-slate-500">
                                        <Users className="w-4 h-4" />
                                        <span>{ms.total_students_marked || 0} marked</span>
                                    </div>
                                </div>
                                <div className="pt-4 border-t border-slate-100">
                                    <span className={`text-xs font-bold uppercase tracking-wider ${isActive ? 'text-indigo-600' : 'text-slate-400'}`}>
                                        {isActive ? 'View Live Session \u2192' : 'View Details \u2192'}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
      </div>
    </div>
  );
};

export default ProfessorDashboard;
