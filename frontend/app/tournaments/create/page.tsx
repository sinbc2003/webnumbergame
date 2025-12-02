import TopNav from "@/components/TopNav";
import TournamentForm from "@/components/forms/TournamentForm";

export default function TournamentCreatePage() {
  return (
    <TopNav pageTitle="League Forge" description="새 토너먼트 생성 · OPS AUTHORIZED" showChat={false}>
      <main className="mx-auto flex max-w-3xl justify-center py-10">
        <TournamentForm />
      </main>
    </TopNav>
  );
}

