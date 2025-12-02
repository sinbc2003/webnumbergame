import AuthForm from "@/components/forms/AuthForm";

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md space-y-4">
        <div className="text-center">
          <p className="text-[10px] uppercase tracking-[0.5em] text-night-400">MATHGAME NETWORK</p>
          <p className="text-sm text-night-300">새 사령관 계정을 생성하세요.</p>
        </div>
        <AuthForm mode="register" />
      </div>
    </div>
  );
}

