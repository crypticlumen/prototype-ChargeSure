import { useEffect, useState } from 'react'
import L from 'leaflet'
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

// FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';


const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: "\u{1F4CA}" },
  { key: "route", label: "Plan Route", icon: "\u{1F5FA}\uFE0F" },
  { key: "vehicles", label: "Vehicles", icon: "\u{1F697}" },
  { key: "bookings", label: "Bookings", icon: "\u{1F4C5}" },
  { key: "settings", label: "Settings", icon: "\u2699\uFE0F" },
];

const VEHICLE_TYPES = ["2-Wheeler", "3-Wheeler", "4-Wheeler"];
const CONNECTOR_TYPES = ["Type 2", "CCS2", "CHAdeMO", "Bharat AC001", "Bharat DC001"];

const EMPTY_VEHICLE_FORM = {
  brand: "",
  model: "",
  regNumber: "",
  year: "",
  mileage: "",
  type: VEHICLE_TYPES[0],
  battery: 80,
  range: 100,
  capacity: 3.5,
  connector: CONNECTOR_TYPES[0],
};

// Normalizes parsed-file keys ("Reg Number", "reg_number", etc.) to one form
const normalizeKeys = (obj) =>
  Object.fromEntries(
    Object.entries(obj).map(([k, v]) => [k.toLowerCase().replace(/[\s_]+/g, ""), v])
  );

// Derives a display name from an email address, e.g. "ram001@gmail.com" -> "Ram001"


const normalizeText = (value) =>
  String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");

const getAddressContext = (result) => {
  const address = result?.address || {};
  return {
    city:
      address.city ||
      address.town ||
      address.municipality ||
      address.village ||
      "",
    state: address.state || "",
    district: address.state_district || address.county || "",
    locality:
      address.suburb ||
      address.neighbourhood ||
      address.city_district ||
      address.residential ||
      "",
  };
};

