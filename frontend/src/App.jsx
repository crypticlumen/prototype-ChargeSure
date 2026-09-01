import { useState, useEffect } from 'react'
import heroImg from './assets/hero.png'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import './App.css'
import { registerUser, loginUser, getSavedSession, saveSession, clearSession, updateUsername } from './api/client';


const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: "\u{1F4CA}" },
  { key: "route", label: "Plan Route", icon: "\u{1F5FA}\uFE0F" },
  { key: "vehicles", label: "Vehicles", icon: "\u{1F697}" },
  { key: "bookings", label: "Bookings", icon: "\u{1F4C5}" },
  { key: "settings", label: "Settings", icon: "\u2699\uFE0F" },
];

const VEHICLE_TYPES = ["2-Wheeler", "3-Wheeler", "4-Wheeler"];
const CONNECTOR_TYPES = ["Type 2", "CCS2", "Bharat AC001", "Bharat DC001"];

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

// Fallback display name from an email, used only if no stored name is found
// (e.g. signing in on a browser that never saw the sign-up for this email).
const getFallbackName = (email) => {
  if (!email) return "there";
  const prefix = email.split("@")[0];
  return prefix.charAt(0).toUpperCase() + prefix.slice(1);
};

const NAME_STORAGE_PREFIX = "chargesure_name_";

// TODO: this localStorage lookup is a stand-in for a real backend. Once
// sign-up/sign-in hit an actual API, the name should come back with the
// user record instead of being looked up client-side like this.
const getStoredName = (email) => {
  try {
    return localStorage.getItem(NAME_STORAGE_PREFIX + email);
  } catch {
    return null;
  }
};

const setStoredName = (email, name) => {
  try {
    localStorage.setItem(NAME_STORAGE_PREFIX + email, name);
  } catch {
    // ignore storage errors (e.g. private browsing)
  }
};

export default function App() {
  // ---- theme ----
  const [theme, setTheme] = useState("dark"); // "dark" | "light"
  const themeClass = theme === "light" ? "theme-light" : "";
  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  // ---- auth state ----
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userEmail, setUserEmail] = useState("");
<<<<<<< HEAD
  const [username, setUsername] = useState("");
=======
  const [userName, setUserName] = useState("");
>>>>>>> 0e45001fd3805e9d054a8565158b3a7cb2069431
  const [mode, setMode] = useState("signin");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notRobot, setNotRobot] = useState(false);
  const [errors, setErrors] = useState({});
  const [authToken, setAuthToken] = useState(null);
  const [authError, setAuthError] = useState(""); 
  const [sessionChecked, setSessionChecked] = useState(false);

  // ---- app state (post-login) ----
  const [activeTab, setActiveTab] = useState("dashboard");
  const [vehicles, setVehicles] = useState([]);
  const [activeVehicleId, setActiveVehicleId] = useState(null);
  const [vehicleForm, setVehicleForm] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [showDeleteAccount, setShowDeleteAccount] = useState(false);

  const activeVehicle = vehicles.find((v) => v.id === activeVehicleId) || null;
<<<<<<< HEAD
  const displayName = username || getDisplayName(userEmail);

  // ---- restore session on reload ----
  useEffect(() => {
    const saved = getSavedSession();
    if (saved?.token) {
      setAuthToken(saved.token);
      setUserEmail(saved.email || "");
      setUsername(saved.username || "");
      setIsAuthenticated(true);
    }
    setSessionChecked(true);
  }, []);

  // ---- restore vehicles for the logged-in user ----
  useEffect(() => {
    if (!isAuthenticated || !userEmail) return;
    const raw = localStorage.getItem(`chargesure_vehicles_${userEmail}`);
    if (raw) {
      try {
        setVehicles(JSON.parse(raw));
      } catch {
        // ignore corrupt cache
      }
    }
  }, [isAuthenticated, userEmail]);

  // ---- persist vehicles whenever they change ----
  useEffect(() => {
    if (!isAuthenticated || !userEmail) return;
    localStorage.setItem(`chargesure_vehicles_${userEmail}`, JSON.stringify(vehicles));
  }, [vehicles, isAuthenticated, userEmail]);
=======
  const displayName = userName || getFallbackName(userEmail);
