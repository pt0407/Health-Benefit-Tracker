import axios from "axios";

// Request/response shapes are defined in backend/models/ (shared contract).
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "/api" });

export async function matchBenefits(profile) {
  const { data } = await api.post("/match", profile);
  return data;
}

export async function listPrograms() {
  const { data } = await api.get("/programs");
  return data;
}

export async function getProgram(programId) {
  const { data } = await api.get(`/programs/${programId}`);
  return data;
}

export async function checkInsurance(profile) {
  const { data } = await api.post("/insurance-check", profile);
  return data;
}