const haversineDistanceKm = (lat1, lng1, lat2, lng2) => {
  const toRad = (value) => (Number(value) * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLng / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

const isLikelyLocalShorthand = (value) => {
  const text = normalizeText(value);
  return (
    text.length > 0 &&
    !text.includes(",") &&
    text.split(" ").length <= 3 &&
    !/\b(national highway|nh\s*\d+|airport|railway station)\b/i.test(text)
  );
};

const normalizeRouteResponse = (data, originName, destinationName, origin, destination) => ({
  ...data,
  originName,
  destinationName,
  originLat: origin?.lat ?? data?.origin_lat,
  originLng: origin?.lng ?? data?.origin_lng,
  destinationLat: destination?.lat ?? data?.destination_lat,
  destinationLng: destination?.lng ?? data?.destination_lng,
  departure_time: data?.departure_time ?? data?.departureTime ?? null,
  suggested_stops: Array.isArray(data?.suggested_stops) ? data.suggested_stops : [],
});

const createMapIcon = (background, glyph) =>
  L.divIcon({
    className: "chargesure-map-marker",
    html: `<div style="width:32px;height:32px;border-radius:50%;background:${background};color:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:800;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.35)">${glyph}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
  });

const originIcon = createMapIcon("#2563eb", "S");
const destinationIcon = createMapIcon("#dc2626", "D");
const fallbackChargerIcon = createMapIcon("#7c3aed", "⚡");
const chargerIcons = [
  createMapIcon("#7c3aed", "1"),
  createMapIcon("#9333ea", "2"),
  createMapIcon("#a21caf", "3"),
];

function RouteMapController({ positions }) {
  const map = useMap();
  useEffect(() => {
    const valid = Array.isArray(positions)
      ? positions.filter(
          (p) => Array.isArray(p) && p.length === 2 && Number.isFinite(Number(p[0])) && Number.isFinite(Number(p[1]))
        )
      : [];
    if (valid.length > 1) map.fitBounds(valid, { padding: [28, 28] });
  }, [map, positions]);
  return null;
}

const getDisplayName = (email) => {
  if (!email) return "there";
  const prefix = email.split("@")[0];
  return prefix.charAt(0).toUpperCase() + prefix.slice(1);
};

const STORAGE_KEYS = {
  authEmail: "chargesure_auth_email",
  theme: "chargesure_theme",
};

const getUserStorageKey = (email, section) =>
  `chargesure_${section}_${String(email || "").trim().toLowerCase()}`;

const readStorageJSON = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
};

const writeStorageJSON = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error("ChargeSure storage error:", error);
  }
};

const createVehicleId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `vehicle-${Math.random().toString(36).slice(2)}-${Date.now()}`;
};

export default function App() {
  const storedEmail = (() => {
    try {
      return localStorage.getItem(STORAGE_KEYS.authEmail) || "";
    } catch {
      return "";
    }
  })();

  const loadUserVehicles = (email) =>
    email ? readStorageJSON(getUserStorageKey(email, "vehicles"), []) : [];

  const loadActiveVehicleId = (email) =>
    email ? readStorageJSON(getUserStorageKey(email, "active_vehicle"), null) : null;

  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEYS.theme) || "dark"; }
    catch { return "dark"; }
  });
  const themeClass = theme === "light" ? "theme-light" : "";
  const toggleTheme = () => setTheme((t) => {
    const next = t === "dark" ? "light" : "dark";
    try { localStorage.setItem(STORAGE_KEYS.theme, next); } catch { /* Ignore local storage errors. */ }
    return next;
  });

  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(storedEmail));
  const [userEmail, setUserEmail] = useState(storedEmail);
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notRobot, setNotRobot] = useState(false);
  const [errors, setErrors] = useState({});

  // ---- app state (post-login) ----
  const [activeTab, setActiveTab] = useState("dashboard");
  const [vehicles, setVehicles] = useState(() => loadUserVehicles(storedEmail));
  const [activeVehicleId, setActiveVehicleId] = useState(() => loadActiveVehicleId(storedEmail));
  const [vehicleForm, setVehicleForm] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [showDeleteAccount, setShowDeleteAccount] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !userEmail) return;
    writeStorageJSON(getUserStorageKey(userEmail, "vehicles"), vehicles);
    writeStorageJSON(getUserStorageKey(userEmail, "active_vehicle"), activeVehicleId);
  }, [isAuthenticated, userEmail, vehicles, activeVehicleId]);

  const activeVehicle = vehicles.find((v) => v.id === activeVehicleId) || null;
  const displayName = getDisplayName(userEmail);

  // ---- auth handlers ----
  const validate = () => {
    const next = {};
    if (!email.trim()) next.email = "Email is required.";
    else if (!EMAIL_REGEX.test(email.trim())) next.email = "Enter a valid email address.";

    if (!password) next.password = "Password is required.";
    else if (password.length < 8) next.password = "Password must be at least 8 characters.";
    else if (mode === "signup" && !/(?=.*[A-Za-z])(?=.*\d)/.test(password))
      next.password = "Password must include a letter and a number.";

    if (!notRobot) next.captcha = "Please confirm you're not a robot.";

    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      const nextEmail = email.trim().toLowerCase();
      const savedVehicles = loadUserVehicles(nextEmail);
      const savedActiveVehicleId = loadActiveVehicleId(nextEmail);
      setUserEmail(nextEmail);
      setVehicles(savedVehicles);
      setActiveVehicleId(savedVehicles.some((v) => v.id === savedActiveVehicleId) ? savedActiveVehicleId : savedVehicles[0]?.id ?? null);
      setIsAuthenticated(true);
      try { localStorage.setItem(STORAGE_KEYS.authEmail, nextEmail); } catch { /* Ignore local storage errors. */ }
    }
  };

  const handleGoogleContinue = () => {
    const nextEmail = "google-user@example.com";
    const savedVehicles = loadUserVehicles(nextEmail);
    const savedActiveVehicleId = loadActiveVehicleId(nextEmail);
    setUserEmail(nextEmail);
    setVehicles(savedVehicles);
    setActiveVehicleId(savedVehicles.some((v) => v.id === savedActiveVehicleId) ? savedActiveVehicleId : savedVehicles[0]?.id ?? null);
    setIsAuthenticated(true);
    try { localStorage.setItem(STORAGE_KEYS.authEmail, nextEmail); } catch { /* Ignore local storage errors. */ }
  };

  const switchMode = () => {
    setMode((m) => (m === "signin" ? "signup" : "signin"));
    setErrors({});
  };

  const resetAllState = () => {
    setIsAuthenticated(false);
    setUserEmail("");
    setEmail("");
    setPassword("");
    setNotRobot(false);
    setErrors({});
    setActiveTab("dashboard");
    setVehicles([]);
    setActiveVehicleId(null);
  };

  const handleLogout = () => {
    resetAllState();
    try { localStorage.removeItem(STORAGE_KEYS.authEmail); } catch { /* Ignore local storage errors. */ }
  };

  const handleDeleteAccount = () => {
    const accountEmail = userEmail;
    if (accountEmail) {
      try {
        localStorage.removeItem(getUserStorageKey(accountEmail, "vehicles"));
        localStorage.removeItem(getUserStorageKey(accountEmail, "active_vehicle"));
        localStorage.removeItem(getUserStorageKey(accountEmail, "route"));
        localStorage.removeItem(STORAGE_KEYS.authEmail);
      } catch { /* Ignore local storage errors. */ }
    }
    resetAllState();
    setShowDeleteAccount(false);
  };

  // ---- vehicle handlers ----
  const openAddVehicle = () => {
    setEditingId(null);
    setVehicleForm(EMPTY_VEHICLE_FORM);
  };

  const openEditVehicle = (vehicle) => {
    setEditingId(vehicle.id);
    setVehicleForm({ ...vehicle });
  };

  const closeVehicleForm = () => {
    setVehicleForm(null);
    setEditingId(null);
  };

  const saveVehicle = (e) => {
    e.preventDefault();
    if (!vehicleForm.brand.trim() || !vehicleForm.regNumber.trim()) return;

    if (editingId) {
      setVehicles((prev) =>
        prev.map((v) => (v.id === editingId ? { ...vehicleForm, id: editingId } : v))
      );
    } else {
      const newVehicle = { ...vehicleForm, id: createVehicleId() };
      setVehicles((prev) => [...prev, newVehicle]);
      if (!activeVehicleId) setActiveVehicleId(newVehicle.id);
    }
    closeVehicleForm();
  };

  const deleteVehicle = (id) => {
    setVehicles((prev) => prev.filter((v) => v.id !== id));
    if (activeVehicleId === id) setActiveVehicleId(null);
  };

  const setActiveVehicle = (id) => setActiveVehicleId(id);

  // Parses an uploaded JSON or CSV (single-row) file and autofills the form.
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = String(event.target.result);
      let data = null;

      try {
        data = JSON.parse(text);
        if (Array.isArray(data)) data = data[0];
      } catch {
        const lines = text.trim().split("\n");
        if (lines.length >= 2) {
          const headers = lines[0].split(",").map((h) => h.trim());
          const values = lines[1].split(",").map((v) => v.trim());
          data = Object.fromEntries(headers.map((h, i) => [h, values[i]]));
        }
      }

      if (!data) return;
      const d = normalizeKeys(data);

      setVehicleForm((prev) => ({
        ...prev,
        brand: d.brand ?? prev.brand,
        model: d.model ?? prev.model,
        regNumber: d.regnumber ?? d.vehicleno ?? d.vehiclenumber ?? prev.regNumber,
        year: d.year ?? d.yearofpurchase ?? prev.year,
        mileage: d.mileage ?? prev.mileage,
        type: d.type ?? prev.type,
        battery: d.battery ? Number(d.battery) : prev.battery,
        range: d.range ? Number(d.range) : prev.range,
        capacity: d.capacity ? Number(d.capacity) : prev.capacity,
        connector: d.connector ?? prev.connector,
      }));
    };
    reader.readAsText(file);
  };

  // ================= AUTH SCREEN =================
  if (!isAuthenticated) {
    return (
      <div className={`auth-page ${themeClass}`}>
        <button type="button" className="theme-toggle theme-toggle-floating" onClick={toggleTheme}>
          {theme === "dark" ? "\u2600\uFE0F" : "\u{1F319}"}
        </button>
        <div className="auth-card">
          <div className="auth-brand">
            <span className="auth-brand-mark" aria-hidden="true">
              &#9889;
            </span>
            <h1 className="auth-brand-name">ChargeSure</h1>
          </div>

          <div className="auth-tabs" role="tablist" aria-label="Sign in or sign up">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "signin"}
              className={`auth-tab ${mode === "signin" ? "auth-tab-active" : ""}`}
              onClick={() => setMode("signin")}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "signup"}
              className={`auth-tab ${mode === "signup" ? "auth-tab-active" : ""}`}
              onClick={() => setMode("signup")}
            >
              Sign Up
            </button>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <label className="auth-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className="auth-input"
              placeholder="you@example.com"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {errors.email && <p className="auth-error">{errors.email}</p>}

            <label className="auth-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="auth-input"
              placeholder="Enter your password"
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {errors.password && <p className="auth-error">{errors.password}</p>}

            <div className="captcha-box">
              <input
                id="notRobot"
                type="checkbox"
                checked={notRobot}
                onChange={(e) => setNotRobot(e.target.checked)}
              />
              <div className="captcha-text">
                <label htmlFor="notRobot" className="captcha-label">
                  I&apos;m not a robot
                </label>
                <span className="captcha-sub">Security check</span>
              </div>
            </div>
            {errors.captcha && <p className="auth-error">{errors.captcha}</p>}

            <button type="submit" className="auth-submit">
              {mode === "signin" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <div className="auth-divider">
            <span />
            <p>or</p>
            <span />
          </div>

          <button type="button" className="auth-google" onClick={handleGoogleContinue}>
            <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
              <path
                fill="#4285F4"
                d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.62z"
              />
              <path
                fill="#34A853"
                d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.96v2.33A9 9 0 0 0 9 18z"
              />
              <path
                fill="#FBBC05"
                d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.16.28-1.7V4.97H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.03l2.99-2.33z"
              />
              <path
                fill="#EA4335"
                d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.97l2.99 2.33C4.66 5.17 6.65 3.58 9 3.58z"
              />
            </svg>
            Continue with Google
          </button>

          <p className="auth-switch">
            {mode === "signin" ? (
              <>
                New here?{" "}
                <button type="button" className="auth-link" onClick={switchMode}>
                  Create an account
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button type="button" className="auth-link" onClick={switchMode}>
                  Sign in
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    );
  }

  // ================= APP SHELL (post-login) =================
  return (
    <div className={`app-shell ${themeClass}`}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark" aria-hidden="true">
            &#9889;
          </span>
          <span className="sidebar-brand-name">ChargeSure</span>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`sidebar-nav-item ${activeTab === item.key ? "sidebar-nav-active" : ""}`}
              onClick={() => setActiveTab(item.key)}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button type="button" className="theme-toggle" onClick={toggleTheme}>
            <span aria-hidden="true">{theme === "dark" ? "\u2600\uFE0F" : "\u{1F319}"}</span>
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <div className="sidebar-user">
            <span className="sidebar-user-avatar" aria-hidden="true">
              {displayName.charAt(0).toUpperCase()}
            </span>
            <span className="sidebar-user-email">{displayName}</span>
          </div>
          <button type="button" className="sidebar-logout" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </aside>

      <main className="app-main">
        <header className="app-topbar">
          <div>
            <h1 className="app-topbar-title">
              {NAV_ITEMS.find((n) => n.key === activeTab)?.label}
            </h1>
          </div>
          {activeVehicle && (
            <div className="active-vehicle-chip">
              <span className="chip-dot" aria-hidden="true" />
              <span className="chip-name">
                {activeVehicle.brand} {activeVehicle.model}
              </span>
              <span className="chip-battery">{activeVehicle.battery}%</span>
            </div>
          )}
        </header>

        {activeTab === "dashboard" && (
          <DashboardTab
            vehicles={vehicles}
            activeVehicle={activeVehicle}
            goTo={setActiveTab}
            displayName={displayName}
            userEmail={userEmail}
          />
        )}

        {activeTab === "route" && (
          <RouteTab
            vehicles={vehicles}
            userEmail={userEmail}
          />
        )}

        {activeTab === "vehicles" && (
          <VehiclesTab
            vehicles={vehicles}
            activeVehicleId={activeVehicleId}
            onAdd={openAddVehicle}
            onEdit={openEditVehicle}
            onDelete={deleteVehicle}
            onSetActive={setActiveVehicle}
          />
        )}

        {activeTab === "bookings" && <BookingsTab userEmail={userEmail} />}

        {activeTab === "settings" && (
          <SettingsTab
            userEmail={userEmail}
            theme={theme}
            onSetTheme={setTheme}
            onDeleteAccount={() => setShowDeleteAccount(true)}
          />
        )}
      </main>

      {vehicleForm && (
        <div className="modal-overlay" onClick={closeVehicleForm}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">{editingId ? "Edit Vehicle" : "Add Vehicle"}</h2>

            <label className="auth-label">Autofill data from file</label>
            <input type="file" className="file-input" onChange={handleFileUpload} />
            <p className="tab-note" style={{ marginBottom: 16 }}>
              Matches fields like brand, model, regNumber, year, mileage, battery, range,
              capacity, connector. Fields not found in the file are left as-is.
            </p>

            <form onSubmit={saveVehicle} className="modal-form">
              <div className="modal-row">
                <div>
                  <label className="auth-label">Brand</label>
                  <input
                    className="auth-input"
                    placeholder="e.g. Honda"
                    value={vehicleForm.brand}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, brand: e.target.value })}
                  />
                </div>
                <div>
                  <label className="auth-label">Model</label>
                  <input
                    className="auth-input"
                    placeholder="e.g. Activa Electric"
                    value={vehicleForm.model}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, model: e.target.value })}
                  />
                </div>
              </div>

              <label className="auth-label" style={{ marginTop: 14 }}>
                Vehicle number
              </label>
              <input
                className="auth-input"
                placeholder="e.g. UP78DM9336"
                value={vehicleForm.regNumber}
                onChange={(e) => setVehicleForm({ ...vehicleForm, regNumber: e.target.value })}
              />

              <div className="modal-row">
                <div>
                  <label className="auth-label">Year of purchase</label>
                  <input
                    type="number"
                    className="auth-input"
                    placeholder="e.g. 2023"
                    value={vehicleForm.year}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, year: e.target.value })}
                  />
                </div>
                <div>
                  <label className="auth-label">Mileage (km)</label>
                  <input
                    type="number"
                    className="auth-input"
                    placeholder="e.g. 4200"
                    value={vehicleForm.mileage}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, mileage: e.target.value })}
                  />
                </div>
              </div>

              <label className="auth-label" style={{ marginTop: 14 }}>
                Vehicle type
              </label>
              <select
                className="auth-input"
                value={vehicleForm.type}
                onChange={(e) => setVehicleForm({ ...vehicleForm, type: e.target.value })}
              >
                {VEHICLE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>

              <div className="modal-row">
                <div>
                  <label className="auth-label">Battery %</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    className="auth-input"
                    value={vehicleForm.battery}
                    onChange={(e) =>
                      setVehicleForm({ ...vehicleForm, battery: Number(e.target.value) })
                    }
                  />
                </div>
                <div>
                  <label className="auth-label">Range (km)</label>
                  <input
                    type="number"
                    min="0"
                    className="auth-input"
                    value={vehicleForm.range}
                    onChange={(e) =>
                      setVehicleForm({ ...vehicleForm, range: Number(e.target.value) })
                    }
                  />
                </div>
              </div>

              <div className="modal-row">
                <div>
                  <label className="auth-label">Capacity (kWh)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    className="auth-input"
                    value={vehicleForm.capacity}
                    onChange={(e) =>
                      setVehicleForm({ ...vehicleForm, capacity: Number(e.target.value) })
                    }
                  />
                </div>
                <div>
                  <label className="auth-label">Connector</label>
                  <select
                    className="auth-input"
                    value={vehicleForm.connector}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, connector: e.target.value })}
                  >
                    {CONNECTOR_TYPES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <p className="tab-note">
                TODO: auto-estimating battery/range from brand + model + year needs a vehicle
                spec lookup on the backend — for now these are entered manually or filled from
                an uploaded file.
              </p>

              <div className="modal-actions">
                <button type="button" className="modal-cancel" onClick={closeVehicleForm}>
                  Cancel
                </button>
                <button type="submit" className="auth-submit modal-save">
                  {editingId ? "Save Changes" : "Add Vehicle"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showDeleteAccount && (
        <div className="modal-overlay" onClick={() => setShowDeleteAccount(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Delete account permanently?</h2>
            <p className="tab-subtitle" style={{ marginBottom: 20 }}>
              This will remove your ChargeSure account, saved vehicles, and booking history.
              This action can't be undone.
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="modal-cancel"
                onClick={() => setShowDeleteAccount(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger-submit modal-save"
                onClick={handleDeleteAccount}
              >
                Delete my account
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ================= TAB COMPONENTS =================

function DashboardTab({ vehicles, activeVehicle, goTo, displayName, userEmail }) {
  const [bookings, setBookings] = useState([]);
  const [bookingsLoading, setBookingsLoading] = useState(true);
  const [bookingError, setBookingError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const loadBookings = async () => {
      try {
        const query = userEmail
          ? `?user_email=${encodeURIComponent(userEmail)}`
          : "";

        const response = await fetch(`${API_BASE_URL}/bookings${query}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Could not load booking information.");
        }

        if (!cancelled) {
          setBookings(Array.isArray(data) ? data : []);
          setBookingError("");
          setBookingsLoading(false);
        }
      } catch (err) {
        console.error("Dashboard bookings error:", err);
        if (!cancelled) {
          setBookingError(err.message || "Could not load booking information.");
          setBookingsLoading(false);
        }
      }
    };

    loadBookings();

    return () => {
      cancelled = true;
    };
  }, [userEmail]);

  // The backend already exposes booking status. For the dashboard we treat
  // CONFIRMED bookings as upcoming/reserved slots and CANCELLED bookings as history.
  const upcomingBookings = bookings.filter(
    (booking) => booking.status === "CONFIRMED"
  );

  const nextBooking = [...upcomingBookings].sort(
    (a, b) => new Date(a.slot_start).getTime() - new Date(b.slot_start).getTime()
  )[0];

  const formatBookingDate = (value) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return date.toLocaleDateString(undefined, {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  };

  const formatBookingTime = (start, end) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
      return "—";
    }

    return `${startDate.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    })} – ${endDate.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    })}`;
  };

  return (
    <div className="tab-content">
      <h2 className="dashboard-welcome">Welcome back, {displayName}!</h2>
      <p className="tab-subtitle">Here's what's happening with your EV setup.</p>

      <div className="stat-row">
        <div className="stat-card">
          <span className="stat-value">{vehicles.length}</span>
          <span className="stat-label">Vehicles registered</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{activeVehicle ? `${activeVehicle.battery}%` : "—"}</span>
          <span className="stat-label">Active vehicle battery</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">
            {bookingsLoading ? "…" : upcomingBookings.length}
          </span>
          <span className="stat-label">Upcoming bookings</span>
        </div>
      </div>

      {bookingError && (
        <p className="auth-error" style={{ marginTop: 14 }}>
          {bookingError}
        </p>
      )}

      {!bookingsLoading && nextBooking && (
        <div className="panel" style={{ marginTop: 20 }}>
          <div className="vehicle-card-top">
            <div>
              <span className="type-badge">Next charging slot</span>
              <h3 className="vehicle-name" style={{ marginTop: 10 }}>
                {nextBooking.charger_name}
              </h3>
              <p className="vehicle-reg">{nextBooking.charger_id}</p>
            </div>
            <span className="active-badge">CONFIRMED</span>
          </div>

          <div className="vehicle-stats" style={{ marginTop: 16 }}>
            <div>
              <span className="vehicle-stat-label">Date</span>
              <span className="vehicle-stat-value">
                {formatBookingDate(nextBooking.slot_start)}
              </span>
            </div>
            <div>
              <span className="vehicle-stat-label">Time</span>
              <span className="vehicle-stat-value">
                {formatBookingTime(nextBooking.slot_start, nextBooking.slot_end)}
              </span>
            </div>
            <div>
              <span className="vehicle-stat-label">Connector</span>
              <span className="vehicle-stat-value">
                {nextBooking.vehicle_connector_type || "—"}
              </span>
            </div>
          </div>

          <button
            type="button"
            className="vehicle-action-link"
            style={{ marginTop: 16 }}
            onClick={() => goTo("bookings")}
          >
            View all bookings →
          </button>
        </div>
      )}

      <div className="quick-actions" style={{ marginTop: 20 }}>
        <button className="home-card" onClick={() => goTo("route")}>
          <span className="home-card-icon">{"\u{1F5FA}\uFE0F"}</span>
          <span className="home-card-title">Plan a Route</span>
          <span className="home-card-desc">Find reliability-scored chargers on your route.</span>
        </button>
        <button className="home-card" onClick={() => goTo("vehicles")}>
          <span className="home-card-icon">{"\u{1F697}"}</span>
          <span className="home-card-title">Manage Vehicles</span>
          <span className="home-card-desc">Add or update your registered EVs.</span>
        </button>
        <button className="home-card" onClick={() => goTo("bookings")}>
          <span className="home-card-icon">{"\u{1F4C5}"}</span>
          <span className="home-card-title">View Bookings</span>
          <span className="home-card-desc">Check your upcoming charging slots.</span>
        </button>
      </div>
    </div>
  );
}


