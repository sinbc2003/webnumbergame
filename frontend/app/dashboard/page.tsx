import TopNav from "@/components/TopNav";
import RequireAuth from "@/components/RequireAuth";

export default function DashboardPage() {
  return (
    <RequireAuth>
      <TopNav pageTitle="MathGame Battle Lobby" description="사령관 집결 채널 · 실시간 채팅 사용 가능" />
    </RequireAuth>
  );
}


