import { LockKeyhole, Vault } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function AuthPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("register");
  const [form, setForm] = useState({
    full_name: "Datavault Founder",
    email: "founder@datavault.ai",
    password: "password123",
  });
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      if (mode === "register") {
        await register(form);
      } else {
        await login({ email: form.email, password: form.password });
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication failed");
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <div className="brand-lockup">
          <span className="brand-mark">
            <Vault size={28} />
          </span>
          <div>
            <h1>Datavault</h1>
            <p>AI analytics workspace</p>
          </div>
        </div>

        <div className="mode-switch">
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")} type="button">
            Register
          </button>
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")} type="button">
            Login
          </button>
        </div>

        <form onSubmit={submit} className="auth-form">
          {mode === "register" && (
            <label>
              Full name
              <input value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
            </label>
          )}
          <label>
            Email
            <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
            />
          </label>
          {error && <p className="error-text">{error}</p>}
          <button className="primary-action" type="submit">
            <LockKeyhole size={18} />
            {mode === "register" ? "Create workspace" : "Enter workspace"}
          </button>
        </form>
      </section>
    </main>
  );
}