function RouteTab({ vehicles, userEmail }) {
  const savedRoute = readStorageJSON(getUserStorageKey(userEmail, "route"), null);
  const [from, setFrom] = useState(() => savedRoute?.from || "");
  const [to, setTo] = useState(() => savedRoute?.to || "");
  const [vehicleId, setVehicleId] = useState(() => savedRoute?.vehicleId ?? vehicles[0]?.id ?? "");
  const [departureMode, setDepartureMode] = useState(() => savedRoute?.departureMode || "now");
  const [scheduledDeparture, setScheduledDeparture] = useState(() => savedRoute?.scheduledDeparture || "");
  const [loading, setLoading] = useState(false);
  const [bookingLoading, setBookingLoading] = useState("");
  const [error, setError] = useState("");
  const [routeResult, setRouteResult] = useState(() => savedRoute?.routeResult || null);
  const [bookedChargerIds, setBookedChargerIds] = useState(() => savedRoute?.bookedChargerIds || []);
  const [selectedCharger, setSelectedCharger] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportStatus, setReportStatus] = useState("");
  const [reportNotes, setReportNotes] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportSuccess, setReportSuccess] = useState("");

  useEffect(() => {
    if (!userEmail) return;
    writeStorageJSON(getUserStorageKey(userEmail, "route"), {
      from, to, vehicleId, routeResult, bookedChargerIds, departureMode, scheduledDeparture,
    });
  }, [userEmail, from, to, vehicleId, routeResult, bookedChargerIds, departureMode, scheduledDeparture]);

  const effectiveVehicleId = vehicles.some(
    (v) => v.id === vehicleId || String(v.id) === String(vehicleId)
  ) ? vehicleId : vehicles[0]?.id ?? "";

  const selectedVehicle = vehicles.find(
    (v) => v.id === effectiveVehicleId || String(v.id) === String(effectiveVehicleId)
  ) || null;

  const formatDateTimeLocal = (date) => {
    const pad = (v) => String(v).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const getMinDepartureDateTime = () => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 1);
    return formatDateTimeLocal(now);
  };

  const toApiDepartureTime = (value) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    const offsetMinutes = -date.getTimezoneOffset();
    const sign = offsetMinutes >= 0 ? "+" : "-";
    const absoluteOffset = Math.abs(offsetMinutes);
    const pad = (v) => String(v).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:00${sign}${pad(Math.floor(absoluteOffset / 60))}:${pad(absoluteOffset % 60)}`;
  };

  const geocodePlace = async (place, options = {}) => {
    const trimmedPlace = String(place || "").trim();
    if (!trimmedPlace) throw new Error("Location cannot be empty.");

    const { context = null, near = null, isDestination = false } = options;
    const originCity = context?.city || "";
    const originState = context?.state || "";
    const parts = [trimmedPlace];
    if (isDestination && originCity) parts.push(originCity);
    if (isDestination && originState) parts.push(originState);
    parts.push("India");
    const contextualQuery = parts.join(", ");
    const genericQuery = /\bindia\b/i.test(trimmedPlace) ? trimmedPlace : `${trimmedPlace}, India`;

    const search = async (query) => {
      const params = new URLSearchParams({
        format: "json", limit: "10", addressdetails: "1", countrycodes: "in", q: query,
      });
      if (near && Number.isFinite(Number(near.lat)) && Number.isFinite(Number(near.lng))) {
        const lat = Number(near.lat); const lng = Number(near.lng);
        params.set("viewbox", [lng - 1.5, lat + 1.5, lng + 1.5, lat - 1.5].join(","));
        params.set("bounded", "0");
      }
      const response = await fetch(`https://nominatim.openstreetmap.org/search?${params.toString()}`, {
        headers: { Accept: "application/json", "Accept-Language": "en" },
      });
      if (!response.ok) throw new Error("Could not connect to the location service.");
      const data = await response.json();
      return Array.isArray(data) ? data.filter((item) =>
        String(item?.address?.country_code || "").toLowerCase() === "in" ||
        String(item?.address?.country || "").toLowerCase() === "india"
      ) : [];
    };

    let candidates = await search(contextualQuery);
    if (!candidates.length && contextualQuery !== genericQuery) candidates = await search(genericQuery);
    if (!candidates.length) throw new Error(`Location not found in India: ${place}`);

    const inputText = normalizeText(trimmedPlace);
    const expectedCity = normalizeText(originCity);
    const expectedState = normalizeText(originState);

    const scored = candidates.map((candidate) => {
      const lat = Number(candidate.lat); const lng = Number(candidate.lon);
      const ctx = getAddressContext(candidate);
      const display = normalizeText(candidate.display_name);
      const city = normalizeText(ctx.city); const state = normalizeText(ctx.state);
      const district = normalizeText(ctx.district); const locality = normalizeText(ctx.locality);
      let score = 5;
      const importance = Number(candidate.importance);
      if (Number.isFinite(importance)) score += importance * 20;
      if (display.includes(inputText)) score += 25;
      if (isDestination && expectedCity) {
        if (city === expectedCity) score += 120;
        else if (display.includes(expectedCity)) score += 70;
        if (locality === expectedCity) score += 50;
      }
      if (isDestination && expectedState) {
        if (state === expectedState) score += 70;
        else if (display.includes(expectedState)) score += 30;
      }
      if (expectedCity && district === expectedCity) score += 40;
      const distanceFromOriginKm = near && Number.isFinite(lat) && Number.isFinite(lng)
        ? haversineDistanceKm(Number(near.lat), Number(near.lng), lat, lng) : null;
      if (Number.isFinite(distanceFromOriginKm)) {
        score -= Math.min(distanceFromOriginKm * 0.08, 35);
        if (isDestination && isLikelyLocalShorthand(trimmedPlace)) {
          if (distanceFromOriginKm <= 25) score += 80;
          else if (distanceFromOriginKm <= 75) score += 45;
          else if (distanceFromOriginKm <= 150) score += 15;
        }
      }
      return { candidate, score, lat, lng, context: ctx, distanceFromOriginKm };
    }).filter((item) => Number.isFinite(item.lat) && Number.isFinite(item.lng)).sort((a, b) => b.score - a.score);

    const best = scored[0];
    if (!best) throw new Error(`Could not resolve "${place}" to a usable Indian location.`);
    if (isDestination && near && isLikelyLocalShorthand(trimmedPlace) && Number.isFinite(best.distanceFromOriginKm) && best.distanceFromOriginKm > 250) {
      throw new Error(`Could not confidently resolve "${place}" near ${originCity || "your starting location"}. Try "${place}, ${originCity || "your city"}".`);
    }
    return {
      lat: best.lat, lng: best.lng, displayName: best.candidate.display_name,
      context: best.context, distanceFromOriginKm: best.distanceFromOriginKm,
    };
  };

  const mapConnectorType = (connector) => {
    switch (connector) {
      case "CCS2": return "CCS";
      case "Type 2": return "Type 2";
      case "CHAdeMO": return "CHAdeMO";
      case "Bharat AC001": return "Bharat AC001";
      case "Bharat DC001": return "Bharat DC001";
      default: return connector || "CCS";
    }
  };

  const formatTime = (value) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const normalizeConfidence = (value) => {
    const normalized = String(value || "medium").trim().toLowerCase();
    if (["high", "very high", "excellent"].includes(normalized)) return "High";
    if (["low", "poor", "weak"].includes(normalized)) return "Low";
    return "Medium";
  };

  const getReliabilityConfidence = (stop) => normalizeConfidence(stop.reliability_confidence ?? stop.confidence_band);

  const getConnectorStatus = (stop) => {
    if (stop.connector_status) {
      const normalized = String(stop.connector_status).trim().toLowerCase();
      return { label: normalized === "compatible" ? "Compatible" : normalized === "not compatible" ? "Not compatible" : stop.connector_status, compatible: ["compatible", "true", "yes"].includes(normalized) };
    }
    if (stop.connector_compatible !== undefined) return { label: stop.connector_compatible ? "Compatible" : "Not compatible", compatible: Boolean(stop.connector_compatible) };
    return { label: "Compatible", compatible: true };
  };

  const getAvailability = (stop) => {
    if (stop.availability_status) return String(stop.availability_status);
    if (stop.is_available !== undefined) return stop.is_available ? "Available" : "Unavailable";
    if (stop.available !== undefined) return stop.available ? "Available" : "Unavailable";
    return stop.recommended_slot_start && stop.recommended_slot_end ? "Available" : "Not available";
  };

  const getRankingLabel = (stop, index) => stop.recommendation_label || (index === 0 ? "Best overall match" : index === 1 ? "Strong alternative" : "Good alternative");

  const getWhyThisCharger = (stop, index) => {
    if (stop.why_recommended) return stop.why_recommended;
    const reliability = Number(stop.reliability_score);
    const distance = Number(stop.distance_from_origin_km);
    const compatible = getConnectorStatus(stop).compatible;
    const parts = [];
    if (Number.isFinite(reliability)) parts.push(index === 0 ? `highest reliability (${reliability.toFixed(1)}%)` : index === 1 ? `strong reliability (${reliability.toFixed(1)}%)` : `reliable alternative (${reliability.toFixed(1)}%)`);
    if (compatible) parts.push("compatible connector");
    if (Number.isFinite(distance)) parts.push(distance <= 7 ? "very low route deviation" : distance <= 12 ? "low route deviation" : distance <= 25 ? "reasonable route distance" : "route-compatible option");
    if (stop.is_grid_aware_recommended) parts.push("grid-optimized slot");
    if (!parts.length) return "Selected by ChargeSure's intelligent ranking engine.";
    return parts.length === 1 ? `${parts[0].charAt(0).toUpperCase() + parts[0].slice(1)}.` : `${parts[0].charAt(0).toUpperCase() + parts[0].slice(1)} + ${parts.slice(1).join(" + ")}.`;
  };

  const handleFindRoute = async () => {
    setError(""); setRouteResult(null); setBookedChargerIds([]); setSelectedCharger(null); setReportSuccess("");
    if (!from.trim() || !to.trim()) return setError("Enter both a starting point and destination.");
    if (!selectedVehicle) return setError("Add and select a vehicle before planning a route.");
    if (!selectedVehicle.range || Number(selectedVehicle.range) <= 0) return setError("Please enter a valid vehicle range.");
    if (selectedVehicle.battery === "" || selectedVehicle.battery === null || Number.isNaN(Number(selectedVehicle.battery))) return setError("Please enter a valid battery percentage.");

    let departureTimePayload = null;
    if (departureMode === "scheduled") {
      if (!scheduledDeparture) return setError("Select a departure date and time.");
      const date = new Date(scheduledDeparture);
      if (Number.isNaN(date.getTime())) return setError("Enter a valid departure time.");
      if (date <= new Date()) return setError("Departure time must be in the future.");
      departureTimePayload = toApiDepartureTime(scheduledDeparture);
      if (!departureTimePayload) return setError("Could not process the selected departure time.");
    }

    try {
      setLoading(true);
      const origin = await geocodePlace(from.trim(), { isDestination: false });
      const destination = await geocodePlace(to.trim(), { isDestination: true, near: origin, context: origin.context });
      if (isLikelyLocalShorthand(to.trim()) && Number.isFinite(destination.distanceFromOriginKm) && destination.distanceFromOriginKm > 500) {
        throw new Error(`The destination "${to.trim()}" resolved too far from ${origin.context?.city || "your starting point"}. Please enter a more specific destination.`);
      }

      const response = await fetch(`${API_BASE_URL}/routes/plan`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          origin_lat: origin.lat, origin_lng: origin.lng,
          destination_lat: destination.lat, destination_lng: destination.lng,
          vehicle_class: selectedVehicle.type === "2-Wheeler" ? "2W" : selectedVehicle.type === "3-Wheeler" ? "3W" : "4W",
          vehicle_range_km: Number(selectedVehicle.range), current_charge_pct: Number(selectedVehicle.battery),
          vehicle_connector_type: mapConnectorType(selectedVehicle.connector), departure_time: departureTimePayload,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Route planning failed.");
      setRouteResult(normalizeRouteResponse(data, origin.displayName, destination.displayName, origin, destination));
    } catch (err) {
      console.error("Route planning error:", err);
      setError(err.message || "Unable to plan the route.");
    } finally { setLoading(false); }
  };

  const handleBookSlot = async (stop) => {
    if (!selectedVehicle) return setError("Select a vehicle before booking.");
    if (!stop.recommended_slot_start || !stop.recommended_slot_end) return setError("This charger does not have a valid charging slot.");
    if (bookedChargerIds.includes(stop.charger_id)) return;
    try {
      setBookingLoading(stop.charger_id); setError("");
      const response = await fetch(`${API_BASE_URL}/bookings`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          charger_id: stop.charger_id, charger_name: stop.name, user_email: userEmail,
          vehicle_registration: selectedVehicle.regNumber, vehicle_connector_type: selectedVehicle.connector,
          slot_start: stop.recommended_slot_start, slot_end: stop.recommended_slot_end,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not book this charging slot.");
      setBookedChargerIds((prev) => prev.includes(stop.charger_id) ? prev : [...prev, stop.charger_id]);
    } catch (err) {
      console.error("Booking error:", err); setError(err.message || "Booking failed.");
    } finally { setBookingLoading(""); }
  };

  const openReportModal = (stop) => {
    setSelectedCharger(stop); setReportStatus(""); setReportNotes(""); setReportSuccess(""); setError(""); setShowReportModal(true);
  };

  const handleSubmitReport = async () => {
    if (!selectedCharger) return;
    if (!reportStatus) { setError("Select the current charger status."); return; }
    try {
      setReportLoading(true); setError(""); setReportSuccess("");
      const response = await fetch(`${API_BASE_URL}/reports`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          charger_id: selectedCharger.charger_id,
          reported_status: reportStatus,
          latitude: Number(selectedCharger.latitude), longitude: Number(selectedCharger.longitude),
          user_email: userEmail || null, notes: reportNotes.trim() || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not submit your report.");
      setReportSuccess("Thanks — your charger report was recorded.");
      setReportStatus(""); setReportNotes("");
      setTimeout(() => setShowReportModal(false), 900);
    } catch (err) {
      console.error("Crowd report error:", err); setError(err.message || "Could not submit your report.");
    } finally { setReportLoading(false); }
  };

  const routeCoordinates = Array.isArray(routeResult?.geometry?.coordinates)
    ? routeResult.geometry.coordinates.filter((c) => Array.isArray(c) && c.length >= 2).map((c) => [Number(c[1]), Number(c[0])]).filter((c) => Number.isFinite(c[0]) && Number.isFinite(c[1]))
    : [];

  const mapChargerStops = Array.isArray(routeResult?.suggested_stops)
    ? routeResult.suggested_stops.filter((s) => Number.isFinite(Number(s.latitude)) && Number.isFinite(Number(s.longitude))).map((s) => [Number(s.latitude), Number(s.longitude)])
    : [];

  const mapPositions = [...routeCoordinates, ...mapChargerStops];
  if (Number.isFinite(Number(routeResult?.originLat)) && Number.isFinite(Number(routeResult?.originLng))) mapPositions.push([Number(routeResult.originLat), Number(routeResult.originLng)]);
  if (Number.isFinite(Number(routeResult?.destinationLat)) && Number.isFinite(Number(routeResult?.destinationLng))) mapPositions.push([Number(routeResult.destinationLat), Number(routeResult.destinationLng)]);

  const fallbackCenter = routeCoordinates[0] || [22.3072, 73.1812];
  const safeRange = Number(routeResult?.safe_range_km);
  const hasSafeRange = Number.isFinite(safeRange);
  const routeDistance = Number(routeResult?.distance_km);
  const chargingRequired = hasSafeRange && Number.isFinite(routeDistance) && routeDistance > safeRange;
  const optionalCount = Array.isArray(routeResult?.suggested_stops) ? routeResult.suggested_stops.length : 0;
  const selectedChargerDetails = selectedCharger ? {
    ...selectedCharger,
    confidence: getReliabilityConfidence(selectedCharger),
    connectorStatus: getConnectorStatus(selectedCharger),
    availability: getAvailability(selectedCharger),
    reliability: Number(selectedCharger.reliability_score),
    routeDistance: Number(selectedCharger.distance_from_origin_km),
  } : null;

  return (
    <div className="tab-content">
      <p className="tab-subtitle">Plan a trip with reliability-scored charging stops.</p>
      <div className="panel">
        <label className="auth-label">Starting point</label>
        <input className="auth-input" placeholder="e.g. Ahmedabad" value={from} onChange={(e) => setFrom(e.target.value)} />
        <label className="auth-label" style={{ marginTop: 14 }}>Destination</label>
        <input className="auth-input" placeholder="e.g. Vadodara" value={to} onChange={(e) => setTo(e.target.value)} />
        <label className="auth-label" style={{ marginTop: 14 }}>Vehicle</label>
        <select className="auth-input" value={effectiveVehicleId} onChange={(e) => setVehicleId(e.target.value)}>
          {vehicles.length === 0 && <option value="">Add a vehicle first</option>}
          {vehicles.map((v) => <option key={v.id} value={v.id}>{v.brand} {v.model} ({v.regNumber})</option>)}
        </select>

        <div style={{ marginTop: 18 }}>
          <label className="auth-label">Departure</label>
          <div style={{ display: "flex", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
            <button type="button" className={`theme-option ${departureMode === "now" ? "theme-option-active" : ""}`} onClick={() => setDepartureMode("now")}>● Leave now</button>
            <button type="button" className={`theme-option ${departureMode === "scheduled" ? "theme-option-active" : ""}`} onClick={() => setDepartureMode("scheduled")}>○ Schedule departure</button>
          </div>
          {departureMode === "scheduled" ? (
            <div style={{ marginTop: 12 }}>
              <input type="datetime-local" className="auth-input" value={scheduledDeparture} min={getMinDepartureDateTime()} onChange={(e) => setScheduledDeparture(e.target.value)} />
              <p className="tab-note" style={{ marginTop: 8 }}>Route ETA and charging slots will be calculated from this departure time.</p>
            </div>
          ) : <p className="tab-note" style={{ marginTop: 8 }}>Uses the current India time when you plan the route.</p>}
        </div>

        <button type="button" className="auth-submit" style={{ marginTop: 20 }} onClick={handleFindRoute} disabled={loading}>{loading ? "Planning route..." : "Find Route"}</button>
        {error && !showReportModal && <p className="auth-error" style={{ marginTop: 14 }}>{error}</p>}
      </div>

      {routeResult && (
        <div style={{ marginTop: 20 }}>
          <div className="panel">
            <h2 className="settings-row-title">Route Summary</h2>
            <p className="tab-note" style={{ marginTop: 8 }}>{routeResult.originName} → {routeResult.destinationName}</p>
            <div className="vehicle-stats" style={{ marginTop: 16 }}>
              <div><span className="vehicle-stat-label">Distance</span><span className="vehicle-stat-value">{Number(routeResult.distance_km).toFixed(2)} km</span></div>
              <div><span className="vehicle-stat-label">Duration</span><span className="vehicle-stat-value">{Number(routeResult.duration_minutes).toFixed(0)} min</span></div>
              <div><span className="vehicle-stat-label">Safe range</span><span className="vehicle-stat-value">{hasSafeRange ? `${safeRange.toFixed(1)} km` : "—"}</span></div>
            </div>
            <div className="vehicle-stats" style={{ marginTop: 14 }}>
              <div><span className="vehicle-stat-label">Charging stops</span><span className="vehicle-stat-value">{chargingRequired ? `${optionalCount} required` : "0 required"}</span></div>
              {!chargingRequired && <div><span className="vehicle-stat-label">Optional chargers</span><span className="vehicle-stat-value">{optionalCount}</span></div>}
              <div><span className="vehicle-stat-label">Safe chargers found</span><span className="vehicle-stat-value">{Number.isFinite(Number(routeResult.safe_candidate_count)) ? routeResult.safe_candidate_count : "—"}</span></div>
              <div><span className="vehicle-stat-label">Chargers evaluated</span><span className="vehicle-stat-value">{Number.isFinite(Number(routeResult.candidate_count)) ? routeResult.candidate_count : "—"}</span></div>
            </div>
            <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
              <span className="connector-chip">{departureMode === "scheduled" ? `Departure: ${new Date(scheduledDeparture).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}` : "Departure: Now"}</span>
              {selectedVehicle && <span className="connector-chip">Vehicle: {selectedVehicle.brand} {selectedVehicle.model}</span>}
            </div>
            {hasSafeRange && <div style={{ marginTop: 16, padding: "13px 14px", borderRadius: 10, border: chargingRequired ? "1px solid rgba(245,158,11,0.35)" : "1px solid rgba(34,197,94,0.35)", background: chargingRequired ? "rgba(245,158,11,0.08)" : "rgba(34,197,94,0.08)" }}>
              <strong>{chargingRequired ? "⚠ Charging required" : "✓ No charging required"}</strong>
              <p className="tab-note" style={{ marginTop: 5 }}>{chargingRequired ? `The ${routeDistance.toFixed(1)} km trip exceeds the current safe range of ${safeRange.toFixed(1)} km. ChargeSure has identified safe charging options along the route.` : `The ${routeDistance.toFixed(1)} km trip is within the current safe range of ${safeRange.toFixed(1)} km.`}</p>
            </div>}
          </div>

          {routeCoordinates.length > 1 && <div className="panel" style={{ marginTop: 20, padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "16px 18px 12px" }}><h2 className="settings-row-title">Route Map</h2><p className="tab-note">{chargingRequired ? "Actual road route with your recommended charging stations." : "Actual road route with optional charging stations available as backup."}</p></div>
            <div style={{ height: 460, width: "100%" }}>
              <MapContainer center={fallbackCenter} zoom={9} scrollWheelZoom style={{ width: "100%", height: "100%" }}>
                <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <Polyline positions={routeCoordinates} pathOptions={{ weight: 6, opacity: 0.85 }} />
                <RouteMapController positions={mapPositions} />
                {routeCoordinates[0] && <Marker position={routeCoordinates[0]} icon={originIcon}><Popup><strong>Starting point</strong><br />{routeResult.originName}</Popup></Marker>}
                {routeCoordinates[routeCoordinates.length - 1] && <Marker position={routeCoordinates[routeCoordinates.length - 1]} icon={destinationIcon}><Popup><strong>Destination</strong><br />{routeResult.destinationName}</Popup></Marker>}
                {routeResult.suggested_stops?.map((stop, index) => <Marker key={stop.charger_id} position={[Number(stop.latitude), Number(stop.longitude)]} icon={chargerIcons[index] || fallbackChargerIcon}><Popup><strong>#{index + 1} {stop.name}</strong><div style={{ marginTop: 6, fontSize: 12, lineHeight: 1.5 }}><div>Reliability: <strong>{Number(stop.reliability_score).toFixed(1)}%</strong></div><div>Confidence: <strong>{getReliabilityConfidence(stop)}</strong></div><div>Connector: <strong>{getConnectorStatus(stop).label}</strong></div><div>Est. arrival: <strong>{formatTime(stop.estimated_arrival)}</strong></div></div></Popup></Marker>)}
              </MapContainer>
            </div>
            <div style={{ padding: "12px 18px 16px", display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12 }}><span>🔵 Start</span><span>🔴 Destination</span><span>⚡ {chargingRequired ? "Recommended chargers" : "Optional chargers"}</span></div>
          </div>}

          <div style={{ marginTop: 20 }}>
            <h2 className="settings-row-title">{chargingRequired ? "Recommended Chargers" : "Optional Chargers Nearby"}</h2>
            <p className="tab-note" style={{ marginTop: 6 }}>{chargingRequired ? "Ranked using reliability, route proximity, connector compatibility, operational signals and charging-slot intelligence." : "These are optional backup charging options near your route. The current trip is already within your vehicle's safe range."}</p>
            {routeResult.suggested_stops?.length > 0 ? <div className="vehicle-grid" style={{ marginTop: 14 }}>
              {routeResult.suggested_stops.map((stop, index) => {
                const isBooked = bookedChargerIds.includes(stop.charger_id);
                const connectorStatus = getConnectorStatus(stop);
                const availability = getAvailability(stop);
                const confidence = getReliabilityConfidence(stop);
                const rankingLabel = getRankingLabel(stop, index);
                const why = getWhyThisCharger(stop, index);
                const reliability = Number(stop.reliability_score);
                const routeDist = Number(stop.distance_from_origin_km);
                return <div className="vehicle-card" key={stop.charger_id}>
                  <div className="vehicle-card-top"><div><span className="type-badge">#{index + 1} {chargingRequired ? "Recommended" : "Optional"}</span><button type="button" onClick={() => setSelectedCharger(stop)} style={{ display: "block", marginTop: 10, padding: 0, border: "none", background: "none", color: "inherit", textAlign: "left", cursor: "pointer", font: "inherit" }}><h3 className="vehicle-name" style={{ margin: 0 }}>{stop.name}</h3></button><p className="vehicle-reg">{stop.charger_id}</p></div><span className="active-badge">{confidence}</span></div>
                  <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: 10, background: "rgba(127,127,127,0.08)", fontSize: 12, fontWeight: 600 }}>{rankingLabel}</div>
                  <div className="vehicle-stats" style={{ marginTop: 14 }}><div><span className="vehicle-stat-label">Reliability</span><span className="vehicle-stat-value">{Number.isFinite(reliability) ? `${reliability.toFixed(1)}%` : "—"}</span></div><div><span className="vehicle-stat-label">Route distance</span><span className="vehicle-stat-value">{Number.isFinite(routeDist) ? `${routeDist.toFixed(2)} km` : "—"}</span></div></div>
                  <div style={{ marginTop: 14, borderTop: "1px solid rgba(127,127,127,0.15)", paddingTop: 14 }}><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px 16px" }}><div><span className="vehicle-stat-label">Confidence</span><span className="vehicle-stat-value">{confidence}</span></div><div><span className="vehicle-stat-label">Connector</span><span className="vehicle-stat-value">{connectorStatus.compatible ? "✓" : "✕"} {connectorStatus.label}</span></div><div><span className="vehicle-stat-label">Est. arrival</span><span className="vehicle-stat-value">{formatTime(stop.estimated_arrival)}</span></div><div><span className="vehicle-stat-label">Availability</span><span className="vehicle-stat-value">{availability}</span></div><div><span className="vehicle-stat-label">Grid</span><span className="vehicle-stat-value">{stop.is_grid_aware_recommended ? "Optimized" : "Near ETA"}</span></div></div></div>
                  <div style={{ marginTop: 16, padding: 12, borderRadius: 10, border: "1px solid rgba(127,127,127,0.18)" }}><div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}><span className="connector-chip">{stop.is_grid_aware_recommended ? "Grid-aware slot" : departureMode === "scheduled" ? "Scheduled-trip slot" : "Near-ETA slot"}</span>{availability === "Available" && <span style={{ fontSize: 12, fontWeight: 700 }}>● Available</span>}</div>{stop.recommended_slot_start ? <p className="tab-note" style={{ marginTop: 10, fontWeight: 600 }}>Charging slot: {formatTime(stop.recommended_slot_start)} – {formatTime(stop.recommended_slot_end)}</p> : <p className="tab-note" style={{ marginTop: 10 }}>No charging slot is currently available.</p>}</div>
                  <div style={{ marginTop: 14, padding: 12, borderRadius: 10, border: "1px solid rgba(127,127,127,0.14)" }}><span className="vehicle-stat-label">{chargingRequired ? "Why recommended" : "Why this charger is available"}</span><p className="tab-note" style={{ marginTop: 6, lineHeight: 1.5 }}>{why}</p></div>
                  <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}><button type="button" className="vehicle-action-link" onClick={() => setSelectedCharger(stop)} style={{ border: "none", background: "none", padding: 0, cursor: "pointer" }}>View details</button><button type="button" className="vehicle-action-link" onClick={() => openReportModal(stop)} style={{ border: "none", background: "none", padding: 0, cursor: "pointer" }}>Report status</button><a href={`https://www.google.com/maps/dir/?api=1&destination=${stop.latitude},${stop.longitude}`} target="_blank" rel="noreferrer" className="vehicle-action-link" style={{ textDecoration: "none" }}>Open in Maps</a>{!isBooked && <button type="button" className="vehicle-action-link" onClick={() => handleBookSlot(stop)} disabled={bookingLoading === stop.charger_id} style={{ border: "none", background: "none", cursor: bookingLoading === stop.charger_id ? "wait" : "pointer", padding: 0 }}>{bookingLoading === stop.charger_id ? "Booking..." : "Book Slot"}</button>}</div>
                  {isBooked && <div style={{ marginTop: 14, padding: "10px 12px", borderRadius: 10, border: "1px solid rgba(127,127,127,0.18)" }}><p className="tab-note" style={{ margin: 0, fontWeight: 700 }}>✓ Booking confirmed</p><p className="tab-note" style={{ marginTop: 4 }}>This charging station is reserved for your selected slot.</p></div>}
                </div>;
              })}
            </div> : <div className="empty-state" style={{ marginTop: 14 }}><p>{chargingRequired ? "No safe charging stops were found for this route." : "No optional charging stations were found near this route."}</p></div>}
          </div>
        </div>
      )}

      {selectedChargerDetails && <div className="modal-overlay" onClick={() => setSelectedCharger(null)} role="presentation"><div className="modal-card" style={{ width: "min(760px, 94vw)", maxHeight: "88vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}><div><span className="type-badge">{selectedChargerDetails.recommendation_label || "Charger details"}</span><h2 className="modal-title" style={{ marginTop: 10, marginBottom: 6 }}>{selectedChargerDetails.name}</h2><p className="vehicle-reg">{selectedChargerDetails.charger_id}</p></div><button type="button" className="modal-cancel" onClick={() => setSelectedCharger(null)}>✕ Close</button></div>
        <div style={{ marginTop: 18, padding: 16, borderRadius: 12, border: "1px solid rgba(127,127,127,0.18)", background: "rgba(127,127,127,0.06)" }}><div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}><div><span className="vehicle-stat-label">Reliability</span><div style={{ marginTop: 4, fontSize: 28, fontWeight: 800 }}>{Number.isFinite(selectedChargerDetails.reliability) ? `${selectedChargerDetails.reliability.toFixed(1)}%` : "—"}</div></div><div style={{ textAlign: "right" }}><span className="vehicle-stat-label">Confidence</span><div className="active-badge" style={{ marginTop: 7, display: "inline-flex" }}>{selectedChargerDetails.confidence}</div></div></div><p className="tab-note" style={{ marginTop: 10 }}>ChargeSure&apos;s predicted reliability for this charger, together with the confidence of that prediction.</p></div>
        <div style={{ marginTop: 18 }}><h3 className="settings-row-title">Charger Status</h3><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginTop: 12 }}><div className="panel"><span className="vehicle-stat-label">Availability</span><span className="vehicle-stat-value">{selectedChargerDetails.availability}</span></div><div className="panel"><span className="vehicle-stat-label">Connector</span><span className="vehicle-stat-value">{selectedChargerDetails.connectorStatus.compatible ? "✓" : "✕"} {selectedChargerDetails.connectorStatus.label}</span></div><div className="panel"><span className="vehicle-stat-label">Estimated arrival</span><span className="vehicle-stat-value">{formatTime(selectedChargerDetails.estimated_arrival)}</span></div><div className="panel"><span className="vehicle-stat-label">Grid</span><span className="vehicle-stat-value">{selectedChargerDetails.is_grid_aware_recommended ? "Optimized" : "Near ETA"}</span></div></div></div>
        <div style={{ marginTop: 18 }}><h3 className="settings-row-title">Trip Fit</h3><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginTop: 12 }}><div className="panel"><span className="vehicle-stat-label">Route distance</span><span className="vehicle-stat-value">{Number.isFinite(selectedChargerDetails.routeDistance) ? `${selectedChargerDetails.routeDistance.toFixed(2)} km` : "—"}</span></div><div className="panel"><span className="vehicle-stat-label">Range safety</span><span className="vehicle-stat-value">{chargingRequired ? "Safe charging option" : "Optional backup"}</span></div><div className="panel"><span className="vehicle-stat-label">Vehicle</span><span className="vehicle-stat-value">{selectedVehicle ? `${selectedVehicle.brand} ${selectedVehicle.model}` : "—"}</span></div><div className="panel"><span className="vehicle-stat-label">Compatibility</span><span className="vehicle-stat-value">{selectedChargerDetails.connectorStatus.compatible ? "Compatible" : "Not compatible"}</span></div></div></div>
        <div style={{ marginTop: 18, padding: 14, borderRadius: 10, border: "1px solid rgba(127,127,127,0.14)" }}><span className="vehicle-stat-label">Why this charger?</span><p className="tab-note" style={{ marginTop: 7, lineHeight: 1.6 }}>{getWhyThisCharger(selectedChargerDetails, Math.max(0, routeResult?.suggested_stops?.findIndex((s) => s.charger_id === selectedChargerDetails.charger_id) ?? 0))}</p></div>
        <div style={{ marginTop: 18 }}><h3 className="settings-row-title">Recommended Charging Slot</h3><div style={{ marginTop: 12, padding: 14, borderRadius: 10, border: "1px solid rgba(127,127,127,0.16)" }}><div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}><span className="connector-chip">{selectedChargerDetails.is_grid_aware_recommended ? "Grid-aware slot" : departureMode === "scheduled" ? "Scheduled-trip slot" : "Near-ETA slot"}</span><span style={{ fontSize: 12, fontWeight: 700 }}>{selectedChargerDetails.availability === "Available" ? "● Available" : selectedChargerDetails.availability}</span></div>{selectedChargerDetails.recommended_slot_start ? <p className="tab-note" style={{ marginTop: 10, fontWeight: 700 }}>Charging slot: {formatTime(selectedChargerDetails.recommended_slot_start)} – {formatTime(selectedChargerDetails.recommended_slot_end)}</p> : <p className="tab-note" style={{ marginTop: 10 }}>No charging slot is currently available.</p>}</div></div>
        <div className="modal-actions" style={{ marginTop: 20 }}><button type="button" className="modal-cancel" onClick={() => setSelectedCharger(null)}>Close</button><button type="button" className="vehicle-action-link" onClick={() => openReportModal(selectedChargerDetails)} style={{ border: "none", background: "none", cursor: "pointer" }}>Report status</button><a href={`https://www.google.com/maps/dir/?api=1&destination=${selectedChargerDetails.latitude},${selectedChargerDetails.longitude}`} target="_blank" rel="noreferrer" className="vehicle-action-link" style={{ textDecoration: "none" }}>Open in Maps</a>{bookedChargerIds.includes(selectedChargerDetails.charger_id) ? <span className="active-badge" style={{ display: "inline-flex", alignItems: "center" }}>✓ Booking confirmed</span> : <button type="button" className="auth-submit modal-save" onClick={() => handleBookSlot(selectedChargerDetails)} disabled={bookingLoading === selectedChargerDetails.charger_id}>{bookingLoading === selectedChargerDetails.charger_id ? "Booking..." : "Book Slot"}</button>}</div>
      </div></div>}

      {showReportModal && selectedCharger && <div className="modal-overlay" onClick={() => !reportLoading && setShowReportModal(false)} role="presentation"><div className="modal-card" style={{ width: "min(560px, 94vw)" }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 14 }}><div><span className="type-badge">Crowd report</span><h2 className="modal-title" style={{ marginTop: 10, marginBottom: 6 }}>Report charger status</h2><p className="vehicle-reg">{selectedCharger.name} · {selectedCharger.charger_id}</p></div><button type="button" className="modal-cancel" onClick={() => !reportLoading && setShowReportModal(false)}>✕ Close</button></div>
        <p className="tab-subtitle" style={{ marginTop: 18 }}>Help ChargeSure keep charger availability and reliability signals fresh.</p>
        <label className="auth-label" style={{ marginTop: 16 }}>Current status</label>
        <div style={{ display: "grid", gap: 10, marginTop: 10 }}>
          {[{value:"working",label:"✓ Working"},{value:"busy",label:"◔ Busy / queue"},{value:"broken",label:"✕ Broken / unavailable"},{value:"wrong_location",label:"📍 Wrong location"}].map((item) => <button key={item.value} type="button" className={`theme-option ${reportStatus === item.value ? "theme-option-active" : ""}`} onClick={() => setReportStatus(item.value)} style={{ textAlign: "left" }}>{item.label}</button>)}
        </div>
        <label className="auth-label" style={{ marginTop: 16 }}>Optional note</label>
        <textarea className="auth-input" rows="4" placeholder="Add what you observed..." value={reportNotes} onChange={(e) => setReportNotes(e.target.value)} style={{ resize: "vertical" }} />
        {(error || reportSuccess) && <p className={reportSuccess ? "tab-note" : "auth-error"} style={{ marginTop: 12, fontWeight: reportSuccess ? 600 : undefined }}>{reportSuccess || error}</p>}
        <div className="modal-actions" style={{ marginTop: 18 }}><button type="button" className="modal-cancel" onClick={() => !reportLoading && setShowReportModal(false)}>Cancel</button><button type="button" className="auth-submit modal-save" onClick={handleSubmitReport} disabled={reportLoading}>{reportLoading ? "Submitting..." : "Submit report"}</button></div>
      </div></div>}
    </div>
  );
}

