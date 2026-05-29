import { Send } from "lucide-react";
import { useState } from "react";
import AiResult, { parseAiResult } from "./AiResult";

export default function ChatPanel({ chats, onAsk, disabled }) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    try {
      await onAsk(question.trim());
      setQuestion("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="chat-panel">
      <div className="panel-heading">
        <h2>Ask Datavault</h2>
        <span>{chats.length} messages</span>
      </div>
      <div className="chat-list">
        {chats.length === 0 ? (
          <p className="empty-state">Upload a dataset, then ask about totals, averages, missing values, or records.</p>
        ) : (
          chats.map((chat) => {
            const aiResult = parseAiResult(chat);

            return (
              <div className="chat-pair" key={chat.id}>
                <p className="user-message">{chat.user_message}</p>
                <div className="ai-message">
                  {aiResult ? <AiResult result={aiResult} /> : <p>{chat.ai_response}</p>}
                </div>
              </div>
            );
          })
        )}
      </div>
      <form className="chat-form" onSubmit={submit}>
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about the dataset"
          disabled={disabled || busy}
        />
        <button type="submit" disabled={disabled || busy} title="Send question">
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}
