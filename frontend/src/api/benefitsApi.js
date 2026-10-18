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

// Downloads the application-worksheet PDF for a finished match.
export async function exportWorksheetPdf(profile, result) {
  const { data } = await api.post(
    "/export/pdf",
    { profile, result },
    { responseType: "blob" },
  );
  const url = URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "civis-worksheet.pdf";
  a.click();
  // Revoking right away can cancel the download in some browsers.
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

// "What if my income changes?": the rules-only matcher at a grid of incomes.
export async function getIncomeScenarios(profile) {
  const { data } = await api.post("/income-scenarios", profile);
  return data;
}

// Ask Civis: a question answered from the program records, with sources.
export async function askCivis({ question, history = [], profile }) {
  const { data } = await api.post("/ask", { question, history, ...(profile ? { profile } : {}) });
  return data;
}
