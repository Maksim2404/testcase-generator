import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

const API = "/api";

/* ---- tiny helpers ---- */
function cx(...parts) { return parts.filter(Boolean).join(" "); }

async function apiFetch(path, opts = {}) {
    const res = await fetch(`${API}${path}`, opts);
    const text = await res.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
    if (!res.ok) {
        const msg = (data && (data.message || data.detail)) || text || "Request failed";
        const details = typeof data === "object" ? JSON.stringify(data) : text;
        const err = new Error(`${res.status}: ${msg}`);
        err.status = res.status;
        err.payload = details;
        throw err;
    }
    return data;
}

function renderMarkdown(md) {
    if (!md) return "";
    let html = md;
    html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    html = html.replace(/^######\s?(.*)$/gm, "<h6>$1</h6>");
    html = html.replace(/^#####\s?(.*)$/gm, "<h5>$1</h5>");
    html = html.replace(/^####\s?(.*)$/gm, "<h4>$1</h4>");
    html = html.replace(/^###\s?(.*)$/gm, "<h3>$1</h3>");
    html = html.replace(/^##\s?(.*)$/gm, "<h2>$1</h2>");
    html = html.replace(/^#\s?(.*)$/gm, "<h1>$1</h1>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    html = html.replace(/\*(.+?)\*/g, "<i>$1</i>");
    html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_m, _lang, code) => {
        return `<pre class="code"><code>${code.replace(/&/g,"&amp;")}</code></pre>`;
    });
    html = html.replace(/\n{2,}/g, "</p><p>");
    html = `<p>${html.replace(/\n/g, "<br/>")}</p>`;
    return html;
}

/* ---- theming ---- */
const light = {
    pageBg: "#fff",
    text: "#111",
    cardBg: "#fff",
    border: "#e5e7eb",
    label: "#374151",
    inputBg: "#fff",
    inputBorder: "#d1d5db",
    monoBg: "#f8fafc",
    primary: "#10b981",
    secondaryBg: "#f3f4f6",
    secondaryText: "#111",
    warn: "#f59e0b",
    danger: "#ef4444",
    okBg: "#ecfdf5",
    okBorder: "#a7f3d0",
    okText: "#065f46",
    errBg: "#fee2e2",
    errBorder: "#fca5a5",
    errText: "#991b1b",
    tabActiveBg: "#111",
    tabInactiveBg: "#f3f4f6",
    tabActiveText: "#fff",
    tabInactiveText: "#111",
};
const dark = {
    pageBg: "#0b0f12",
    text: "#e5e7eb",
    cardBg: "#12181c",
    border: "#1f2937",
    label: "#9ca3af",
    inputBg: "#0f1418",
    inputBorder: "#374151",
    monoBg: "#0f1418",
    primary: "#10b981",
    secondaryBg: "#1f2937",
    secondaryText: "#e5e7eb",
    warn: "#f59e0b",
    danger: "#ef4444",
    okBg: "#0f3c2f",
    okBorder: "#1d6b51",
    okText: "#b8f3d8",
    errBg: "#3b1111",
    errBorder: "#7f1d1d",
    errText: "#fecaca",
    tabActiveBg: "#10b981",
    tabInactiveBg: "#1f2937",
    tabActiveText: "#0b0f12",
    tabInactiveText: "#e5e7eb",
};

function App() {
    // theme
    const [darkMode, setDarkMode] = useState(() => {
        const saved = localStorage.getItem("qa.dark");
        if (saved === "1") return true;
        if (saved === "0") return false;
        return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    });
    useEffect(() => {
        localStorage.setItem("qa.dark", darkMode ? "1" : "0");
    }, [darkMode]);
    const theme = darkMode ? dark : light;

    // form state
    const [useAI, setUseAI] = useState(true);
    const [appName, setAppName] = useState("");
    const [area, setArea] = useState("");
    const [suite, setSuite] = useState("Regression");
    const [priority, setPriority] = useState("P2");
    const [notes, setNotes] = useState("");

    // app state
    const [markdown, setMarkdown] = useState("");
    const [suggestedId, setSuggestedId] = useState("");
    const [activeTab, setActiveTab] = useState("md"); // 'md' | 'rendered'
    const [isBusy, setIsBusy] = useState(false);
    const [okBanner, setOkBanner] = useState(null);
    const [errBanner, setErrBanner] = useState(null);
    const [lintIssues, setLintIssues] = useState([]);

    const canGenerate = appName && area && suite && priority && !isBusy;

    useEffect(() => {
        (async () => {
            try {
                if (!appName || !area) return;
                const data = await apiFetch(`/suggest-id?app=${encodeURIComponent(appName)}&area=${encodeURIComponent(area)}`);
                setSuggestedId(data.next_id || "");
            } catch {
                setSuggestedId("");
            }
        })();
    }, [appName, area]);

    /* styles bound to theme */
    const styles = {
        page: { fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif", padding: 16, color: theme.text, background: theme.pageBg, minHeight: "100vh" },
        row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" },
        card: { border: `1px solid ${theme.border}`, borderRadius: 10, padding: 14, background: theme.cardBg },
        label: { fontSize: 12, fontWeight: 600, color: theme.label, display: "block", marginBottom: 6 },
        input: { width: "100%", padding: "9px 10px", borderRadius: 8, border: `1px solid ${theme.inputBorder}`, background: theme.inputBg, color: theme.text },
        textarea: { width: "100%", height: 180, padding: 12, borderRadius: 8, border: `1px solid ${theme.inputBorder}`, fontFamily: "ui-monospace, Menlo, Consolas, monospace", background: theme.monoBg, color: theme.text },
        btnRow: { display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 8 },
        btn: { padding: "9px 12px", borderRadius: 999, border: "1px solid transparent", fontWeight: 600, cursor: "pointer" },
        btnPrimary: { background: theme.primary, color: "#fff" },
        btnSecondary: { background: theme.secondaryBg, color: theme.secondaryText },
        btnWarn: { background: theme.warn, color: theme.pageBg },
        btnDanger: { background: theme.danger, color: "#fff" },
        disabled: { opacity: .6, cursor: "not-allowed" },
        bannerOk: { background: theme.okBg, border: `1px solid ${theme.okBorder}`, color: theme.okText, padding: 10, borderRadius: 8, marginBottom: 10 },
        bannerErr: { background: theme.errBg, border: `1px solid ${theme.errBorder}`, color: theme.errText, padding: 10, borderRadius: 8, marginBottom: 10 },
        tabs: { display: "flex", gap: 8, borderBottom: `1px solid ${theme.border}`, marginBottom: 8 },
        tab: (active) => ({ padding: "8px 10px", borderRadius: "10px 10px 0 0", background: active ? theme.tabActiveBg : theme.tabInactiveBg, color: active ? theme.tabActiveText : theme.tabInactiveText, cursor: "pointer", fontWeight: 600 }),
        previewPane: { border: `1px solid ${theme.border}`, borderRadius: 10, padding: 12, minHeight: 280, background: theme.cardBg, color: theme.text },
        hint: { fontSize: 12, color: theme.label, marginTop: 6 },
        headerBar: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 },
        headerRight: { display: "flex", gap: 8, alignItems: "center" }
    };

    async function handleGenerate() {
        if (!canGenerate) return;
        setOkBanner(null); setErrBanner(null); setLintIssues([]);
        setIsBusy(true);
        try {
            const payload = { app: appName, area, suite, priority, notes };
            const data = await apiFetch(`/generate${useAI ? "" : "?mode=stub"}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const md = data.markdown || "";
            setMarkdown(md);
            const lint = await apiFetch("/lint", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ markdown: md }),
            });
            if (lint.markdown) setMarkdown(lint.markdown);
            setLintIssues(Array.isArray(lint.errors) ? lint.errors : []);
            setActiveTab("md");
        } catch (e) {
            setErrBanner({ status: e.status || 500, message: e.message || "Generate failed" });
        } finally {
            setIsBusy(false);
        }
    }

    async function handleLint() {
        if (!markdown) return;
        setOkBanner(null); setErrBanner(null);
        try {
            const lint = await apiFetch("/lint", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ markdown }),
            });
            if (lint.markdown) setMarkdown(lint.markdown);
            setLintIssues(Array.isArray(lint.errors) ? lint.errors : []);
        } catch (e) {
            setErrBanner({ status: e.status || 500, message: e.message || "Lint failed" });
        }
    }

    async function handleCreateMR() {
        if (!markdown) return;
        setOkBanner(null); setErrBanner(null);
        setIsBusy(true);
        try {
            await handleLint(); // ensure normalized YAML
            const payload = { app: appName, area, markdown, preferred_id: suggestedId || undefined };
            const data = await apiFetch("/create-mr", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            setOkBanner({ title: "Merge Request opened", link: data.mr_url });
            if (data.mr_url) window.open(data.mr_url, "_blank");
        } catch (e) {
            setErrBanner({ status: e.status || 500, message: e.message || "Create MR failed" });
        } finally {
            setIsBusy(false);
        }
    }

    function handleCopy() {
        if (!markdown) return;
        navigator.clipboard.writeText(markdown).then(() => {
            setOkBanner({ title: "Markdown copied to clipboard" });
            setTimeout(() => setOkBanner(null), 1500);
        });
    }

    function handleClear() {
        setNotes(""); setMarkdown(""); setLintIssues([]); setOkBanner(null); setErrBanner(null);
    }

    const rendered = useMemo(() => ({ __html: renderMarkdown(markdown) }), [markdown]);

    return (
        <div style={styles.page}>
            <div style={styles.headerBar}>
                <h2 style={{ margin: 0 }}>QA Testcase Assistant</h2>
                <div style={styles.headerRight}>
                    <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
                        <input type="checkbox" checked={useAI} onChange={e=>setUseAI(e.target.checked)} />
                        Use AI
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
                        <input type="checkbox" checked={darkMode} onChange={e=>setDarkMode(e.target.checked)} />
                        Dark
                    </label>
                </div>
            </div>

            {okBanner && (
                <div style={styles.bannerOk}>
                    <b>Success:</b> {okBanner.title}
                    {" "}
                    {okBanner.link && <a href={okBanner.link} target="_blank" rel="noreferrer">Open MR</a>}
                </div>
            )}
            {errBanner && (
                <div style={styles.bannerErr}>
                    <b>Error {errBanner.status}:</b> {String(errBanner.message || "")}
                </div>
            )}

            <div style={styles.row}>
                {/* left: form */}
                <div style={styles.card}>
                    <div>
                        <label style={styles.label}>App *</label>
                        <input style={styles.input} value={appName} onChange={e=>setAppName(e.target.value)} placeholder="e.g., AppName" />
                    </div>
                    <div style={{ height: 10 }} />
                    <div>
                        <label style={styles.label}>Area *</label>
                        <input style={styles.input} value={area} onChange={e=>setArea(e.target.value)} placeholder="e.g., Login" />
                    </div>
                    <div style={{ height: 10 }} />
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                        <div>
                            <label style={styles.label}>Suite *</label>
                            <input style={styles.input} value={suite} onChange={e=>setSuite(e.target.value)} placeholder="e.g., Regression" />
                        </div>
                        <div>
                            <label style={styles.label}>Priority *</label>
                            <input style={styles.input} value={priority} onChange={e=>setPriority(e.target.value)} placeholder="e.g., P2" />
                        </div>
                    </div>
                    <div style={{ height: 10 }} />
                    <div>
                        <label style={styles.label}>Notes</label>
                        <textarea style={styles.textarea} value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Describe the scenario, data, edge cases…" />
                        <div style={styles.hint}>* Required fields. Suggested next ID: <b>{suggestedId || "…"}</b></div>
                    </div>

                    <div style={styles.btnRow}>
                        <button
                            onClick={handleGenerate}
                            disabled={!canGenerate}
                            style={{ ...styles.btn, ...styles.btnPrimary, ...(canGenerate ? {} : styles.disabled) }}
                            title={!canGenerate ? "Fill required fields" : "Generate"}
                        >
                            {isBusy ? "Generating…" : "Generate"}
                        </button>
                        <button onClick={handleLint} disabled={!markdown} style={{ ...styles.btn, ...styles.btnSecondary, ...(!markdown ? styles.disabled : {}) }}>
                            Lint
                        </button>
                        <button onClick={handleClear} style={{ ...styles.btn, ...styles.btnSecondary }}>
                            Clear
                        </button>
                    </div>

                    {lintIssues.length > 0 && (
                        <div style={{ marginTop: 12, padding: 10, border: `1px solid ${theme.warn}`, background: darkMode ? "#3b2e12" : "#fffbeb", borderRadius: 8 }}>
                            <b>Lint warnings:</b>
                            <ul style={{ margin: "6px 0 0 20px" }}>
                                {lintIssues.map((e, i) => <li key={i}>{String(e)}</li>)}
                            </ul>
                        </div>
                    )}
                </div>

                {/* right: preview/editor */}
                <div style={styles.card}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                        <div style={styles.tabs}>
                            <div style={styles.tab(activeTab === "md")} onClick={() => setActiveTab("md")}>📝 Markdown</div>
                            <div style={styles.tab(activeTab === "rendered")} onClick={() => setActiveTab("rendered")}>👀 Rendered</div>
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                            <button onClick={handleCopy} disabled={!markdown} style={{ ...styles.btn, ...styles.btnSecondary, ...(!markdown ? styles.disabled : {}) }}>
                                Copy
                            </button>
                            <button
                                onClick={handleCreateMR}
                                disabled={!markdown || isBusy}
                                style={{ ...styles.btn, ...styles.btnWarn, ...((!markdown || isBusy) ? styles.disabled : {}) }}
                                title={!markdown ? "Generate or paste a case first" : "Open Merge Request"}
                            >
                                {isBusy ? "Working…" : "Create MR"}
                            </button>
                        </div>
                    </div>

                    {activeTab === "md" ? (
                        <textarea
                            style={{ ...styles.textarea, height: 360 }}
                            value={markdown}
                            onChange={e => setMarkdown(e.target.value)}
                            placeholder="Your test case Markdown will appear here…"
                        />
                    ) : (
                        <div style={styles.previewPane} dangerouslySetInnerHTML={rendered} />
                    )}
                </div>
            </div>
        </div>
    );
}

createRoot(document.getElementById("root")).render(<App />);