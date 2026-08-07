import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const allowedRoots = new Set(["health", "status", "funds"]);

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const root = path.at(0);
  if (!root || !allowedRoots.has(root) || path.some((part) => part === "..")) {
    return NextResponse.json({ detail: "مسیر API مجاز نیست." }, { status: 404 });
  }

  const configuredBase = process.env.VITE_API_URL?.trim().replace(/\/+$/, "");
  if (!configuredBase) {
    return NextResponse.json(
      {
        detail: "آدرس Backend هنوز برای Frontend تنظیم نشده است.",
        code: "API_NOT_CONFIGURED",
      },
      { status: 503 },
    );
  }

  let target: URL;
  try {
    const base = new URL(`${configuredBase}/`);
    target = new URL(path.map(encodeURIComponent).join("/"), base);
    target.search = request.nextUrl.search;
  } catch {
    return NextResponse.json(
      { detail: "مقدار VITE_API_URL معتبر نیست.", code: "INVALID_API_URL" },
      { status: 500 },
    );
  }

  try {
    const upstream = await fetch(target, {
      method: "GET",
      headers: { accept: "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    const body = await upstream.arrayBuffer();
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail: "اتصال Frontend به Backend برقرار نشد.",
        code: "API_UNREACHABLE",
      },
      { status: 502 },
    );
  }
}
