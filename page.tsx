"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DataState,
  LoadingGrid,
  MetricCard,
  PageHeader,
  Panel,
  StatusBadge,
} from "@/components/dashboard-ui";
import { ApiError, FundSummary, getFunds, getStatus, SystemStatus } from "@/lib/api";
import {
  connectionLabel,
  formatCompact,
  formatDate,
  formatNumber,
  toNumber,
} from "@/lib/format";

export default function DashboardPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [funds, setFunds] = useState<FundSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextStatus, fundResponse] = await Promise.all([
        getStatus(),
        getFunds({ limit: 200 }),
      ]);
      setStatus(nextStatus);
      setFunds(fundResponse.items);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught
          : new ApiError("خطای پیش‌بینی‌نشده در دریافت اطلاعات.", 500),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const navSummary = useMemo(() => {
    const rows = funds
      .map((fund) => ({
        fund,
        nav: toNumber(fund.latest_nav?.statistical_nav),
        netAsset: toNumber(fund.latest_nav?.net_asset),
      }))
      .filter((row) => row.nav !== null);
    const netAssets = rows
      .map((row) => row.netAsset)
      .filter((value): value is number => value !== null);
    const latestUpdate = funds
      .map((fund) => fund.source_updated_at ?? fund.latest_nav?.nav_date ?? null)
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1);
    const averageNav = rows.length
      ? rows.reduce((total, row) => total + (row.nav ?? 0), 0) / rows.length
      : null;
    return {
      rows: rows.sort((a, b) => (b.nav ?? 0) - (a.nav ?? 0)).slice(0, 8),
      averageNav,
      totalNetAsset: netAssets.length
        ? netAssets.reduce((total, value) => total + value, 0)
        : null,
      latestUpdate,
    };
  }, [funds]);

  const connection = connectionLabel(status?.latest_crawl?.status);
  const chartMaximum = Math.max(...navSummary.rows.map((row) => row.nav ?? 0), 1);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="MARKET DATA OVERVIEW"
        title="داشبورد تخصیص دارایی افران"
        description="نمای یکپارچه وضعیت دریافت داده، پوشش صندوق‌ها و آخرین اطلاعات ثبت‌شده در سامانه."
        action={
          <button type="button" className="button-secondary" onClick={() => void load()} disabled={loading}>
            {loading ? "در حال دریافت…" : "بروزرسانی نما"}
          </button>
        }
      />

      {loading ? <LoadingGrid /> : null}
      {!loading && error ? (
        <DataState
          tone={error.code === "API_NOT_CONFIGURED" ? "warning" : "danger"}
          title={error.code === "API_NOT_CONFIGURED" ? "Backend تنظیم نشده است" : "ارتباط با API برقرار نشد"}
          description={error.message}
        />
      ) : null}

      {!loading && !error && status ? (
        <>
          <section className="metric-grid" aria-label="شاخص‌های کلیدی">
            <MetricCard
              label="تعداد کل صندوق‌ها"
              value={formatNumber(status.counts.funds)}
              detail={`${formatNumber(status.counts.nav_records)} مشاهده NAV ذخیره شده`}
              tone="navy"
            />
            <MetricCard
              label="وضعیت Fipiran"
              value={<StatusBadge tone={connection.tone}>{connection.label}</StatusBadge>}
              detail={status.latest_crawl ? `روش دریافت: ${status.latest_crawl.method ?? "—"}` : "هنوز Crawl ثبت نشده است"}
              tone="green"
            />
            <MetricCard
              label="آخرین Crawl"
              value={formatDate(status.latest_crawl?.finished_at ?? status.latest_crawl?.started_at, true)}
              detail={status.latest_crawl ? `${formatNumber(status.latest_crawl.records_received)} رکورد دریافت شد` : "داده‌ای موجود نیست"}
            />
            <MetricCard
              label="آخرین بروزرسانی داده"
              value={formatDate(navSummary.latestUpdate)}
              detail={`${formatNumber(navSummary.rows.length)} صندوق دارای NAV معتبر در نمای فعلی`}
            />
          </section>

          <section className="two-column-grid">
            <Panel
              title="خلاصه NAV"
              subtitle="جمع دارایی خالص و میانگین NAV آماری رکوردهای معتبر دریافت‌شده"
            >
              <div className="summary-pair">
                <div>
                  <span>جمع خالص دارایی</span>
                  <strong>{formatCompact(navSummary.totalNetAsset)}</strong>
                  <small>بر اساس فیلد net_asset</small>
                </div>
                <div>
                  <span>میانگین NAV آماری</span>
                  <strong>{formatNumber(navSummary.averageNav)}</strong>
                  <small>بدون جایگزینی مقادیر مفقود</small>
                </div>
              </div>
              {navSummary.rows.length ? (
                <div className="bar-list" aria-label="مقایسه آخرین NAV صندوق‌ها">
                  {navSummary.rows.map(({ fund, nav }) => (
                    <div className="bar-row" key={fund.id}>
                      <div className="bar-label">
                        <span>{fund.name}</span>
                        <strong>{formatNumber(nav)}</strong>
                      </div>
                      <div className="bar-track">
                        <span style={{ width: `${Math.max(((nav ?? 0) / chartMaximum) * 100, 2)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <DataState title="NAV ثبت نشده است" description="پس از نخستین Crawl موفق، خلاصه NAV در این بخش ظاهر می‌شود." />
              )}
            </Panel>

            <Panel title="کنترل کیفیت داده" subtitle="نمایش مستقیم وضعیت ثبت‌شده در Backend">
              <div className="quality-list">
                <div>
                  <span>رکوردهای عملکرد</span>
                  <strong>{formatNumber(status.counts.performance_records)}</strong>
                </div>
                <div>
                  <span>اطلاعات مدیران</span>
                  <strong>{formatNumber(status.counts.manager_records)}</strong>
                </div>
                <div>
                  <span>تعداد اجراهای Crawler</span>
                  <strong>{formatNumber(status.counts.crawl_runs)}</strong>
                </div>
                <div>
                  <span>خطاهای آخرین اجرا</span>
                  <strong>{status.latest_crawl ? formatNumber(status.latest_crawl.error_count) : "—"}</strong>
                </div>
              </div>
              {status.last_runtime_error ? (
                <DataState tone="danger" title="آخرین خطای Runtime" description={status.last_runtime_error} />
              ) : (
                <DataState title="جایگزینی داده غیرفعال است" description="مقادیر مفقود به صفر یا داده نمونه تبدیل نمی‌شوند." />
              )}
            </Panel>
          </section>
        </>
      ) : null}
    </div>
  );
}
