import React, { useEffect, useState } from "react";
import axios from "axios";
import { RefreshCw, Trash2 } from "lucide-react";
import toast from "react-hot-toast";

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
      toast.error("Failed to load students");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete ${name}?`)) return;

    try {
      const res = await axios.delete(`http://localhost:8000/students/${id}`);
      if (res.data.success) {
        toast.success(`${name} deleted`);
        setStudents((prev) => prev.filter((s) => s.id !== id));
      } else {
        toast.error(res.data.message);
      }
    } catch (err) {
      toast.error("Delete failed");
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const getPhotoUrl = (photoUrl) => {
    if (!photoUrl) return null;
    // Standardize: If it has student-photos/ prefix, strip it.
    const filename = photoUrl.includes("/")
      ? photoUrl.split("/").pop()
      : photoUrl;
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
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-6">
        {students.length === 0 && !loading ? (
          <div className="col-span-full text-center py-10 text-gray-400 font-medium">
            No students enrolled yet
          </div>
        ) : (
          students.map((student) => (
            <div
              key={student.id}
              className="group relative bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100 hover:shadow-md transition-all"
            >
              {/* Delete Button - Visible on Hover */}
              <button
                onClick={() => handleDelete(student.id, student.name)}
                className="absolute top-2 right-2 p-2 bg-red-50 text-red-600 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-100 z-10"
              >
                <Trash2 size={16} />
              </button>

              <img
                src={getPhotoUrl(student.photo_url)}
                alt={student.name}
                className="w-full h-48 object-cover bg-gray-100"
                onError={(e) => {
                  e.target.src = `https://ui-avatars.com/api/?name=${student.name}&background=random`;
                }}
              />

              <div className="p-4">
                <p className="font-bold text-gray-800 truncate">
                  {student.name}
                </p>
                <p className="text-[10px] text-gray-400 mt-1 uppercase tracking-tighter">
                  ID: {student.id.substring(0, 8)}...
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