>>>>>>> 0e45001fd3805e9d054a8565158b3a7cb2069431

  // ---- auth handlers ----
  const validate = () => {
    const next = {};
<<<<<<< HEAD
    if (mode === "signup" && !username.trim()) next.username = "Username is required.";
=======

    if (mode === "signup" && !fullName.trim()) {
      next.fullName = "Full name is required.";
    }
>>>>>>> 0e45001fd3805e9d054a8565158b3a7cb2069431

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

<<<<<<< HEAD
  const handleSubmit = async (e) => {
  e.preventDefault();
  if (!validate()) return;

  setAuthError("");
  try {
    const data =
      mode === "signup"
        ? await registerUser({ username: username.trim(), email: email.trim(), password })
        : await loginUser({ email: email.trim(), password });

    const resolvedUsername = mode === "signup" ? username.trim() : data.username || "";

    setAuthToken(data.access_token);
    setUserEmail(email.trim());
    setUsername(resolvedUsername);
    setIsAuthenticated(true);
    saveSession({ token: data.access_token, email: email.trim(), username: resolvedUsername });
  } catch (err) {
    setAuthError(err.message || "Something went wrong. Try again.");
  }
};

  const handleGoogleContinue = () => {
    setUserEmail("google-user@example.com");
    setUsername("");
=======
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    const trimmedEmail = email.trim();

    if (mode === "signup") {
      const name = fullName.trim();
      setStoredName(trimmedEmail, name);
      setUserName(name);
    } else {
      setUserName(getStoredName(trimmedEmail) || getFallbackName(trimmedEmail));
    }

    setUserEmail(trimmedEmail);
    setIsAuthenticated(true);
  };

  const handleGoogleContinue = () => {
    const demoEmail = "google-user@example.com";
    setUserEmail(demoEmail);
    setUserName(getStoredName(demoEmail) || "Google User");
>>>>>>> 0e45001fd3805e9d054a8565158b3a7cb2069431
    setIsAuthenticated(true);
  };

  const handleSaveUsername = async (newUsername) => {
    const trimmed = newUsername.trim();
    if (!trimmed) return { ok: false, error: "Username can't be empty." };

    try {
      if (authToken) {
        await updateUsername(trimmed, authToken);
      }
      setUsername(trimmed);
      saveSession({ token: authToken, email: userEmail, username: trimmed });
      return { ok: true };
    } catch (err) {
      // Backend endpoint may not exist yet (e.g. during the Google sign-in
      // flow, or before /auth/me PATCH is implemented) — save locally so
      // the UI still reflects the change, but flag it wasn't synced.
      setUsername(trimmed);
      saveSession({ token: authToken, email: userEmail, username: trimmed });
      return { ok: true, warning: "Saved locally — couldn't sync to the server yet." };
    }
  };

  const switchMode = () => {
    setMode((m) => (m === "signin" ? "signup" : "signin"));
    setErrors({});
  };

  const resetAllState = () => {
    clearSession();
    setIsAuthenticated(false);
    setUserEmail("");
<<<<<<< HEAD
    setUsername("");
=======
    setUserName("");
    setFullName("");
>>>>>>> 0e45001fd3805e9d054a8565158b3a7cb2069431
    setEmail("");
    setPassword("");
    setNotRobot(false);
    setErrors({});
    setActiveTab("dashboard");
    setVehicles([]);
    setActiveVehicleId(null);
  };

  const handleLogout = () => resetAllState();

  const handleDeleteAccount = () => {
    // TODO: call the backend's delete-account endpoint here once it exists.
    // This should permanently remove the user's data server-side, not just
    // reset local state.
    if (userEmail) localStorage.removeItem(`chargesure_vehicles_${userEmail}`);
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
      const newVehicle = { ...vehicleForm, id: Date.now() };
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
  if (!sessionChecked) {
    return null; // or a small loading spinner
  }
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
            {mode === "signup" && (
              <>
<<<<<<< HEAD
                <label className="auth-label" htmlFor="username">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  className="auth-input"
                  placeholder="Choose a username"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                {errors.username && <p className="auth-error">{errors.username}</p>}
              </>
            )}

            <label className="auth-label" htmlFor="email">
=======
                <label className="auth-label" htmlFor="fullName">
                  Full name
                </label>
                <input
                  id="fullName"
                  type="text"
                  className="auth-input"
                  placeholder="e.g. Kavya Sharma"
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
                {errors.fullName && <p className="auth-error">{errors.fullName}</p>}
              </>
            )}

            <label className="auth-label" htmlFor="email" style={mode === "signup" ? { marginTop: 16 } : undefined}>
