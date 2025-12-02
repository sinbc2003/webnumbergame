import TopNav from "@/components/TopNav";
import AuthForm from "@/components/forms/AuthForm";

export default function LoginPage() {
  return (
    <TopNav pageTitle="Battle.net Access" description="지휘관 인증 포털 · ACCESS LEVEL 3">
      <main className="mx-auto flex max-w-3xl justify-center py-10">
        <AuthForm mode="login" />
      </main>
    </TopNav>
  );
}

