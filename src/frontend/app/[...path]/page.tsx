import { Analytics } from "@vercel/analytics/react";
import { Home } from "../components/home";
import { getServerSideConfig } from "../config/server";

const serverConfig = getServerSideConfig();

export default async function CatchAllPage() {
  return (
    <>
      <Home />
      {serverConfig?.isVercel && (
        <>
          <Analytics />
        </>
      )}
    </>
  );
}
