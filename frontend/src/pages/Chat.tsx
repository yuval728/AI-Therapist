import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

interface Message {
  role: "user" | "ai";
  content: string;
}

function ChatPage() {
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [threadId] = useState("default");

  const accessToken = localStorage.getItem("access_token");

  useEffect(() => {
    if (!accessToken) {
      navigate("/signin");
      return;
    }

    const socket = new WebSocket("ws://localhost:8000/chat/ws/chat");
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      socket.send(
        JSON.stringify({
          access_token: accessToken,
          input: "Hello",
          thread_id: threadId,
        })
      );
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        console.error("AI Error:", data.error);
        return;
      }
      setMessages((prev) => [...prev, { role: "ai", content: data.content }]);
      setLoading(false);
    };

    socket.onclose = (event) => {
      setConnected(false);
      console.warn("WebSocket closed:", event.reason);
    };

    return () => {
      socket.close();
    };
  }, [accessToken, navigate, threadId]);

  const sendMessage = () => {
    if (!input.trim() || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;

    const message: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, message]);
    setLoading(true);

    socketRef.current.send(JSON.stringify({ input }));
    setInput("");
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Therapist Chat</h1>

      <div className="border rounded p-4 h-[400px] overflow-y-auto bg-gray-50 space-y-2">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`p-2 rounded ${
              msg.role === "user" ? "bg-blue-100 text-right" : "bg-green-100 text-left"
            }`}
          >
            {msg.content}
          </div>
        ))}
        {loading && <div className="text-gray-500">Typing...</div>}
      </div>

      <div className="mt-4 flex">
        <input
          className="flex-1 border p-2 rounded"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message..."
        />
        <button
          className="ml-2 px-4 py-2 bg-blue-500 text-white rounded"
          onClick={sendMessage}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatPage;
