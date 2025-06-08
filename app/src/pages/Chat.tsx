import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

interface Message {
  role: "user" | "ai";
  content: string;
  meta?: {
    emotion?: string;
    mode?: string;
    is_crisis?: boolean;
    attack?: string;
  };
}

export default function ChatPage() {
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [threadId] = useState("default");

  const token = localStorage.getItem("token");

  useEffect(() => {
    if (!token) {
      navigate("/");
      return;
    }

    const wsUrl =
      (window.location.protocol === "https:" ? "wss://" : "ws://") +
      window.location.hostname +
      ":8000/chat/ws/chat";
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      socket.send(
        JSON.stringify({
          access_token: token,
          thread_id: threadId,
        })
      );
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        setMessages((prev) => [
          ...prev,
          { role: "ai", content: `Error: ${data.error}` }
        ]);
        setLoading(false);
        return;
      }
      if (data.response) {
        setMessages((prev) => [
          ...prev,
          {
            role: "ai",
            content: data.response,
            meta: {
              emotion: data.emotion,
              mode: data.mode,
              is_crisis: data.is_crisis,
              attack: data.attack,
            },
          },
        ]);
      }
      setLoading(false);
    };

    socket.onclose = (event) => {
      setConnected(false);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: `Connection closed: ${event.reason}` },
      ]);
    };

    return () => {
      socket.close();
    };
    // eslint-disable-next-line
  }, [token, threadId]);

  const sendMessage = () => {
    if (!input.trim() || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    setMessages((prev) => [...prev, { role: "user", content: input }]);
    setLoading(true);
    socketRef.current.send(JSON.stringify({ input }));
    setInput("");
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="border rounded p-4 h-[400px] overflow-y-auto bg-white space-y-2 shadow flex flex-col-reverse">
        {[...messages].reverse().map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-lg shadow text-base whitespace-pre-line ${
                msg.role === "user"
                  ? "bg-blue-100 text-blue-900"
                  : "bg-green-100 text-green-900"
              }`}
            >
              {msg.content}
              {msg.meta && (
                <div className="mt-1 text-xs text-gray-400">
                  {msg.meta.emotion && <span>Emotion: {msg.meta.emotion} </span>}
                  {msg.meta.mode && <span>Mode: {msg.meta.mode} </span>}
                  {msg.meta.is_crisis && <span className="text-red-500">Crisis detected</span>}
                  {msg.meta.attack && msg.meta.attack !== "safe" && (
                    <span className="text-orange-500"> ({msg.meta.attack})</span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <div className="text-gray-500">AI is typing...</div>}
      </div>

      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 border p-2 rounded shadow"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message..."
          disabled={!connected || loading}
        />
        <button
          className="px-4 py-2 bg-blue-500 text-white rounded shadow disabled:opacity-50"
          onClick={sendMessage}
          disabled={!connected || loading || !input.trim()}
        >
          Send
        </button>
      </div>
      {!connected && (
        <div className="mt-2 text-sm text-red-500">Connecting to AI therapist...</div>
      )}
    </div>
  );
}
          
