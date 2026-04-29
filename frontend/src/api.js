import axios from "axios";

const fromEnv = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;

// For EC2 Deployment with ngrok frontend and IP-based backend
export const API_BASE_URL = "http://16.176.24.242:8000";

const API = axios.create({
  baseURL: API_BASE_URL,
});

export const cameraAPI = `${API.defaults.baseURL}/camera`;
export const studentAPI = `${API.defaults.baseURL}/students`;
export const attendanceAPI = `${API.defaults.baseURL}/attendance`;

export const setAuthToken = (token) => {
  if (token) {
    API.defaults.headers.common.Authorization = `Bearer ${token}`;
    axios.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete API.defaults.headers.common.Authorization;
    delete axios.defaults.headers.common.Authorization;
  }
};

export default API;
