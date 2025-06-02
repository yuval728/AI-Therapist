
import { useState, useEffect } from "react";
import Login from "./pages/Login";
import ChatBox from "./components/ChatBox";
import OAuthCallback from "./pages/OAuthCallback";
import { getMe } from "./api";
import { BrowserRouter, Routes, Route } from "react-router-dom";

function App() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("token");
    if (saved) {
      getMe(saved)
        .then((user) => {
          setToken(saved);
          setEmail(user.email);
        })
        .catch(() => localStorage.removeItem("token"));
    }
  }, []);

  const handleAuth = (jwt: string, userEmail: string) => {
    setToken(jwt);
    setEmail(userEmail);
    localStorage.setItem("token", jwt);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={token ? <ChatBox token={token} /> : <Login onAuth={handleAuth} />} />
        <Route path="/oauth/callback" element={<OAuthCallback onAuth={handleAuth} />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
