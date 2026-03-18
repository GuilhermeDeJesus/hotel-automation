export function logoutUser() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("selected_hotel_id");
  window.location.href = "/login";
}

export function getAuthToken(): string | null {
  return localStorage.getItem("auth_token");
}

export function isAuthenticated(): boolean {
  return !!getAuthToken();
}
