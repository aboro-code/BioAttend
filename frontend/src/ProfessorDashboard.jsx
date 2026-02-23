import React, { useState, useEffect } from "react";
import axios from "axios";
import QRCode from "react-qr-code";
import { Clock, Users, MapPin, Wifi, X, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";

const ProfessorDashboard = () => {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [qrToken, setQrToken] = useState(null);
  const [formData, setFormData] = useState({
    course_name: "",
    professor_name: "",
    duration_hours: 2,
    classroom_location: "",
    classroom_lat: null,
    classroom_lon: null,
    geofence_radius: 50,
    allowed_wifi_ssid: "",
  });

  // Auto-refresh QR token every 30 seconds
  useEffect(() => {
    if (!session) return;

    const fetchQR = async () => {
      try {
        const res = await axios.get(
          `http://localhost:8000/sessions/${session.session_id}/qr-token`,
        );
        setQrToken(res.data);
      } catch (err) {
        console.error("QR refresh error:", err);
      }
    };

    fetchQR();
    const interval = setInterval(fetchQR, 30000);

    return () => clearInterval(interval);
  }, [session]);

  // Auto-refresh attendance list every 5 seconds
  useEffect(() => {
    if (!session) return;

    const fetchAttendance = async () => {
      try {
        const res = await axios.get(
          `http://localhost:8000/sessions/${session.session_id}/details`,
        );
        setAttendanceRecords(res.data.attendance_records);
      } catch (err) {
        console.error("Attendance fetch error:", err);
      }
    };

    fetchAttendance();
    const interval = setInterval(fetchAttendance, 5000);

    return () => clearInterval(interval);
  }, [session]);

  // Get current location
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
      const response = await axios.post(
        "http://localhost:8000/sessions/create",
        formData,
      );

      if (response.data.success) {
        setSession(response.data);
        toast.success("Session created successfully!");
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
      await axios.post(
        `http://localhost:8000/sessions/${session.session_id}/close`,
      );
      toast.success("Session closed");
      setSession(null);
      setAttendanceRecords([]);
      setQrToken(null);
    } catch (error) {
      toast.error("Failed to close session");
    }
  };

  const calculateTimeRemaining = () => {
    if (!session) return "";

    const expiresAt = new Date(session.expires_at);
    const now = new Date();
    const diff = expiresAt - now;

    if (diff <= 0) return "Expired";

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    return `${hours}h ${minutes}m`;
  };

  if (session) {
    // Active session view
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-50 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
            <div className="flex justify-between items-start">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  {session.course_name || formData.course_name}
                </h1>
                <p className="text-gray-600 mt-1">
                  Professor: {session.professor_name || formData.professor_name}
                </p>
              </div>
              <button
                onClick={closeSession}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                <X className="w-4 h-4" />
                Close Session
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-xl">
                <Clock className="w-6 h-6 text-blue-600" />
                <div>
                  <p className="text-sm text-gray-600">Time Remaining</p>
                  <p className="text-lg font-bold text-gray-900">
                    {calculateTimeRemaining()}
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
                  <p className="text-sm text-gray-600">Geofence Radius</p>
                  <p className="text-lg font-bold text-gray-900">
                    {formData.geofence_radius}m
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* QR Code Section */}
            <div className="bg-white rounded-2xl shadow-lg p-8">
              <h2 className="text-xl font-bold text-gray-900 mb-6 text-center">
                Scan to Mark Attendance
              </h2>

              {qrToken && (
                <div className="space-y-6">
                  <div className="bg-white p-6 rounded-xl border-4 border-indigo-200 flex justify-center">
                    <QRCode value={qrToken.qr_url} size={280} />
                  </div>

                  <div className="text-center">
                    <p className="text-sm text-gray-600 mb-2">
                      Or enter OTP manually:
                    </p>
                    <div className="text-5xl font-bold text-indigo-600 tracking-wider font-mono">
                      {session.otp}
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      QR refreshes every 30 seconds
                    </p>
                  </div>

                  {formData.allowed_wifi_ssid && (
                    <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
                      <Wifi className="w-5 h-5 text-blue-600" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Required WiFi:
                        </p>
                        <p className="text-sm text-gray-600">
                          {formData.allowed_wifi_ssid}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Attendance List */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  Live Attendance
                </h2>
                <RefreshCw className="w-5 h-5 text-gray-400 animate-spin" />
              </div>

              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {attendanceRecords.length === 0 ? (
                  <div className="text-center py-12 text-gray-400">
                    <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No students marked yet</p>
                    <p className="text-sm mt-1">
                      Waiting for first attendance...
                    </p>
                  </div>
                ) : (
                  attendanceRecords.map((record, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-4 bg-green-50 rounded-lg border border-green-200"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">
                          {idx + 1}
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900">
                            {record.student_name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(record.marked_at).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                      {record.location_score && (
                        <div className="text-right">
                          <p className="text-sm font-medium text-green-700">
                            Score: {record.location_score}
                          </p>
                          <p className="text-xs text-gray-500">
                            {record.verification_method}
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

  // Session creation form
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-50 p-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Create Attendance Session
          </h1>
          <p className="text-gray-600 mb-8">
            Configure your attendance session settings
          </p>

          <form onSubmit={createSession} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Course Name *
              </label>
              <input
                type="text"
                required
                value={formData.course_name}
                onChange={(e) =>
                  setFormData({ ...formData, course_name: e.target.value })
                }
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="e.g., Data Structures and Algorithms"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Professor Name *
              </label>
              <input
                type="text"
                required
                value={formData.professor_name}
                onChange={(e) =>
                  setFormData({ ...formData, professor_name: e.target.value })
                }
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="e.g., Dr. Sarah Johnson"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Duration (hours) *
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
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Geofence Radius (m)
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
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Classroom Location
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
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="e.g., Room 301, CS Building"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  GPS Coordinates (Optional)
                </label>
                <button
                  type="button"
                  onClick={getCurrentLocation}
                  className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  Use Current Location
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
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
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
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="Longitude"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Required WiFi SSID (Optional)
              </label>
              <input
                type="text"
                value={formData.allowed_wifi_ssid}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    allowed_wifi_ssid: e.target.value,
                  })
                }
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="e.g., UNIVERSITY_WIFI"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loading ? "Creating Session..." : "Start Attendance Session"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ProfessorDashboard;
