
import { useEffect, useRef, useState } from "react";

export default function ChatBox({ token }: { token: string }) {
  const [messages, setMessages] = useState<{ sender: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = `wss://your-api-url/ws/chat?token=${token}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => [...prev, { sender: "ai", text: data.text }]);
    };

    return () => ws.current?.close();
  }, [token]);

  const sendMessage = () => {
    if (!input.trim()) return;
    setMessages((prev) => [...prev, { sender: "user", text: input }]);
    ws.current?.send(JSON.stringify({ message: input }));
    setInput("");
  };

  return (
    <div className="h-full flex flex-col p-4">
      <div className="flex-1 overflow-y-auto space-y-2 mb-4">
        {messages.map((msg, i) => (
          <div key={i} className={`text-${msg.sender === "user" ? "right" : "left"}`}>
            <span className={`inline-block p-2 rounded bg-${msg.sender === "user" ? "blue" : "gray"}-200`}>
              {msg.text}
            </span>
          </div>
        ))}
      </div>
      <div className="flex">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          className="flex-1 border rounded p-2"
          placeholder="Type a message..."
        />
        <button onClick={sendMessage} className="ml-2 bg-blue-500 text-white px-4 py-2 rounded">
          Send
        </button>
      </div>
    </div>
  );
}
