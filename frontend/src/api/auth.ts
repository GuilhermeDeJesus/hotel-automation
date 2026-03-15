import axios from "axios";

export async function registerUser({ email, password, hotel_id }: { email: string; password: string; hotel_id?: string }) {
  try {
    const res = await axios.post("/api/auth/register", { email, password, hotel_id });
    return res.data;
  } catch (error: any) {
    const message = error.response?.data?.detail || error.response?.data?.message || "Erro ao registrar usuário";
    throw new Error(message);
  }
}

export async function loginUser({ email, password }: { email: string; password: string }) {
  try {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const res = await axios.post(`${apiUrl}/api/auth/login`, { email, password });
    return res.data.token;
  } catch (error: any) {
    const message = error.response?.data?.detail || error.response?.data?.message || "Erro ao fazer login";
    throw new Error(message);
  }
}
