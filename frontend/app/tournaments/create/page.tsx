import TopNav from "@/components/TopNav";
import TournamentForm from "@/components/forms/TournamentForm";

export default function TournamentCreatePage() {
  return (
    <div>
      <TopNav />
      <main className="mx-auto flex max-w-3xl justify-center px-6 py-10">
        <TournamentForm />
      </main>
    </div>
  );
}

