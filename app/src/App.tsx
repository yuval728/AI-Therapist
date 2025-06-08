
import { useState, useEffect } from "react";
import Login from "./pages/Login";
import ChatBox from "./components/ChatBox";
import ChatPage from "./pages/Chat";
import OAuthCallback from "./pages/OAuthCallback";
import { getMe } from "./api";
import { BrowserRouter, Routes, Route } from "react-router-dom";

function App() {

  const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"));
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      getMe(token)
        .then((user) => setEmail(user.email))
        .catch(() => {
          setToken(null);
          setEmail(null);
          localStorage.removeItem("token");
        });
    }
  }, [token]);

  const handleAuth = (jwt: string, userEmail: string) => {
    setToken(jwt);
    setEmail(userEmail);
    localStorage.setItem("token", jwt);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50">
      <header className="py-6 mb-4 shadow bg-white">
        <h1 className="text-3xl font-bold text-blue-700 tracking-tight">AI Therapist</h1>
        {email && <div className="text-gray-500 text-sm mt-1">Signed in as {email}</div>}
      </header>
      <main className="max-w-2xl mx-auto">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={token ? <ChatPage /> : <Login onAuth={handleAuth} />} />
            <Route path="/oauth/callback" element={<OAuthCallback onAuth={handleAuth} />} />
          </Routes>
        </BrowserRouter>
      </main>
    </div>
  );
}

export default App;
