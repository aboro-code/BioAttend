import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
});

export const cameraAPI = `${API.defaults.baseURL}/camera`;
export const studentAPI = `${API.defaults.baseURL}/students`;
export const attendanceAPI = `${API.defaults.baseURL}/attendance`;

export default API;
