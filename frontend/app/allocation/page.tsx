"use client";

import { useEffect, useMemo, useState } from "react";
import { DataState, MetricCard, PageHeader, Panel, StatusBadge } from "@/components/dashboard-ui";
import { ApiError, FundSummary, getFunds } from "@/lib/api";
import { formatNumber, formatPercent, normalizePersianName, toNumber } from "@/lib/format";
import { getBenchmarkBm } from "@/lib/runtime";

const selectedFundNames = [
  "رشدی کیان",
  "سلام",
  "ثمین",
  "ثروتم",
  "جوانه کوچک",
  "آگاس",
  "سرو",
  "اطلس",
];

interface ExposureRow {
  fund: FundSummary;
  stock: number | null;
  equityFund: number | null;
  exposure: number | null;
}

function exposureOf(fund: FundSummary): ExposureRow {
  const source = fund.latest_exposure ?? fund;
  const stock = toNumber(source.stock_percentage ?? fund.stock);
  const equityFund = toNumber(source.equity_fund_percentage ?? fund.equity_fund);
  const publishedExposure = toNumber(source.equity_exposure ?? fund.equity_exposure);
  return {
    fund,
    stock,
    equityFund,
    exposure:
      publishedExposure ?? (stock !== null && equityFund !== null ? stock + equityFund : null),
  };
}

