import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/Shell";
import { CandidateProvider } from "@/lib/candidate";

export const metadata: Metadata = {
  title: "Skill Scout Nexus",
  description: "Placement readiness: resume, quizzes, mock interviews and an adaptive weekly plan.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CandidateProvider>
          <Shell>{children}</Shell>
        </CandidateProvider>
      </body>
    </html>
  );
}
