import { useCallback, useEffect, useRef, useState } from "react";
import { dashboardApi } from "../../app/api";
import type { RemoteRepository } from "../../shared/types";

export function useRepositoryCatalog(host: string, organization: string) {
  const [results, setResults] = useState<RemoteRepository[]>([]);
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const request = useRef(0);

  const search = useCallback(async (text: string, nextPage = 1): Promise<void> => {
    const id = ++request.current;
    setLoading(true);
    setError("");
    if (nextPage === 1) { setResults([]); setHasMore(false); }
    try {
      const items = organization ? await dashboardApi.searchRepositories(host, text, nextPage, organization)
        : await dashboardApi.searchRepositories(host, text, nextPage);
      if (request.current !== id) return;
      setResults((previous) => nextPage === 1 ? items : [...previous, ...items.filter((item) => !previous.some((old) => old.clone_url === item.clone_url))]);
      setPage(nextPage);
      setAppliedQuery(text);
      setHasMore(items.length === 100);
    } catch (reason) {
      if (request.current === id) setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      if (request.current === id) setLoading(false);
    }
  }, [host, organization]);

  useEffect(() => {
    setQuery("");
    if (host) void search("");
    else { setResults([]); setHasMore(false); setLoading(false); setError(""); }
    return () => { request.current += 1; };
  }, [host, search]);

  return { results, setResults, query, setQuery, loading, error, hasMore, search,
    loadMore: () => search(appliedQuery, page + 1) };
}
