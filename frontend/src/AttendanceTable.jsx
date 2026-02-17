import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { Download, UserCheck, Activity, VideoOff, Video, ChevronDown } from "lucide-react";
import toast from "react-hot-toast";

const AttendanceTable = () => {
  const [logs, setLogs] = useState([]);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [streamUrl, setStreamUrl] = useState("");
  const [showExportMenu, setShowExportMenu] = useState(false);
  const prevLogsLength = useRef(0);
  const imgRef = useRef(null);

  const startStream = () => {
    setStreamUrl(`http://localhost:8000/camera/video_feed?t=${Date.now()}`);
    setIsCameraActive(true);
  };

  const stopStream = async () => {
    setIsCameraActive(false);
    setStreamUrl("");
    if (imgRef.current) {
      imgRef.current.src = "";
    }
    try {
      await axios.post("http://localhost:8000/camera/release");
      toast.success("Camera released");
    } catch (error) {
      console.error("Camera release error:", error);
    }
  };

  const handleExport = (format) => {
    const url = `http://localhost:8000/attendance/export/${format}`;
    window.open(url, '_blank');
    setShowExportMenu(false);
    toast.success(`Downloading ${format.toUpperCase()} report...`);
  };

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await axios.get(
          "http://localhost:8000/attendance/today",
        );
        const newLogs = response.data;

        if (newLogs.length > prevLogsLength.current) {
          if (prevLogsLength.current !== 0) {
            const latestEntry = newLogs[0];
            toast.success(`Verified: ${latestEntry.name}`, {
              icon: "👤",
              style: {
                borderRadius: "10px",
                background: "#333",
                color: "#fff",
              },
            });
          }
          prevLogsLength.current = newLogs.length;
        }
        setLogs(newLogs);
      } catch (error) {
        console.error("Fetch error:", error);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);

    return () => {
      clearInterval(interval);
      stopStream();
    };
  }, []);

  return (
    <div className="p-6 space-y-8 animate-in fade-in duration-700">
      {/* LIVE MONITOR */}
      <div className="mb-8 overflow-hidden rounded-3xl border-4 border-white shadow-2xl relative bg-slate-900 aspect-video max-w-3xl mx-auto flex items-center justify-center">
        {isCameraActive ? (
          <>
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-red-600/80 backdrop-blur-md px-3 py-1 rounded-full">
              <div className="h-2 w-2 rounded-full bg-white animate-pulse" />
              <span className="text-[10px] font-black text-white uppercase tracking-tighter">
                Live Monitor
              </span>
            </div>
            <button
              onClick={stopStream}
              className="absolute top-4 right-4 z-10 p-2 bg-red-600/80 hover:bg-red-700 backdrop-blur-md rounded-full transition-all"
            >
              <VideoOff className="w-5 h-5 text-white" />
            </button>
            <img
              ref={imgRef}
              src={streamUrl}
              alt="Live AI Feed"
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.onerror = null;
                setIsCameraActive(false);
              }}
            />
          </>
        ) : (
          <div className="text-center p-10">
            <VideoOff className="w-12 h-12 text-slate-700 mx-auto mb-4" />
            <p className="text-slate-500 font-medium mb-4">Camera Stopped</p>
            <button
              onClick={startStream}
              className="flex items-center gap-2 mx-auto px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-all"
            >
              <Video className="w-5 h-5" />
              Start Live Monitoring
            </button>
          </div>
        )}
      </div>

      {/* STATS */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <StatCard
          label="Detections"
          val={logs.length}
          icon={Activity}
          color="text-blue-600"
          bg="bg-blue-50"
        />
        <StatCard
          label="Unique Faces"
          val={new Set(logs.map((l) => l.name)).size}
          icon={UserCheck}
          color="text-emerald-600"
          bg="bg-emerald-50"
        />
        <StatCard
          label="System Status"
          val={isCameraActive ? "Active" : "Stopped"}
          icon={Activity}
          color={isCameraActive ? "text-emerald-600" : "text-slate-600"}
          bg={isCameraActive ? "bg-emerald-50" : "bg-slate-50"}
        />
      </div>

      {/* TABLE */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm ">
        <div className="px-6 py-5 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-center gap-4">
          <h2 className="text-lg font-bold text-slate-800">
            Real-time Activity
          </h2>
          
          {/* Export Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-2 bg-slate-900 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-slate-800 transition-all active:scale-95 shadow-lg shadow-slate-200"
            >
              <Download className="w-4 h-4" /> 
              Export Report
              <ChevronDown className={`w-4 h-4 transition-transform ${showExportMenu ? 'rotate-180' : ''}`} />
            </button>
            
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden z-50">
                <div className="py-1">
                  <button
                    onClick={() => handleExport('csv')}
                    className="w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors flex items-center gap-3 group"
                  >
                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center group-hover:bg-green-200 transition-colors">
                      <Download className="w-5 h-5 text-green-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800">CSV Format</p>
                      <p className="text-xs text-slate-500">Simple spreadsheet</p>
                    </div>
                  </button>
                  
                  <button
                    onClick={() => handleExport('excel')}
                    className="w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors flex items-center gap-3 group"
                  >
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                      <Download className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800">Excel Format</p>
                      <p className="text-xs text-slate-500">Formatted with styles</p>
                    </div>
                  </button>
                  
                  <button
                    onClick={() => handleExport('excel-detailed')}
                    className="w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors flex items-center gap-3 group"
                  >
                    <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
                      <Download className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800">Detailed Report</p>
                      <p className="text-xs text-slate-500">With statistics</p>
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-slate-50/50">
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Student
                </th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Status
                </th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-widest text-right">
                  Timestamp
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.length === 0 ? (
                <tr>
                  <td
                    colSpan="3"
                    className="py-10 text-center text-slate-400 italic"
                  >
                    No detections recorded today.
                  </td>
                </tr>
              ) : (
                logs.map((log, i) => (
                  <tr
                    key={i}
                    className="hover:bg-slate-50/80 transition-colors group"
                  >
                    <td className="py-4 px-6 font-semibold text-slate-700">
                      {log.name}
                    </td>
                    <td className="py-4 px-6">
                      <span className="inline-flex items-center gap-1.5 py-1 px-3 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700 uppercase">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />{" "}
                        {log.status}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-slate-400 text-right font-mono text-xs">
                      {log.time}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ label, val, icon: Icon, color, bg }) => (
  <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">
          {label}
        </p>
        <p className="text-3xl font-bold text-slate-900 mt-1">{val}</p>
      </div>
      <div className={`${bg} ${color} p-3 rounded-xl`}>
        <Icon className="w-6 h-6" />
      </div>
    </div>
  </div>
);

export default AttendanceTable;
