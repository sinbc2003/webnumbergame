import RequireAuth from "@/components/RequireAuth";

export default function RoomsLayout({ children }: { children: React.ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}

