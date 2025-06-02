
import { useEffect } from "react";
import { getMe } from "../api";
import { useNavigate } from "react-router-dom";

export default function OAuthCallback({ onAuth }: { onAuth: (token: string, email: string) => void }) {
  const navigate = useNavigate();

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.substring(1));
    const token = hash.get("access_token");
    if (!token) return;

    getMe(token)
      .then((user) => {
        onAuth(token, user.email);
        localStorage.setItem("token", token);
        navigate("/");
      })
      .catch(() => alert("OAuth verification failed"));
  }, []);

  return <div className="p-4">Signing you in...</div>;
}
