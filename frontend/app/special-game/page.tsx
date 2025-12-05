import RequireAuth from "@/components/RequireAuth";
import TopNav from "@/components/TopNav";
import SpecialGamePanel from "./SpecialGamePanel";

export const revalidate = 0;

export default function SpecialGamePage() {
  return (
    <RequireAuth>
      <TopNav
        layout="focus"
        pageTitle="Special Game"
        description="관리자가 지정한 문제에서 기호 사용량 최고 기록에 도전하세요."
        showChat={false}
      >
        <SpecialGamePanel />
      </TopNav>
    </RequireAuth>
  );
}

