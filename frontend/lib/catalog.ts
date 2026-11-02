"use client";

import { useEffect, useState } from "react";
import { get, type Catalog, type Domain } from "./api";

let cached: Promise<Catalog> | null = null;

/** The catalog, fetched once per page load and shared by every page. */
export function useCatalog(): { catalog: Catalog | null; error: string | null } {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    cached ??= get<Catalog>("/api/catalog");
    cached.then(setCatalog, (e: Error) => {
      cached = null;
      setError(e.message);
    });
  }, []);
  return { catalog, error };
}

/** The domain that lists `role`; roles only the skill map knows are computer science. */
export function domainOf(catalog: Catalog, role: string | undefined): Domain {
  return catalog.domains.find((d) => d.roles.some((r) => r.name === role)) ?? catalog.domains[0];
}
