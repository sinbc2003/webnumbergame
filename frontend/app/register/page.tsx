import TopNav from "@/components/TopNav";
import AuthForm from "@/components/forms/AuthForm";

export default function RegisterPage() {
  return (
    <div>
      <TopNav />
      <main className="mx-auto flex max-w-6xl justify-center px-6 py-16">
        <AuthForm mode="register" />
      </main>
    </div>
  );
}

