import RequireAuth from "@/components/RequireAuth";

export default function TournamentsLayout({ children }: { children: React.ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}

