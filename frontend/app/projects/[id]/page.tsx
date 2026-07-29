import ProtectedPage from "@/components/auth/ProtectedPage";
import ProjectDetailClient from "./_components/ProjectDetailClient";

export default function ProjectDetailPage() {
  return (
    <ProtectedPage>
      <ProjectDetailClient />
    </ProtectedPage>
  );
}