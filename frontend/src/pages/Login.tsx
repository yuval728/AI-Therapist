
import { useState } from "react";
import { signIn, signUp, getOAuthURL } from "../api";

export default function Login({ onAuth }: { onAuth: (token: string, email: string) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignup, setIsSignup] = useState(false);

  const handleSubmit = async () => {
    try {
      const res = isSignup ? await signUp(email, password) : await signIn(email, password);
      onAuth(res.access_token, res.email);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Auth error");
    }
  };

  const handleGoogleLogin = async () => {
    try {
      const url = await getOAuthURL("google");
      window.location.href = url;
    } catch {
      alert("OAuth failed");
    }
  };

  return (
    <div className="p-4 max-w-sm mx-auto space-y-4">
      <h2 className="text-xl font-bold">{isSignup ? "Sign Up" : "Sign In"}</h2>
      <input className="w-full border p-2 rounded" placeholder="Email" onChange={(e) => setEmail(e.target.value)} />
      <input className="w-full border p-2 rounded" type="password" placeholder="Password" onChange={(e) => setPassword(e.target.value)} />
      <button className="w-full bg-blue-500 text-white p-2 rounded" onClick={handleSubmit}>
        {isSignup ? "Create Account" : "Login"}
      </button>
      <button
        onClick={handleGoogleLogin}
        className="w-full flex items-center justify-center gap-2 border border-gray-300 rounded p-2 mt-4 hover:bg-gray-100"
      >
        <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/google/google-original.svg" className="w-5 h-5" />
        Continue with Google
      </button>
      <p className="text-center text-sm">
        {isSignup ? "Already have an account?" : "Need an account?"}{" "}
        <button className="text-blue-500 underline" onClick={() => setIsSignup(!isSignup)}>
          {isSignup ? "Login" : "Sign up"}
        </button>
      </p>
    </div>
  );
}
