import { FileArchive, LogOut, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import ChatPanel from "../components/ChatPanel";
import FileDrop from "../components/FileDrop";
import InsightChart from "../components/InsightChart";
import KpiGrid from "../components/KpiGrid";
import { useAuth } from "../context/AuthContext";
import {
  askQuestion,
  createProject,
  fetchChats,
  fetchFiles,
  fetchProjects,
  generateReport,
  getSummary,
  uploadProjectFile,
} from "../services/api";

export default function Workspace() {
  const { logout } = useAuth();
  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState("");
  const [files, setFiles] = useState([]);
  const [summary, setSummary] = useState(null);
  const [chats, setChats] = useState([]);
  const [notice, setNotice] = useState("");

  const activeProject = useMemo(
    () => projects.find((project) => project.id === activeProjectId),
    [projects, activeProjectId]
  );

  async function bootstrap() {
    let loaded = await fetchProjects();
    if (loaded.length === 0) {
      const created = await createProject({
        title: "Datavault Prototype",
        description: "AI-powered dataset analytics, product prototype PDFs, and executive reporting.",
      });
      loaded = [created];
    }
    setProjects(loaded);
    setActiveProjectId((current) => current || loaded[0]?.id || "");
  }

  async function refreshProject(projectId = activeProjectId) {
    if (!projectId) return;
    const [fileList, chatList] = await Promise.all([fetchFiles(projectId), fetchChats(projectId)]);
    setFiles(fileList);
    setChats(chatList);
    try {
      setSummary(await getSummary(projectId));
    } catch {
      setSummary(null);
    }
  }

  useEffect(() => {
    bootstrap();
  }, []);

  useEffect(() => {
    refreshProject(activeProjectId);
  }, [activeProjectId]);

  async function addProject() {
    const title = window.prompt("Project title", "New analysis project");
    if (!title) return;
    const project = await createProject({ title, description: "Created from Datavault workspace" });
    setProjects((current) => [project, ...current]);
    setActiveProjectId(project.id);
  }

  async function handleUpload(file, purpose) {
    await uploadProjectFile(activeProjectId, file, purpose);
    setNotice(purpose === "prototype_pdf" ? "Prototype PDF attached." : "Dataset uploaded and ready for analysis.");
    await refreshProject();
  }

  async function handleAsk(question) {
    const chat = await askQuestion(activeProjectId, question);
    setChats((current) => [...current, chat]);
  }

  async function handleReport() {
    const report = await generateReport(activeProjectId);
    setNotice(`Report generated: ${report.report_path}`);
  }

  const prototypePdf = files.find((file) => file.purpose === "prototype_pdf");
  const datasets = files.filter((file) => file.purpose === "dataset");

  return (
    <main className="workspace-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <ShieldCheck size={24} />
          <div>
            <strong>Datavault</strong>
            <span>AI analytics</span>
          </div>
        </div>
        <button className="new-project" onClick={addProject} type="button">
          <Plus size={17} />
          New project
        </button>
        <nav className="project-list">
          {projects.map((project) => (
            <button
              className={project.id === activeProjectId ? "active" : ""}
              key={project.id}
              onClick={() => setActiveProjectId(project.id)}
              type="button"
            >
              <strong>{project.title}</strong>
              <span>{project.description || "Analytics workspace"}</span>
            </button>
          ))}
        </nav>
        <button className="logout-button" onClick={logout} type="button">
          <LogOut size={17} />
          Logout
        </button>
      </aside>

      <section className="workspace-main">
        <header className="topbar">
          <div>
            <span className="eyebrow">Product workspace</span>
            <h1>{activeProject?.title || "Datavault Prototype"}</h1>
          </div>
          <div className="topbar-actions">
            <button onClick={() => refreshProject()} title="Refresh workspace" type="button">
              <RefreshCw size={17} />
            </button>
            <button className="report-action" onClick={handleReport} disabled={!summary} type="button">
              <FileArchive size={17} />
              Generate report
            </button>
          </div>
        </header>

        {notice && <div className="notice">{notice}</div>}

        <KpiGrid summary={summary} />

        <section className="upload-grid">
          <FileDrop
            title="Upload CSV or Excel"
            subtitle="Analyze rows, KPIs, missing values, and trends"
            accept=".csv,.xlsx,.xls"
            purpose="dataset"
            onUpload={handleUpload}
          />
          <FileDrop
            title={prototypePdf ? "Replace prototype PDF" : "Attach prototype PDF"}
            subtitle={prototypePdf ? prototypePdf.file_name : "Keep the product prototype beside the analysis"}
            accept=".pdf"
            purpose="prototype_pdf"
            onUpload={handleUpload}
          />
        </section>

        <section className="content-grid">
          <InsightChart data={summary?.chart_data || []} />
          <section className="files-panel">
            <div className="panel-heading">
              <h2>Project Assets</h2>
              <span>{files.length} files</span>
            </div>
            <div className="asset-list">
              {files.length === 0 && <p className="empty-state">No assets uploaded yet.</p>}
              {files.map((file) => (
                <div className="asset-row" key={file.id}>
                  <span>{file.purpose === "prototype_pdf" ? "PDF" : "DATA"}</span>
                  <div>
                    <strong>{file.file_name}</strong>
                    <small>{Math.round(file.file_size / 1024).toLocaleString()} KB</small>
                  </div>
                </div>
              ))}
            </div>
            <div className="recommendations">
              <h3>Recommendations</h3>
              {(summary?.recommendations || ["Upload a dataset to unlock AI-assisted recommendations."]).map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
            {datasets.length > 0 && <p className="dataset-count">{datasets.length} dataset upload ready for chat.</p>}
          </section>
        </section>

        <ChatPanel chats={chats} onAsk={handleAsk} disabled={!summary} />
      </section>
    </main>
  );
}
