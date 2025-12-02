import TopNav from "@/components/TopNav";
import RoomCreateBoard from "@/components/rooms/RoomCreateBoard";

export default function RoomCreatePage() {
  return (
    <TopNav layout="focus" pageTitle="방 만들기" description="커스텀 매치 생성" showChat={false}>
      <RoomCreateBoard />
    </TopNav>
  );
}


