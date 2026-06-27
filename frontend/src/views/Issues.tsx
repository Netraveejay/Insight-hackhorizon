import { useEffect, useState } from 'react';
import { api, Issue, IssueDetail } from '../api';
import IssueRow from '../components/IssueRow';
import IssueDetailPanel from '../components/IssueDetailPanel';

export default function Issues({ week }: { week: string }) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<IssueDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    api.issues(week).then((d) => {
      setIssues(d.issues);
      if (d.issues.length > 0) {
        setSelected(d.issues[0].cluster_id);
      } else {
        setSelected(null);
        setDetail(null);
      }
    });
  }, [week]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    setLoadingDetail(true);
    api.issueDetail(selected)
      .then((d) => setDetail(d as IssueDetail))
      .finally(() => setLoadingDetail(false));
  }, [selected]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Prioritised Issues — {week}</h2>
        <p className="text-sm text-slate-500 mt-1">
          Ranked by priority and negative volume. Select an issue to review evidence and recommendations.
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <div className="space-y-2">
          {issues.map((issue) => (
            <IssueRow
              key={issue.cluster_id}
              issue={issue}
              selected={selected === issue.cluster_id}
              onClick={() => setSelected(issue.cluster_id)}
            />
          ))}
          {issues.length === 0 && (
            <p className="text-slate-500 bg-white border rounded-lg p-6 text-center">
              No prioritised issues this week.
            </p>
          )}
        </div>

        <div>
          {loadingDetail && (
            <div className="bg-white border rounded-xl p-8 text-center text-slate-500 text-sm sticky top-4">
              Loading issue detail…
            </div>
          )}
          {!loadingDetail && detail && <IssueDetailPanel detail={detail} />}
          {!loadingDetail && !detail && issues.length > 0 && (
            <div className="bg-slate-50 border border-dashed rounded-xl p-8 text-center text-slate-500 text-sm sticky top-4">
              Select an issue to view evidence
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