>>>>>>> 0e45001fd3805e9d054a8565158b3a7cb2069431
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
            {authError && <p className="auth-error">{authError}</p>}

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
          />
        )}

        {activeTab === "route" && <RouteTab vehicles={vehicles} authToken={authToken} />}

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

        {activeTab === "bookings" && <BookingsTab />}

        {activeTab === "settings" && (
          <SettingsTab
            userEmail={userEmail}
            username={username}
            onSaveUsername={handleSaveUsername}
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

<<<<<<< HEAD

=======
>>>>>>> 0e45001fd3805e9d054a8565158b3a7cb2069431
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

function DashboardTab({ vehicles, activeVehicle, goTo, displayName }) {
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
          <span className="stat-value">0</span>
          <span className="stat-label">Upcoming bookings</span>
        </div>
      </div>

      <div className="quick-actions">
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

function RouteTab({ vehicles }) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [vehicleId, setVehicleId] = useState(vehicles[0]?.id || "");

  return (
    <div className="tab-content">
      <p className="tab-subtitle">Plan a trip with reliability-scored charging stops.</p>
      <div className="panel">
        <label className="auth-label">Starting point</label>
        <input
          className="auth-input"
          placeholder="Current location"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
        />
        <label className="auth-label" style={{ marginTop: 14 }}>
          Destination
        </label>
        <input
          className="auth-input"
          placeholder="Where are you headed?"
          value={to}
          onChange={(e) => setTo(e.target.value)}
        />
        <label className="auth-label" style={{ marginTop: 14 }}>
          Vehicle
        </label>
        <select
          className="auth-input"
          value={vehicleId}
          onChange={(e) => setVehicleId(e.target.value)}
        >
          {vehicles.length === 0 && <option value="">Add a vehicle first</option>}
          {vehicles.map((v) => (
            <option key={v.id} value={v.id}>
              {v.brand} {v.model} ({v.regNumber})
            </option>
          ))}
        </select>
        <button type="button" className="auth-submit" style={{ marginTop: 20 }}>
          Find Route
        </button>
      </div>
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

function BookingsTab() {
  return (
    <div className="tab-content">
      <p className="tab-subtitle">Your upcoming and past charging slots.</p>
      <div className="empty-state">
        <p>No bookings yet.</p>
        <p className="tab-note">Bookings you make from Plan Route will show up here.</p>
      </div>
    </div>
  );
}

function SettingsTab({ userEmail, username, onSaveUsername, theme, onSetTheme, onDeleteAccount }) {
  const [isEditingUsername, setIsEditingUsername] = useState(false);
  const [draftUsername, setDraftUsername] = useState(username || "");
  const [usernameError, setUsernameError] = useState("");
  const [usernameNotice, setUsernameNotice] = useState("");

  const startEditing = () => {
    setDraftUsername(username || "");
    setUsernameError("");
    setUsernameNotice("");
    setIsEditingUsername(true);
  };

  const cancelEditing = () => {
    setIsEditingUsername(false);
    setUsernameError("");
  };

  const submitUsername = async (e) => {
    e.preventDefault();
    setUsernameError("");
    setUsernameNotice("");
    const result = await onSaveUsername(draftUsername);
    if (!result.ok) {
      setUsernameError(result.error || "Couldn't save username.");
      return;
    }
    if (result.warning) setUsernameNotice(result.warning);
    setIsEditingUsername(false);
  };

  return (
    <div className="tab-content">
      <p className="tab-subtitle">Account settings.</p>

      <div className="panel" style={{ marginBottom: 20 }}>
        <label className="auth-label">Username</label>
        {isEditingUsername ? (
          <form onSubmit={submitUsername}>
            <input
              className="auth-input"
              value={draftUsername}
              autoFocus
              placeholder="Choose a username"
              onChange={(e) => setDraftUsername(e.target.value)}
            />
            {usernameError && <p className="auth-error">{usernameError}</p>}
            <div className="settings-row" style={{ marginTop: 10 }}>
              <button type="submit" className="auth-submit" style={{ width: "auto" }}>
                Save
              </button>
              <button type="button" className="vehicle-action-link" onClick={cancelEditing}>
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <div className="settings-row">
            <span>{username || "No username set"}</span>
            <button type="button" className="vehicle-action-link" onClick={startEditing}>
              {username ? "Edit" : "Add username"}
            </button>
          </div>
        )}
        {!isEditingUsername && usernameNotice && <p className="tab-note">{usernameNotice}</p>}
      </div>

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