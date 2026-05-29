import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8010",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("datavault_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function registerAccount(payload) {
  const { data } = await api.post("/auth/register", payload);
  return data;
}

export async function loginAccount(payload) {
  const { data } = await api.post("/auth/login", payload);
  return data;
}

export async function fetchProjects() {
  const { data } = await api.get("/projects");
  return data;
}

export async function createProject(payload) {
  const { data } = await api.post("/projects", payload);
  return data;
}

export async function fetchFiles(projectId) {
  const { data } = await api.get(`/files/${projectId}`);
  return data;
}

export async function uploadProjectFile(projectId, file, purpose) {
  const formData = new FormData();
  formData.append("file", file);
  const endpoint = purpose === "prototype_pdf" ? "prototype-pdf" : "dataset";
  const { data } = await api.post(`/files/${projectId}/${endpoint}`, formData);
  return data;
}

export async function getSummary(projectId) {
  const { data } = await api.get(`/workspace-analytics/${projectId}/summary`);
  return data;
}

export async function askQuestion(projectId, question) {
  const { data } = await api.post("/workspace-analytics/ask", { project_id: projectId, question });
  return data;
}

export async function fetchChats(projectId) {
  const { data } = await api.get(`/workspace-analytics/${projectId}/chats`);
  return data;
}

export async function generateReport(projectId) {
  const { data } = await api.post(`/analytics/${projectId}/report`);
  return data;
}