export default function AllocationPage() {
  const [funds, setFunds] = useState<FundSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [benchmark, setBenchmark] = useState(2.99);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    const benchmarkTimer = window.setTimeout(() => setBenchmark(getBenchmarkBm()), 0);
    let active = true;
    getFunds({ limit: 200 })
      .then((response) => {
        if (!active) return;
        setFunds(response.items);
        setTotal(response.total);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError("داده صندوق‌ها برای تحلیل دریافت نشد.", 500),
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      window.clearTimeout(benchmarkTimer);
    };
  }, []);

  const universe = useMemo(() => {
    return selectedFundNames.map((selectedName) => {
      const needle = normalizePersianName(selectedName);
      const fund = funds.find((candidate) => {
        const candidateName = normalizePersianName(candidate.name);
        return candidateName.includes(needle) || needle.includes(candidateName);
      });
      return {
        selectedName,
        row: fund ? exposureOf(fund) : null,
      };
    });
  }, [funds]);

  const validRows = useMemo(
    () =>
      universe
        .flatMap((item) => (item.row?.exposure !== null && item.row ? [item.row] : []))
        .sort((a, b) => (b.exposure ?? 0) - (a.exposure ?? 0)),
    [universe],
  );
  const averageExposure = validRows.length
    ? validRows.reduce((totalValue, row) => totalValue + (row.exposure ?? 0), 0) /
      validRows.length
    : null;
  const maximum = Math.max(benchmark, ...validRows.map((row) => row.exposure ?? 0), 1);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="ALLOCATION ANALYSIS"
        title="تحلیل Exposure صندوق‌های منتخب"
        description="محاسبه فقط بر مبنای Stock و Equity Fund واقعی دریافت‌شده از Backend انجام می‌شود."
        action={<StatusBadge tone="blue">Bm = {formatPercent(benchmark)}</StatusBadge>}
      />

      <section className="formula-strip" aria-label="فرمول تحلیل تخصیص">
        <div>
          <span>ورودی اول</span>
          <strong>Stock %</strong>
        </div>
        <i>+</i>
        <div>
          <span>ورودی دوم</span>
          <strong>Equity Fund %</strong>
        </div>
        <i>=</i>
        <div className="formula-result">
          <span>خروجی</span>
          <strong>Exposure %</strong>
        </div>
      </section>

      <section className="metric-grid allocation-metrics">
        <MetricCard label="Benchmark درآمد ثابت" value={formatPercent(benchmark)} detail="مقدار Runtime قابل تنظیم" tone="navy" />
        <MetricCard label="پوشش صندوق‌های منتخب" value={`${formatNumber(validRows.length)} / ۸`} detail="دارای دو ورودی معتبر Exposure" tone="green" />
        <MetricCard label="میانگین Exposure" value={formatPercent(averageExposure)} detail="فقط صندوق‌های دارای داده معتبر" />
        <MetricCard label="بیشترین Exposure" value={validRows[0] ? formatPercent(validRows[0].exposure) : "—"} detail={validRows[0]?.fund.name ?? "داده کافی موجود نیست"} />
      </section>

      {loading ? <DataState title="در حال دریافت داده تحلیل" description="اطلاعات صندوق‌ها از Backend خوانده می‌شود." /> : null}
      {error ? (
        <DataState
          tone={error.code === "API_NOT_CONFIGURED" ? "warning" : "danger"}
          title="تحلیل Allocation در دسترس نیست"
          description={error.message}
        />
      ) : null}

      {!loading && !error && validRows.length === 0 ? (
        <DataState
          tone="warning"
          title="API فعلی داده Exposure ارائه نمی‌کند"
          description="هیچ مقدار ساختگی نمایش داده نشده است. برای فعال شدن رتبه‌بندی، پاسخ Backend باید stock_percentage و equity_fund_percentage یا equity_exposure را برای صندوق‌ها برگرداند."
        />
      ) : null}

      {!loading && !error ? (
        <section className="two-column-grid allocation-grid">
          <Panel
            title="رتبه‌بندی Exposure"
            subtitle="مرتب‌شده از بیشترین مواجهه سهامی تا کمترین"
          >
            {validRows.length ? (
              <div className="ranking-list">
                {validRows.map((row, index) => (
                  <div className="ranking-row" key={row.fund.id}>
                    <span className="rank-number">{formatNumber(index + 1)}</span>
                    <div>
                      <strong>{row.fund.name}</strong>
                      <small>
                        سهام {formatPercent(row.stock)} · صندوق سهامی {formatPercent(row.equityFund)}
                      </small>
                    </div>
                    <b>{formatPercent(row.exposure)}</b>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-inline">تا دریافت فیلدهای Exposure، رتبه‌ای تولید نمی‌شود.</p>
            )}
          </Panel>

          <Panel title="نمودار مقایسه‌ای" subtitle={`نمایش Exposure در برابر Bm ${formatPercent(benchmark)}`}>
            {validRows.length ? (
              <div className="exposure-chart">
                {validRows.map((row) => (
                  <div className="exposure-bar-row" key={row.fund.id}>
                    <div><span>{row.fund.name}</span><strong>{formatPercent(row.exposure)}</strong></div>
                    <div className="exposure-track">
                      <span className="benchmark-marker" style={{ insetInlineStart: `${(benchmark / maximum) * 100}%` }} />
                      <span className="exposure-fill" style={{ width: `${((row.exposure ?? 0) / maximum) * 100}%` }} />
                    </div>
                  </div>
                ))}
                <p className="chart-legend"><i /> خط مرجع Bm</p>
              </div>
            ) : (
              <p className="empty-inline">نمودار بدون داده معتبر ساخته نمی‌شود.</p>
            )}
          </Panel>
        </section>
      ) : null}

      {!loading && !error ? (
        <Panel
          title="وضعیت Universe منتخب"
          subtitle={`${formatNumber(total)} صندوق در API بررسی شد؛ فقط هشت صندوق مصوب در این تحلیل نمایش داده می‌شوند.`}
        >
          <div className="universe-grid">
            {universe.map((item) => {
              const hasFund = Boolean(item.row);
              const hasExposure = item.row?.exposure !== null && item.row?.exposure !== undefined;
              return (
                <div className="universe-item" key={item.selectedName}>
                  <span>{item.selectedName}</span>
                  <StatusBadge tone={hasExposure ? "success" : hasFund ? "warning" : "danger"}>
                    {hasExposure ? "Exposure معتبر" : hasFund ? "فیلد Exposure مفقود" : "صندوق شناسایی نشد"}
                  </StatusBadge>
                </div>
              );
            })}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
