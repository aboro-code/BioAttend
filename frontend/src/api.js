import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
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