function VehiclesTab({ vehicles, activeVehicleId, onAdd, onEdit, onDelete, onSetActive }) {
  return (
    <div className="tab-content">
      <div className="tab-header-row">
        <p className="tab-subtitle">Manage your EV fleet.</p>
        <button type="button" className="add-vehicle-btn" onClick={onAdd}>
          + Add vehicle
        </button>
      </div>

      {vehicles.length === 0 ? (
        <div className="empty-state">
          <p>No vehicles added yet.</p>
          <button type="button" className="add-vehicle-btn" onClick={onAdd}>
            + Add your first vehicle
          </button>
        </div>
      ) : (
        <div className="vehicle-grid">
          {vehicles.map((v) => (
            <div
              key={v.id}
              className={`vehicle-card ${v.id === activeVehicleId ? "vehicle-card-active" : ""}`}
            >
              <div className="vehicle-card-top">
                <div>
                  <h3 className="vehicle-name">
                    {v.brand} {v.model}
                  </h3>
                  <p className="vehicle-reg">
                    {v.regNumber}
                    {v.year ? ` · ${v.year}` : ""}
                  </p>
                </div>
                {v.id === activeVehicleId && <span className="active-badge">Active</span>}
              </div>

              <span className="type-badge">{v.type}</span>

              <div className="battery-row">
                <span>Battery</span>
                <span>{v.battery}%</span>
              </div>
              <div className="battery-track">
                <div className="battery-fill" style={{ width: `${v.battery}%` }} />
              </div>

              <div className="vehicle-stats">
                <div>
                  <span className="vehicle-stat-label">Range</span>
                  <span className="vehicle-stat-value">{v.range} km</span>
                </div>
                <div>
                  <span className="vehicle-stat-label">Capacity</span>
                  <span className="vehicle-stat-value">{v.capacity} kWh</span>
                </div>
                {v.mileage && (
                  <div>
                    <span className="vehicle-stat-label">Mileage</span>
                    <span className="vehicle-stat-value">{v.mileage} km</span>
                  </div>
                )}
              </div>

              <span className="connector-chip">{v.connector}</span>

              <div className="vehicle-actions">
                {v.id !== activeVehicleId && (
                  <button
                    type="button"
                    className="vehicle-action-link"
                    onClick={() => onSetActive(v.id)}
                  >
                    Set active
                  </button>
                )}
                <button type="button" className="vehicle-action-link" onClick={() => onEdit(v)}>
                  Edit
                </button>
                <button
                  type="button"
                  className="vehicle-action-link vehicle-action-danger"
                  onClick={() => onDelete(v.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function BookingsTab({ userEmail }) {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const query = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : "";
        const response = await fetch(`${API_BASE_URL}/bookings${query}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load bookings.");
        if (!cancelled) { setBookings(Array.isArray(data) ? data : []); setError(""); }
      } catch (err) {
        console.error("Bookings load error:", err);
        if (!cancelled) setError(err.message || "Could not load bookings.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [userEmail]);

  const cancelBooking = async (bookingId) => {
    try {
      setActionId(bookingId);
      setError("");

      const response = await fetch(`${API_BASE_URL}/bookings/${bookingId}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not cancel booking.");
      }

      setBookings((prev) =>
        prev.map((booking) =>
          booking.id === bookingId
            ? { ...booking, status: "CANCELLED" }
            : booking
        )
      );
    } catch (err) {
      console.error("Booking cancellation error:", err);
      setError(err.message || "Could not cancel booking.");
    } finally {
      setActionId("");
    }
  };

  return (
    <div className="tab-content">
      <p className="tab-subtitle">Your upcoming and past charging slots.</p>

      {error && (
        <p className="auth-error" style={{ marginTop: 14 }}>
          {error}
        </p>
      )}

      {loading ? (
        <div className="empty-state">
          <p>Loading bookings...</p>
        </div>
      ) : bookings.length === 0 ? (
        <div className="empty-state">
          <p>No bookings yet.</p>
          <p className="tab-note">
            Book a charging slot from Plan Route and it will appear here.
          </p>
        </div>
      ) : (
        <div className="vehicle-grid" style={{ marginTop: 18 }}>
          {bookings.map((booking) => {
            const start = new Date(booking.slot_start);
            const end = new Date(booking.slot_end);
            const active = booking.status === "CONFIRMED";
            const future = active;

            return (
              <div className="vehicle-card" key={booking.id}>
                <div className="vehicle-card-top">
                  <div>
                    <span className="type-badge">
                      {active && future ? "Upcoming" : "Booking"}
                    </span>
                    <h3 className="vehicle-name" style={{ marginTop: 10 }}>
                      {booking.charger_name}
                    </h3>
                    <p className="vehicle-reg">{booking.charger_id}</p>
                  </div>
                  <span
                    className="active-badge"
                    style={booking.status === "CANCELLED" ? { opacity: 0.65 } : undefined}
                  >
                    {booking.status}
                  </span>
                </div>

                <div className="vehicle-stats">
                  <div>
                    <span className="vehicle-stat-label">Date</span>
                    <span className="vehicle-stat-value">
                      {start.toLocaleDateString()}
                    </span>
                  </div>
                  <div>
                    <span className="vehicle-stat-label">Time</span>
                    <span className="vehicle-stat-value">
                      {start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} – {end.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>

                <p className="tab-note" style={{ marginTop: 12 }}>
                  Vehicle: {booking.vehicle_registration || "—"}
                  <br />
                  Connector: {booking.vehicle_connector_type || "—"}
                </p>

                {active && future && (
                  <button
                    type="button"
                    className="vehicle-action-link vehicle-action-danger"
                    onClick={() => cancelBooking(booking.id)}
                    disabled={actionId === booking.id}
                    style={{
                      border: "none",
                      background: "none",
                      padding: 0,
                      marginTop: 12,
                      cursor: actionId === booking.id ? "wait" : "pointer",
                    }}
                  >
                    {actionId === booking.id ? "Cancelling..." : "Cancel booking"}
                  </button>
                )}

                {booking.status === "CANCELLED" && (
                  <p className="tab-note" style={{ marginTop: 12 }}>
                    This booking has been cancelled.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SettingsTab({ userEmail, theme, onSetTheme, onDeleteAccount }) {
  return (
    <div className="tab-content">
      <p className="tab-subtitle">Account settings.</p>

      <div className="panel" style={{ marginBottom: 20 }}>
        <label className="auth-label">Email</label>
        <input className="auth-input" value={userEmail} disabled />
      </div>

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="settings-row">
          <div>
            <p className="settings-row-title">Appearance</p>
            <p className="tab-note">Choose how ChargeSure looks on this device.</p>
          </div>
          <div className="theme-select" role="tablist" aria-label="Theme">
            <button
              type="button"
              role="tab"
              aria-selected={theme === "light"}
              className={`theme-option ${theme === "light" ? "theme-option-active" : ""}`}
              onClick={() => onSetTheme("light")}
            >
              {"\u2600\uFE0F"} Light Theme
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={theme === "dark"}
              className={`theme-option ${theme === "dark" ? "theme-option-active" : ""}`}
              onClick={() => onSetTheme("dark")}
            >
              {"\u{1F319}"} Dark Theme
            </button>
          </div>
        </div>
      </div>

      <div className="panel danger-panel">
        <p className="settings-row-title">Delete account</p>
        <p className="tab-note" style={{ marginBottom: 14 }}>
          Permanently delete your account and all associated data. This can't be undone.
        </p>
        <button type="button" className="danger-submit" onClick={onDeleteAccount}>
          Delete my account
        </button>
      </div>
    </div>
  );
}