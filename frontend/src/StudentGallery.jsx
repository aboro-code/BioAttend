import React, { useEffect, useState } from "react";
import axios from "axios";
import { RefreshCw } from "lucide-react";

const StudentGallery = () => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchStudents = async () => {
    setLoading(true);
    try {
      const res = await axios.get("http://localhost:8000/students");
      setStudents(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        fetchStudents();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  // Helper function to extract filename from photo_url
  const getPhotoUrl = (photoUrl) => {
    if (!photoUrl) {
      return null;
    }

    // Handle both formats:
    // "student-photos/abc-123.jpg" → "abc-123.jpg"
    // "abc-123.jpg" → "abc-123.jpg"
    const filename = photoUrl.includes("/")
      ? photoUrl.split("/").pop() // Get last part after /
      : photoUrl; // Already just filename

    return `http://localhost:8000/photo/${filename}`;
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">
          Known Faces Gallery ({students.length})
        </h2>
        <button
          onClick={fetchStudents}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-all disabled:opacity-50 active:scale-95"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-6">
        {students.length === 0 ? (
          <div className="col-span-full text-center py-10 text-gray-400">
            No students enrolled yet
          </div>
        ) : (
          students.map((student) => (
            <div
              key={student.id}
              className="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100 hover:shadow-md transition-shadow"
            >
              <img
                src={getPhotoUrl(student.photo_url)}
                alt={student.name}
                className="w-full h-48 object-cover bg-gray-100"
                onError={(e) => {
                  console.error(
                    `Failed to load photo for ${student.name}:`,
                    student.photo_url,
                  );
                  e.target.src =
                    "https://via.placeholder.com/200x200?text=No+Photo";
                }}
              />
              <div className="p-4 text-center">
                <p className="font-bold text-gray-800">{student.name}</p>
                <p className="text-xs text-gray-400 mt-1 uppercase tracking-widest">
                  Enrolled
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default StudentGallery;
