// Sprint 7.4: shape of GET /admin/stats (counters computed by the database).
export type AdminStats = {
  users: { total: number; active: number; inactive: number; verified: number; unverified: number; admins: number };
  projects: { total: number };
  analyses: {
    total: number;
    completed: number;
    running: number;
    failed: number;
    with_errors: number;
    average_score: number | null;
  };
  top_sectors: { industry: string; count: number }[];
  top_regions: { region: string; count: number }[];
};
