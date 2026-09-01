const API_BASE = import.meta.env.VITE_API_BASE_URL;

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// ---- Auth ----

export function registerUser({ username, email, password, vehicleClass = "2W", vehicleRangeKm = 80 }) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      username,
      email,
      password,
      vehicle_class: vehicleClass,
      vehicle_range_km: vehicleRangeKm,
    }),
  });
  // returns { access_token, token_type }
}

// ---- Session persistence ----
// Call this once on app load to check for a saved session.
export function getSavedSession() {
  const raw = localStorage.getItem("chargesure_session");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveSession({ token, email, username }) {
  localStorage.setItem(
    "chargesure_session",
    JSON.stringify({ token, email, username })
  );
}

export function clearSession() {
  localStorage.removeItem("chargesure_session");
}

// ---- Profile ----
// PATCH /auth/me needs to exist on the backend and accept { username }.
// Until it does, callers should catch the error and fall back to a
// local-only update (see App.jsx's handleSaveUsername).
export function updateUsername(username, token) {
  return request("/auth/me", {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ username }),
  });
}

export async function loginUser({ email, password }) {
  // /auth/login expects form-encoded data (OAuth2PasswordRequestForm), not JSON
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Login failed");
  }
  return res.json(); // { access_token, token_type }
}

// ---- Chargers ----

export function getNearbyChargers(lat, lng, radiusKm = 5, vehicleClass) {
  const params = new URLSearchParams({ lat, lng, radius_km: radiusKm });
  if (vehicleClass) params.append("vehicle_class", vehicleClass);
  return request(`/chargers/nearby?${params.toString()}`);
}

// ---- Routes ----

export function planRoute(
  { originLat, originLng, destLat, destLng, vehicleClass, vehicleRangeKm, currentChargePct = 100 },
  token
) {
  return request("/routes/plan", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: JSON.stringify({
      origin_lat: originLat,
      origin_lng: originLng,
      destination_lat: destLat,
      destination_lng: destLng,
      vehicle_class: vehicleClass,
      vehicle_range_km: vehicleRangeKm,
      current_charge_pct: currentChargePct,
    }),
  });
}

// ---- Bookings ----

export function createBooking({ chargerId, tripId, slotStart, slotEnd }, token) {
  return request("/bookings", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      charger_id: chargerId,
      trip_id: tripId,
      slot_start: slotStart,
      slot_end: slotEnd,
    }),
  });
}