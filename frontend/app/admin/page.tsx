import AdminPanel from "./AdminPanel";
import TopNav from "@/components/TopNav";
import RequireAuth from "@/components/RequireAuth";

export const revalidate = 0;

export default function AdminPage() {
  return (
    <RequireAuth>
      <TopNav layout="focus" pageTitle="Ops Console" description="관리자 전용 패널 · LEVEL 7 CLEARANCE" showChat={false}>
        <main className="mx-auto max-w-5xl py-6">
          <h1 className="text-2xl font-semibold text-white">관리자 페이지</h1>
          <p className="mt-2 text-sm text-night-400">
            문제 데이터 관리 및 테스트 데이터 초기화를 수행할 수 있습니다.
          </p>
          <div className="mt-6">
            <AdminPanel />
          </div>
        </main>
      </TopNav>
    </RequireAuth>
  );
}


