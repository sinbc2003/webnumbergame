import TopNav from "@/components/TopNav";
import AuthForm from "@/components/forms/AuthForm";

export default function RegisterPage() {
  return (
    <TopNav pageTitle="Commander Registration" description="신규 사령관 계정 발급 · LEVEL 1 CLEARANCE">
      <main className="mx-auto flex max-w-3xl justify-center py-10">
        <AuthForm mode="register" />
      </main>
    </TopNav>
  );
}

