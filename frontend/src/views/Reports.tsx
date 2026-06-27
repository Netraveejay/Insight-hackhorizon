import { useEffect, useState } from 'react';
import { Download, FileText, Mail } from 'lucide-react';
import { api, ReportMeta } from '../api';
import { useAuth } from '../auth/AuthContext';

interface Props {
  week: string;
}

export default function Reports({ week }: Props) {
  const { user } = useAuth();
  const [reports, setReports] = useState<ReportMeta[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.reports(week).then((r) => setReports(r.reports)).catch((e) => setError(e.message));
  }, [week]);

  const siteReports = reports.filter((r) => r.report_type === 'site');
  const digest = reports.find((r) => r.report_type === 'digest');

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Manager Reports</h2>
        <p className="text-sm text-slate-600 mt-1">
          After each pipeline run, Insight generates HTML reports and queues them for site managers.
          Download your report below — open in a browser and use <strong>Print → Save as PDF</strong> for a PDF copy.
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-slate-700">
        <p className="font-semibold text-slate-900 mb-1">How delivery works</p>
        <ol className="list-decimal list-inside space-y-1 text-slate-600">
          <li>Pipeline completes → Output Agent generates one report per site + executive digest</li>
          <li>Reports are saved as HTML files (logged to distribution queue with recipient email)</li>
          <li>Managers sign in here and download their site report for week {week}</li>
          <li>In production: same files attach to email or SharePoint — demo uses download only</li>
        </ol>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      {reports.length === 0 && !error && (
        <p className="text-slate-500 text-sm">No reports yet — run the pipeline for week {week} first.</p>
      )}

      {digest && user?.role === 'admin' && (
        <ReportCard report={digest} featured />
      )}

      <div className="space-y-3">
        <h3 className="font-semibold text-slate-800 text-sm">
          {user?.role === 'manager' ? 'Your site report' : 'Site reports'}
        </h3>
        {siteReports.map((r) => (
          <ReportCard key={r.id} report={r} />
        ))}
      </div>
    </div>
  );
}

function ReportCard({ report, featured }: { report: ReportMeta; featured?: boolean }) {
  const [downloading, setDownloading] = useState(false);

  const download = async () => {
    setDownloading(true);
    try {
      await api.downloadReport(report.id, report.file_name);
    } catch {
      alert('Download failed — sign in and re-run the pipeline if reports are missing.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className={`bg-white border rounded-xl p-5 flex items-start gap-4 ${featured ? 'border-accent shadow-sm' : ''}`}>
      <div className={`w-11 h-11 rounded-lg flex items-center justify-center shrink-0 ${featured ? 'bg-accent text-white' : 'bg-slate-100 text-slate-600'}`}>
        <FileText size={20} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-slate-900">{report.title}</p>
        <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
          <Mail size={12} />
          Queued for {report.recipient_email}
        </p>
        <p className="text-xs text-slate-400 mt-1">{report.file_name}</p>
      </div>
      <button
        type="button"
        onClick={download}
        disabled={downloading}
        className="flex items-center gap-1.5 bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 shrink-0 disabled:opacity-60"
      >
        <Download size={16} />
        {downloading ? '…' : 'Download'}
      </button>
    </div>
  );
}
